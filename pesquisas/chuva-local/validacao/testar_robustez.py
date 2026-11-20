"""Testa a estabilidade de diferenças emparelhadas sob outras divisões em eventos."""
import argparse
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

from avaliar_validacao import confidence_by_event, events, gauge_coverage, predict


def effect_sums(errors, strong, labels):
    cluster = labels[labels >= 0]
    ids = np.unique(cluster)
    sums, sizes = [], []
    for label in ids:
        mask = strong & (labels[:, None] == label)
        sums.append(errors[mask].sum())
        sizes.append(mask.sum())
    return np.asarray(sums), np.asarray(sizes)


def deletion_range(sums, sizes):
    left = sizes.sum() - sizes
    nonempty = left > 0
    if not nonempty.any():
        return np.nan, np.nan
    effect = (sums.sum() - sums[nonempty]) / left[nonempty]
    return effect.min(), effect.max()


def share_of_four(sums, sizes):
    count = len(sizes)
    if count < 4:
        return np.nan
    choices = np.asarray(list(combinations(range(count), 4)))
    values = sums[choices].sum(axis=1) / sizes[choices].sum(axis=1)
    return np.mean(values < 0)


def test(dataset, baseline, candidate):
    observed = dataset.gauge_rate.transpose("time", "id").values
    predicted = predict(dataset, extended=False)
    a, b = predicted[baseline], predicted[candidate]
    valid = np.isfinite(a) & np.isfinite(b) & np.isfinite(observed)
    strong = valid & (observed >= 5) & (gauge_coverage(dataset)[None, :] <= 20_000)
    errors = np.abs(b - observed) - np.abs(a - observed)
    station_sums = np.where(strong, errors, 0).sum(axis=0)
    station_counts = strong.sum(axis=0)
    site_bounds = deletion_range(station_sums[station_counts > 0], station_counts[station_counts > 0])
    lines = []
    for gap in (6, 12, 24):
        labels = events(dataset.time.values, strong, gap_hours=gap)
        sums, sizes = effect_sums(errors, strong, labels)
        if not sizes.size:
            continue
        ci = confidence_by_event(errors, strong, labels)
        event_bounds = deletion_range(sums, sizes)
        lines.append({
            "separacao_eventos_h": gap, "eventos": len(sizes), "pares_5": int(sizes.sum()),
            "delta_eam_5": sums.sum() / sizes.sum(), "delta_ic025": ci[0], "delta_ic975": ci[1],
            "eventos_com_melhora": int((sums < 0).sum()),
            "min_sem_um_evento": event_bounds[0], "max_sem_um_evento": event_bounds[1],
            "min_sem_um_pluviometro": site_bounds[0], "max_sem_um_pluviometro": site_bounds[1],
            "fracao_amostras_quatro_eventos_com_melhora": share_of_four(sums, sizes),
        })
    return pd.DataFrame(lines)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pairs", type=Path)
    parser.add_argument("recorte")
    parser.add_argument("baseline")
    parser.add_argument("candidate")
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    ds = xr.load_dataset(args.pairs)
    if args.recorte == "SE agosto":
        ds = ds.sel(time=ds.time > np.datetime64("2015-08-01T00:00"))
    report = test(ds, args.baseline, args.candidate)
    report.insert(0, "recorte", args.recorte)
    report.insert(1, "base", args.baseline)
    report.insert(2, "candidato", args.candidate)
    print(report.to_string(index=False, float_format=lambda v: f"{v:.4f}"))
    report.to_csv(args.output, index=False, float_format="%.8f")
