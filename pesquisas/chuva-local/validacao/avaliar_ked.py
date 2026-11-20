"""Executa os filtros no KED do mergeplg só nas células usadas para avaliação."""
import argparse
from pathlib import Path

from mergeplg import bk_functions
import numpy as np
import pandas as pd
from scipy.spatial.distance import cdist
import xarray as xr

from avaliar_validacao import METHODS, adaptive_masks, coordinates, evaluate

MODEL = {"nugget": 0.3, "psill": 0.7, "range": 30_000}


def predict_ked(ds, *, full_line, extended=False, directional=False):
    links = coordinates(ds, "link_x", "link_y")
    target = coordinates(ds, "target_x", "target_y")
    variogram = bk_functions.construct_variogram(
        np.zeros(len(links)), links, MODEL, "spherical"
    )
    interpolation = bk_functions.BKEDTree(
        variogram, target[:, 0], target[:, 1], ds_cmls=ds,
        nnear=70, max_distance=60_000, full_line=full_line,
    )
    distances = cdist(links, links)
    np.fill_diagonal(distances, np.inf)
    neighbors = np.argsort(distances, axis=1, kind="stable")
    neighbor_distances = np.take_along_axis(distances, neighbors, axis=1)

    path = ds.radar_at_link.transpose("time", "cml_id").values
    estimates = ds.link_rate.transpose("time", "cml_id").values
    raw = ds.radar_at_gauge.transpose("time", "id").values
    names = METHODS + (("alcance_adaptativo",) if extended else ())
    if directional:
        q = ds.link_disagreement.transpose("time", "cml_id").values
        uncertainty = 0.3 * (1 + np.minimum(9, np.nan_to_num(q, nan=0) ** 2))
        names += ("incerteza_dupla",)
    models = {key: raw.copy() for key in names}

    for hour, (path_rain, link_rain, gauge_cell) in enumerate(zip(path, estimates, raw, strict=True)):
        residual = link_rain - path_rain
        valid = (path_rain > 0) & np.isfinite(residual)
        if valid.sum() <= 3:
            continue
        intensity, local = adaptive_masks(residual, path_rain, valid, neighbors, neighbor_distances)
        passes = (valid, valid & (np.abs(residual) <= 5),
                  valid & (np.abs(residual) <= 10), intensity, local)
        if extended:
            _, radius = adaptive_masks(
                residual, path_rain, valid, neighbors, neighbor_distances, expanded=True
            )
            passes += (radius,)
        if directional:
            passes += (passes[2],)
        radar = np.where(gauge_cell > 0.01, gauge_cell, 0)
        for key, keep in zip(names[1:], passes, strict=True):
            if keep.sum() <= 3:
                continue
            sigma = uncertainty[hour] if key == "incerteza_dupla" else None
            merged, _ = interpolation(radar, np.where(keep, link_rain, np.nan), path_rain, sigma)
            merged = np.where(radar > 0, np.clip(merged, 0, 150), 0)
            merged = np.where(np.isfinite(merged), merged, radar)
            models[key][hour] = np.where(np.isfinite(gauge_cell), merged, np.nan)
    return models


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pairs", type=Path)
    parser.add_argument("region", help="SE separa agosto. Outras etiquetas avaliam toda a série.")
    parser.add_argument("geometry", choices=("ponto", "bloco"))
    parser.add_argument("output", type=Path)
    parser.add_argument("--extended", action="store_true")
    parser.add_argument("--directional", action="store_true", help="Usa discordância entre sentidos")
    args = parser.parse_args()
    ds = xr.load_dataset(args.pairs)
    if args.region == "SE":
        ds = ds.sel(time=ds.time > np.datetime64("2015-08-01T00:00"))
    result = predict_ked(
        ds, full_line=(args.geometry == "bloco"), extended=args.extended,
        directional=args.directional,
    )
    records = evaluate(
        ds, result, "fixo_10", np.ones(ds.sizes["time"], dtype=bool),
        f"{args.region}, KED {args.geometry}", 20_000,
    )
    report = pd.DataFrame(records)
    print(report[["recorte", "metodo", "pares_5", "eventos_5", "eam_5", "eam_10",
                  "falsos_alarmes_5", "taxa_deteccao_5", "delta_ic025", "delta_ic975"]]
          .to_string(index=False, float_format=lambda v: f"{v:.4f}"), flush=True)
    report.to_csv(args.output, index=False, float_format="%.8f")
