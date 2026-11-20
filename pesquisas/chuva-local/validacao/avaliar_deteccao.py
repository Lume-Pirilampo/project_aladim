"""Calibra o corte de previsão em 2022 e mede detecção em 2021."""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

from avaliar_validacao import confidence_by_event, events, gauge_coverage, predict

TARGET_RATE = 0.0025
REFERENCE_DEPTH = 5
BASELINE = "fixo_10"


def panel(path):
    ds = xr.load_dataset(path)
    reference = ds.gauge_rate.transpose("time", "id").values
    estimates = predict(ds, extended=True)
    coverage = gauge_coverage(ds) <= 20_000
    valid = np.isfinite(reference) & coverage[None, :]
    for field in estimates.values():
        valid &= np.isfinite(field)
    strong = valid & (reference >= REFERENCE_DEPTH)
    return ds.time.values, estimates, valid & ~strong, strong


def alarm_cut(values, max_rate):
    if not len(values):
        raise ValueError("Calibração sem observações abaixo do corte")
    allowance = int(len(values) * max_rate)
    # Com empates no limite, o corte deve excluir todas as previsões empatadas.
    ordered = np.partition(values, len(values) - 1 - allowance)
    last_excluded = ordered[len(values) - 1 - allowance]
    return float(np.nextafter(float(last_excluded), np.inf))


def count_row(mode, method, cut, alarms, negatives, strong, base_alarms, event_labels):
    delta = alarms.astype(float) - base_alarms
    ci = confidence_by_event(delta, strong, event_labels)
    false_alarms = int(np.count_nonzero(alarms & negatives))
    detections = int(np.count_nonzero(alarms & strong))
    return {
        "recorte": mode, "metodo": method, "corte_previsto_mm": cut,
        "fortes_observados": int(strong.sum()), "nao_fortes_observados": int(negatives.sum()),
        "detectados": detections, "falsos_alarmes": false_alarms,
        "taxa_deteccao": detections / strong.sum(),
        "falsos_alarmes_por_10mil": 10_000 * false_alarms / negatives.sum(),
        "delta_deteccao_vs_fixo": float(delta[strong].mean()),
        "delta_ic025": ci[0], "delta_ic975": ci[1],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("calibration", type=Path)
    parser.add_argument("verification", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    development = panel(args.calibration)
    verification = panel(args.verification)
    _, forecasts, negatives, _ = development
    cuts = {key: alarm_cut(values[negatives], TARGET_RATE) for key, values in forecasts.items()}
    rows = []
    for label, (times, forecasts, negatives, strong) in (
        ("IT calibração 2022", development), ("IT verificação 2021", verification)
    ):
        labels = events(times, strong)
        # A promoção para float64 preserva a exclusão dos valores empatados no corte.
        base = (forecasts[BASELINE].astype(float) >= cuts[BASELINE])
        for key, values in forecasts.items():
            alarm = values.astype(float) >= cuts[key]
            rows.append(count_row(label, key, cuts[key], alarm, negatives, strong, base, labels))
    report = pd.DataFrame(rows)
    print(report[["recorte", "metodo", "corte_previsto_mm", "detectados", "taxa_deteccao",
                  "falsos_alarmes_por_10mil", "delta_ic025", "delta_ic975"]]
          .to_string(index=False, float_format=lambda v: f"{v:.4f}"))
    report.to_csv(args.output, index=False, float_format="%.8f")
