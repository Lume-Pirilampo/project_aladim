"""Mede os filtros congelados na terceira rede e a cobertura de correção."""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

from avaliar_validacao import evaluate, gauge_coverage, predict
from diagnosticar_limites import sweep
from obter_radar_nyc import windows


def estimates_nyc(ds, *, protect_censored=False):
    estimates = predict(ds, extended=True)
    estimates["fixo_20"] = sweep(ds, limits=(20,))[20]
    if protect_censored:
        estimates["apagao_sem_reducao"] = sweep(
            ds, limits=(np.inf,), protect_censored=True
        )[np.inf]
    return estimates


def run(ds, catalog, kind, *, protect_censored=False):
    estimates = estimates_nyc(ds, protect_censored=protect_censored)
    timestamps = ds.time.values
    reference = ds.gauge_rate.transpose("time", "id").values
    valid = np.isfinite(reference) & (gauge_coverage(ds)[None, :] <= 20_000)
    for field in estimates.values():
        valid &= np.isfinite(field)
    severe = valid & (reference >= 5)
    eval_windows = [(kind, np.ones(len(timestamps), dtype=bool))]
    if catalog:
        for label, start, end in windows(catalog):
            in_window = (timestamps >= start.to_datetime64()) & (timestamps <= end.to_datetime64())
            if in_window.any():
                eval_windows.append((label, in_window))
    rows = []
    for label, selector in eval_windows:
        metrics = evaluate(ds, estimates, "fixo_10", selector, label, 20_000)
        for row in metrics:
            method = row["metodo"]
            changed = ~np.isclose(estimates[method], estimates["radar"])
            row["pares_alterados"] = int(np.count_nonzero(valid[selector] & changed[selector]))
            row["pares_5_alterados"] = int(np.count_nonzero(severe[selector] & changed[selector]))
        rows.extend(metrics)
    return pd.DataFrame(rows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pairs", type=Path)
    parser.add_argument("label")
    parser.add_argument("output", type=Path)
    parser.add_argument("--catalog", type=Path)
    parser.add_argument("--protect-censored", action="store_true")
    args = parser.parse_args()
    ds = xr.load_dataset(args.pairs)
    out = run(ds, args.catalog, args.label, protect_censored=args.protect_censored)
    cols = ["recorte", "metodo", "pares", "pares_5", "eventos_5", "eam_5", "eam_10",
            "falsos_alarmes_5", "taxa_deteccao_5", "pares_alterados", "pares_5_alterados"]
    print(out[cols].to_string(index=False, float_format=lambda v: f"{v:.4f}"))
    out.to_csv(args.output, index=False, float_format="%.8f")
