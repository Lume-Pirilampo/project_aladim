"""Compara limites fixos e adaptativos em pares horários previamente preparados."""
import argparse
from pathlib import Path

from mergeplg.radolan.idw import Invdisttree
import numpy as np
import pandas as pd
from scipy.spatial import distance
import xarray as xr

METHODS = ("radar", "sem_filtro", "fixo_5", "fixo_10", "intensidade", "intensidade_vizinhos")
FIXED = ("fixo_5", "fixo_10")


def coordinates(ds, x, y):
    return np.column_stack((ds[y].values, ds[x].values))


def gauge_to_link_distance(ds):
    points = coordinates(ds, "gauge_x", "gauge_y")
    start = coordinates(ds, "site_0_x", "site_0_y")
    end = coordinates(ds, "site_1_x", "site_1_y")
    lines = end - start
    origin_to_points = points[:, None, :] - start
    squared_length = np.sum(lines * lines, axis=1)
    fraction = np.divide(
        np.sum(origin_to_points * lines, axis=2), squared_length,
        out=np.zeros(origin_to_points.shape[:2]), where=squared_length > 0,
    )
    projected = start + np.clip(fraction, 0, 1)[:, :, None] * lines
    return np.linalg.norm(points[:, None, :] - projected, axis=2)


def gauge_coverage(ds):
    return gauge_to_link_distance(ds).min(axis=1)


def adaptive_masks(residual, path_rain, valid, neighbor_order, neighbor_distances, *, expanded=False):
    bound = np.minimum(15, 5 * np.sqrt(1 + np.maximum(0, path_rain) / 2))
    z = np.where(valid, residual / bound, np.nan)
    simple = valid & (np.abs(z) <= 1)
    local = simple.copy()
    radius = 30_000 if expanded else 10_000
    for i in np.flatnonzero(valid):
        near = neighbor_order[i]
        distances = neighbor_distances[i]
        use = (distances <= radius) & valid[near]
        others = z[near[use][:12]]
        if len(others) >= 8:
            center = np.median(others)
            scale = 1.4826 * np.median(np.abs(others - center))
            tolerance = np.clip(3 * scale, 0.5, 2.0)
            if expanded:
                weight = (10_000 / max(10_000, distances[use][7])) ** 2
                center *= weight
                tolerance = weight * tolerance + (1 - weight)
            local[i] = abs(z[i] - center) <= tolerance and abs(z[i]) <= 3
    return simple, local


def predict(ds, *, extended=False):
    links = coordinates(ds, "link_x", "link_y")
    target = coordinates(ds, "target_x", "target_y")
    inter = Invdisttree(links)
    link_distances = distance.cdist(links, links)
    np.fill_diagonal(link_distances, np.inf)
    neighbor_order = np.argsort(link_distances, axis=1, kind="stable")
    neighbor_distances = np.take_along_axis(link_distances, neighbor_order, axis=1)

    path = ds.radar_at_link.transpose("time", "cml_id").values
    rates = ds.link_rate.transpose("time", "cml_id").values
    raw = ds.radar_at_gauge.transpose("time", "id").values
    names = METHODS + (("alcance_adaptativo",) if extended else ())
    models = {name: raw.copy() for name in names}
    nnear = min(70, len(links))
    for i, (path_rain, link_rate, radar_at_gauges) in enumerate(zip(path, rates, raw, strict=True)):
        residual = link_rate - path_rain
        valid = (path_rain > 0) & np.isfinite(residual)
        if valid.sum() <= 3:
            continue
        intensity, local = adaptive_masks(
            residual, path_rain, valid, neighbor_order, neighbor_distances
        )
        passes = (valid, valid & (np.abs(residual) <= 5),
                  valid & (np.abs(residual) <= 10), intensity, local)
        radar_wet = np.where(
            np.isfinite(radar_at_gauges),
            np.where(radar_at_gauges > 0.01, radar_at_gauges, 0),
            np.nan,
        )
        if extended:
            _, adjusted_neighbors = adaptive_masks(
                residual, path_rain, valid, neighbor_order, neighbor_distances, expanded=True
            )
            passes += (adjusted_neighbors,)
        for name, keep in zip(names[1:], passes, strict=True):
            if keep.sum() <= 3:
                continue
            adjustments = inter(
                q=target, z=np.where(keep, residual, np.nan), nnear=nnear,
                p=2, max_distance=60_000,
            )
            corrections = np.where(
                radar_wet > 0, np.clip(radar_wet + adjustments, 0, 150), radar_wet
            )
            models[name][i] = np.where(np.isfinite(corrections), corrections, radar_wet)
    return models


def divided(numerator, denominator):
    return numerator / denominator if denominator else float("nan")


def masked_mean(array, mask):
    return divided(np.sum(array[mask]), mask.sum())


