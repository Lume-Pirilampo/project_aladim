"""Compara alarmes calibrados nos dois meses e avaliados em abril e julho."""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

from avaliar_deteccao import TARGET_RATE, alarm_cut, count_row
from avaliar_nyc import estimates_nyc
from avaliar_validacao import events, gauge_coverage


def panel(dataset):
    estimates = estimates_nyc(dataset, protect_censored=True)
    obs = dataset.gauge_rate.transpose("time", "id").values
    valid = np.isfinite(obs) & (gauge_coverage(dataset)[None, :] <= 20_000)
    for forecast in estimates.values():
        valid &= np.isfinite(forecast)
    strong = valid & (obs >= 5)
    return dataset.time.values, estimates, valid & ~strong, strong


def evaluate_dates(name, panel_data, cuts, date_mask):
    stamps, estimates, negatives, positives = panel_data
    stamps, negatives, positives = stamps[date_mask], negatives[date_mask], positives[date_mask]
    labels = events(stamps, positives)
    raw = estimates["radar"][date_mask].astype(float) >= cuts["radar"]
    rows = []
    for candidate, estimate in estimates.items():
        alarms = estimate[date_mask].astype(float) >= cuts[candidate]
        row = count_row(name, candidate, cuts[candidate], alarms, negatives, positives, raw, labels)
        row["delta_deteccao_vs_radar"] = row.pop("delta_deteccao_vs_fixo")
        rows.append(row)
    return rows


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("calibration", type=Path)
    parser.add_argument("verification", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    development = panel(xr.load_dataset(args.calibration))
    holdout = panel(xr.load_dataset(args.verification))
    if np.intersect1d(development[0], holdout[0]).size:
        raise ValueError("Janelas de calibração e verificação sobrepostas")
    _, predicted, negatives, _ = development
    cuts = {name: alarm_cut(est[negatives], TARGET_RATE) for name, est in predicted.items()}
    rows = evaluate_dates(
        "maio–junho", development, cuts, np.ones(len(development[0]), dtype=bool)
    )
    date_masks = {
        "abril e julho": np.ones(len(holdout[0]), dtype=bool),
        "abril": holdout[0] <= np.datetime64("2024-05-01T00:00"),
        "julho": holdout[0] > np.datetime64("2024-07-01T00:00"),
    }
    for name, test in date_masks.items():
        rows += evaluate_dates(name, holdout, cuts, test)
    result = pd.DataFrame(rows)
    result.to_csv(args.output, index=False, float_format="%.8f")
    print(result.loc[result.recorte == "abril e julho",
                     ["metodo", "corte_previsto_mm", "fortes_observados", "detectados",
                      "falsos_alarmes_por_10mil", "delta_ic025", "delta_ic975"]]
          .to_string(index=False, float_format=lambda v: f"{v:.4f}"))
