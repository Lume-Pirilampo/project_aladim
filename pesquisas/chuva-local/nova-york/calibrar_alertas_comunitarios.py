"""Calibra alertas com maio–junho e verifica a transferência para março."""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

from avaliar_deteccao import TARGET_RATE, alarm_cut, count_row
from avaliar_pluviometros_comunitarios import (
    active_distance, load_gauges, load_radar, prepare_panel,
)
from avaliar_validacao import events, gauge_coverage, predict


def load_panel(pws, pairs, radar_paths):
    links = xr.load_dataset(pairs).drop_dims("id")
    radar = load_radar(radar_paths)
    gauges = load_gauges(pws, links.get_index("time"), 2)
    return prepare_panel(links, radar, gauges)


def panel_data(ds, *, nearby_only, spinup_hours):
    estimates = predict(ds)
    expected = ("radar", "sem_filtro", "fixo_5", "fixo_10", "intensidade", "intensidade_vizinhos")
    estimates = {k: estimates[k].astype(float) for k in expected}
    observed = ds.gauge_rate.transpose("time", "id").values
    valid = np.isfinite(observed) & (gauge_coverage(ds)[None, :] <= 20_000)
    if spinup_hours:
        age = ds.time.values - ds.window_start.values
        valid &= (age >= np.timedelta64(spinup_hours, "h"))[:, None]
    if nearby_only:
        valid &= active_distance(ds) <= 5000
    for values in estimates.values():
        valid &= np.isfinite(values)
    positives = valid & (observed >= 5)
    return ds.time.values, estimates, valid & ~positives, positives


def evaluate_panel(label, panel, cuts, nearby):
    times, estimates, negatives, positives = panel
    labels = events(times, positives)
    baseline = estimates["radar"] >= cuts["radar"]
    rows = []
    for name, values in estimates.items():
        alerts = values >= cuts[name]
        stats = count_row(label, name, cuts[name], alerts, negatives, positives, baseline, labels)
        stats["delta_deteccao_vs_radar"] = stats.pop("delta_deteccao_vs_fixo")
        stats["escopo"] = "até 5 km de enlace ativo" if nearby else "todos com geometria até 20 km"
        stats["eventos_5"] = len(np.unique(labels[labels >= 0]))
        rows.append(stats)
    return rows


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pws", type=Path)
    parser.add_argument("calibration", type=Path)
    parser.add_argument("verification", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--calibration-radar", nargs="+", type=Path, required=True)
    parser.add_argument("--verification-radar", nargs="+", type=Path, required=True)
    args = parser.parse_args()
    develop = load_panel(args.pws, args.calibration, args.calibration_radar)
    holdout = load_panel(args.pws, args.verification, args.verification_radar)
    if np.intersect1d(develop.time.values, holdout.time.values).size:
        raise ValueError("Janelas de calibração e verificação sobrepostas")
    rows = []
    for nearby in (False, True):
        source = panel_data(develop, nearby_only=nearby, spinup_hours=0)
        target = panel_data(holdout, nearby_only=nearby, spinup_hours=24)
        _, estimates, negative, _ = source
        cuts = {name: alarm_cut(values[negative], TARGET_RATE) for name, values in estimates.items()}
        rows.extend(evaluate_panel("maio–junho (calibração)", source, cuts, nearby))
        rows.extend(evaluate_panel("março (verificação)", target, cuts, nearby))
    result = pd.DataFrame(rows)
    result.to_csv(args.output, index=False, float_format="%.17g")
    print(result[["recorte", "escopo", "metodo", "fortes_observados", "eventos_5",
                  "detectados", "falsos_alarmes", "falsos_alarmes_por_10mil"]].to_string(index=False))