def events(times, intensive, *, gap_hours=6):
    ids = np.full(len(times), -1, dtype=int)
    previous = None
    event = -1
    for index in np.flatnonzero(intensive.any(axis=1)):
        stamp = times[index]
        if previous is None or stamp - previous > np.timedelta64(gap_hours, "h"):
            event += 1
        ids[index] = event
        previous = stamp
    return ids


def confidence_by_event(delta, strong, labels):
    pairs_by_event = []
    sums_by_event = []
    for event in np.unique(labels[labels >= 0]):
        mask = strong & (labels[:, None] == event)
        pairs_by_event.append(int(mask.sum()))
        sums_by_event.append(float(delta[mask].sum()))
    if len(pairs_by_event) < 10:
        return np.nan, np.nan
    rng = np.random.default_rng(20261120)
    draws = rng.integers(len(pairs_by_event), size=(4000, len(pairs_by_event)))
    samples = np.asarray(sums_by_event)[draws].sum(axis=1) / np.asarray(pairs_by_event)[draws].sum(axis=1)
    return tuple(np.quantile(samples, [0.025, 0.975]))


def evaluate(ds, predictions, fixed, subset, name, max_distance):
    times = ds.time.values[subset]
    ref = ds.gauge_rate.transpose("time", "id").values[subset]
    relevant = gauge_coverage(ds) <= max_distance
    predictions = {key: values[subset] for key, values in predictions.items()}
    valid = relevant[None, :] & np.isfinite(ref)
    for values in predictions.values():
        valid &= np.isfinite(values)
    strong = valid & (ref >= 5)
    severe = valid & (ref >= 10)
    event_labels = events(times, strong)
    counter = len(np.unique(event_labels[event_labels >= 0]))
    fixed_error = np.abs(predictions[fixed] - ref)
    metrics = []
    for method, values in predictions.items():
        error = values - ref
        absolute = np.abs(error)
        alarm = valid & (values >= 5)
        true_positive = np.count_nonzero(alarm & strong)
        false_positive = np.count_nonzero(alarm & ~strong)
        interval = confidence_by_event(absolute - fixed_error, strong, event_labels)
        metrics.append({
            "recorte": name,
            "limite_distancia_km": max_distance / 1000,
            "metodo": method,
            "fixo_referencia": fixed,
            "pluviometros": int((valid.any(axis=0)).sum()),
            "pares": int(valid.sum()),
            "pares_5": int(strong.sum()),
            "pares_10": int(severe.sum()),
            "eventos_5": counter,
            "eam": masked_mean(absolute, valid),
            "eam_5": masked_mean(absolute, strong),
            "eam_10": masked_mean(absolute, severe),
            "vies_5": masked_mean(error, strong),
            "detectados_5": true_positive,
            "falsos_alarmes_5": false_positive,
            "taxa_falsos_alarmes_5": divided(false_positive, (valid & ~strong).sum()),
            "taxa_deteccao_5": divided(true_positive, strong.sum()),
            "delta_eam_5_vs_fixo": masked_mean(absolute - fixed_error, strong),
            "delta_ic025": interval[0],
            "delta_ic975": interval[1],
        })
    return metrics


def main(path, mode, fixed, output, *, extended=False):
    with xr.open_dataset(path) as source:
        ds = source.load()
    if not (ds.get_index("time").is_monotonic_increasing and ds.get_index("time").is_unique):
        raise ValueError("Horários devem ser crescentes e únicos")
    predictions = predict(ds, extended=extended)
    all_hours = np.ones(ds.sizes["time"], dtype=bool)
    max_distance = 20_000
    if mode == "sweden":
        june_july = ds.time.values <= np.datetime64("2015-08-01T00:00")
        development = evaluate(ds, predictions, "fixo_10", june_july, "SE junho–julho", max_distance)
        selected = min(
            (r for r in development if r["metodo"] in FIXED),
            key=lambda r: r["eam_5"],
        )["metodo"]
        output_records = (
            evaluate(ds, predictions, selected, june_july, "SE junho–julho", max_distance)
            + evaluate(ds, predictions, selected, ~june_july, "SE agosto", max_distance)
        )
        print(f"Fixo selecionado na Suécia: {selected}", flush=True)
    else:
        output_records = evaluate(ds, predictions, fixed, all_hours, mode, max_distance)
    summary = pd.DataFrame(output_records)
    print(summary[[
        "recorte", "metodo", "pares", "pares_5", "eventos_5", "eam_5", "eam_10",
        "vies_5", "falsos_alarmes_5", "taxa_deteccao_5", "delta_ic025", "delta_ic975",
    ]].to_string(index=False, float_format=lambda v: f"{v:.4f}"))
    summary.to_csv(output, index=False, float_format="%.8f")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("mode", help="sweden para separar desenvolvimento e agosto, ou nome do recorte")
    parser.add_argument("output", type=Path)
    parser.add_argument("--fixed", default="fixo_10", choices=FIXED)
    parser.add_argument("--extended", action="store_true", help="Inclui a variante de raio ampliado")
    args = parser.parse_args()
    main(args.input, args.mode, args.fixed, args.output, extended=args.extended)
