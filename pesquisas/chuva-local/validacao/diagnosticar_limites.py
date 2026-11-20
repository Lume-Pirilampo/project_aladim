"""Mede o que uma troca do limite fixo pode ganhar por tempestade, retrospectivamente."""
import argparse
from pathlib import Path

from mergeplg.radolan.idw import Invdisttree
import numpy as np
import pandas as pd
import xarray as xr

from avaliar_validacao import coordinates, events, gauge_coverage, masked_mean

LIMITS = (2, 3, 5, 7.5, 10, 12.5, 15, 20, 30, 50, np.inf)


def sweep(ds):
    link_xy = coordinates(ds, "link_x", "link_y")
    target = coordinates(ds, "target_x", "target_y")
    interpolation = Invdisttree(link_xy)
    radar = ds.radar_at_gauge.transpose("time", "id").values
    path = ds.radar_at_link.transpose("time", "cml_id").values
    links = ds.link_rate.transpose("time", "cml_id").values
    forecasts = {limit: radar.copy() for limit in LIMITS}
    for i, (ref, link, cell) in enumerate(zip(path, links, radar, strict=True)):
        residual = link - ref
        good = np.isfinite(residual) & (ref > 0)
        if good.sum() <= 3:
            continue
        wet = np.where(cell > 0.01, cell, 0)
        for bound, prediction in forecasts.items():
            included = good & (np.abs(residual) <= bound)
            if included.sum() <= 3:
                continue
            correction = interpolation(
                q=target, z=np.where(included, residual, np.nan),
                nnear=min(70, len(link_xy)), p=2, max_distance=60_000,
            )
            adjusted = np.where(wet > 0, np.clip(wet + correction, 0, 150), wet)
            prediction[i] = np.where(np.isfinite(cell), np.where(np.isfinite(adjusted), adjusted, wet), np.nan)
    return forecasts


def assess(ds, forecasts):
    rain = ds.gauge_rate.transpose("time", "id").values
    common = np.isfinite(rain) & (gauge_coverage(ds)[None, :] <= 20_000)
    for predicted in forecasts.values():
        common &= np.isfinite(predicted)
    strong = common & (rain >= 5)
    labels = events(ds.time.values, strong)
    errors = {bound: np.abs(values - rain) for bound, values in forecasts.items()}
    rows = []
    for limit, error in errors.items():
        fp = np.count_nonzero(common & ~strong & (forecasts[limit] >= 5))
        rows.append({
            "limite_mm_h": limit,
            "eam_5": masked_mean(error, strong),
            "eam_10": masked_mean(error, common & (rain >= 10)),
            "taxa_fp": fp / (common & ~strong).sum(),
            "taxa_deteccao": np.count_nonzero(strong & (forecasts[limit] >= 5)) / strong.sum(),
        })
    event_rows = []
    for e in np.unique(labels[labels >= 0]):
        mask = strong & (labels[:, None] == e)
        error = {k: array[mask].sum() for k, array in errors.items()}
        min_limit = min(error, key=error.get)
        event_rows.append({
            "evento": e + 1,
            "primeira_hora_utc": str(ds.time.values[np.flatnonzero(labels == e)[0]]),
            "pares_5": int(mask.sum()),
            "limite_otimo_retrospectivo": min_limit,
            "erro_fixo_10": error[10],
            "erro_otimo_retrospectivo": error[min_limit],
        })
    return pd.DataFrame(rows), pd.DataFrame(event_rows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pairs", type=Path)
    parser.add_argument("label")
    parser.add_argument("output_prefix", type=Path)
    args = parser.parse_args()
    ds = xr.load_dataset(args.pairs)
    if args.label == "SE":
        ds = ds.sel(time=ds.time > np.datetime64("2015-08-01T00:00"))
    summary, event = assess(ds, sweep(ds))
    print(args.label, flush=True)
    print(summary.to_string(index=False, float_format=lambda v: f"{v:.4f}"))
    print("Eventos:", len(event), "EAM limite escolhido a posteriori:",
          round(event.erro_otimo_retrospectivo.sum() / event.pares_5.sum(), 4))
    summary.to_csv(args.output_prefix.with_suffix(".csv"), index=False, float_format="%.8f")
    event.to_csv(
        args.output_prefix.with_name(args.output_prefix.name + "_eventos").with_suffix(".csv"),
        index=False, float_format="%.8f",
    )
