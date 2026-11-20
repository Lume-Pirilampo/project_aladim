"""Sensibilidade aos eventos, às estações e à concordância entre pluviômetros."""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.spatial.distance import cdist
import xarray as xr

from avaliar_pluviometros_comunitarios import (
    RAIN_PRODUCT, active_distance, load_gauges, normalize_italy_radar, prepare_panel,
)
from avaliar_validacao import coordinates, evaluate, events, gauge_coverage, predict


def leave_one_out(differences, labels, stations):
    totals = []
    for grouping in (labels, stations):
        _, ids = np.unique(grouping, return_inverse=True)
        sums = np.bincount(ids, weights=differences)
        sizes = np.bincount(ids)
        kept = sizes < len(differences)
        estimates = (differences.sum() - sums[kept]) / (len(differences) - sizes[kept])
        totals.append((float(np.min(estimates)), float(np.max(estimates))) if kept.any()
                      else (float("nan"), float("nan")))
    return tuple(value for group in totals for value in group)


def compare_to_asos(panel, asos, times):
    pws_position = coordinates(panel, "gauge_x", "gauge_y")
    asos_position = coordinates(asos, "gauge_x", "gauge_y")
    separation = cdist(asos_position, pws_position)
    closest = separation.argmin(axis=1)
    minimum = separation.min(axis=1)
    official = asos.gauge_rate.transpose("time", "id").sel(time=times).values
    paired = panel.gauge_rate.transpose("time", "id").values[:, closest]
    rows = []
    for limit in (2000, 3000, 5000):
        valid = (minimum <= limit)[None, :] & np.isfinite(official) & np.isfinite(paired)
        marked = valid & (official >= 5)
        difference = paired - official
        rows.append({
            "distancia_maxima_asos_pws_km": limit / 1000,
            "pluviometros_asos": int(valid.any(axis=0).sum()),
            "pares_com_medicao_simultanea": int(valid.sum()),
            "chuvas_fortes_asos": int(marked.sum()),
            "chuvas_fortes_confirmadas_pws": int((marked & (paired >= 5)).sum()),
            "eam_pws_frente_asos_em_picos": float(np.abs(difference[marked]).mean())
            if marked.any() else np.nan,
        })
    return pd.DataFrame(rows)


def sensitivity(panel, tolerance):
    reference = panel.gauge_rate.transpose("time", "id").values
    positions = coordinates(panel, "gauge_x", "gauge_y")
    distance = cdist(positions, positions)
    np.fill_diagonal(distance, np.inf)
    closest = distance.argmin(axis=1)
    independent_wet = (distance.min(axis=1) <= 2000)[None, :] & (reference[:, closest] >= 2)
    nearby = (active_distance(panel) <= 5000) & (gauge_coverage(panel)[None, :] <= 20_000)
    choices = predict(panel)
    choices = {key: choices[key] for key in ("radar", "sem_filtro", "fixo_5", "intensidade")}
    radar = choices["radar"]
    rows = []
    all_hours = np.ones(panel.sizes["time"], dtype=bool)
    for label, match in (("próximos", nearby), ("próximos com estação vizinha chuvosa", nearby & independent_wet)):
        reference_group = panel.gauge_rate.transpose("time", "id").where(match)
        ds = panel.assign(gauge_rate=reference_group)
        stats = evaluate(ds, choices, "radar", all_hours, label, 20_000)
        strong = (reference_group.values >= 5) & np.isfinite(radar)
        labels = events(panel.time.values, strong)
        rows_idx, stations = np.nonzero(strong)
        for row in stats:
            estimated = choices[row["metodo"]]
            delta = np.abs(estimated - reference) - np.abs(radar - reference)
            difference = delta[strong]
            low_event, high_event, low_station, high_station = leave_one_out(
                difference, labels[rows_idx], stations,
            )
            row.update(
                jitter_minutos=tolerance, min_sem_um_evento=low_event, max_sem_um_evento=high_event,
                min_sem_uma_estacao=low_station, max_sem_uma_estacao=high_station,
                pares_fortes_com_estimativa_reduzida=int(((estimated < radar) & strong).sum()),
                maior_parcela_por_estacao=(np.bincount(stations).max() / len(stations)
                                           if len(stations) else np.nan),
            )
        rows.extend(stats)
    return rows


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pws", type=Path)
    parser.add_argument("asos_pairs", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("radar", type=Path, nargs="+")
    args = parser.parse_args()
    asos = xr.load_dataset(args.asos_pairs)
    links = asos.drop_dims("id")
    radar = xr.concat(
        [normalize_italy_radar(xr.load_dataset(path)[RAIN_PRODUCT]) for path in args.radar],
        dim="time", coords="minimal", compat="equals",
    ).sortby("time")
    if not radar.get_index("time").is_unique:
        raise ValueError("Janelas de radar sobrepostas")
    rows = []
    for tolerance in (2, 1):
        gauges = load_gauges(args.pws, links.get_index("time"), tolerance)
        panel = prepare_panel(links, radar, gauges)
        if tolerance == 2:
            agreement = compare_to_asos(panel, asos, panel.time)
            print(agreement.to_string(index=False))
            agreement.to_csv(args.output.with_name(args.output.stem + "-asos.csv"),
                             index=False, float_format="%.8f")
        rows.extend(sensitivity(panel, tolerance))
    report = pd.DataFrame(rows)
    print(report[["jitter_minutos", "recorte", "metodo", "pares_5", "eventos_5", "eam_5",
                  "min_sem_um_evento", "max_sem_um_evento", "min_sem_uma_estacao",
                  "max_sem_uma_estacao", "pares_fortes_com_estimativa_reduzida"]].to_string(index=False))
    report.to_csv(args.output, index=False, float_format="%.8f")
