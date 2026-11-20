"""Avalia campos arquivados pelos autores nos mesmos pares válidos do estudo."""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree
import xarray as xr

from avaliar_validacao import coordinates, evaluate, predict


def read_nearest_cells(path, ds):
    with xr.open_dataset(path) as source:
        common = np.intersect1d(source.time.values, ds.time.values)
        radar_xy = np.column_stack((source.y_grid.values.ravel(), source.x_grid.values.ravel()))
        distance, nearest = cKDTree(radar_xy).query(coordinates(ds, "target_x", "target_y"))
        if distance.max() > 1.0:
            raise ValueError(f"{path.name}: malha publicada não coincide com a malha de avaliação")
        y, x = np.unravel_index(nearest, source.x_grid.shape)
        rain = source.rainfall.sel(time=common)
        parts = []
        for start in range(0, len(common), 36):
            part = rain.isel(time=slice(start, start + 36)).transpose("time", "y", "x")
            parts.append(part.values[:, y, x])
    common_fields = xr.DataArray(
        np.concatenate(parts), coords={"time": common, "id": ds.id.values}, dims=("time", "id")
    )
    return common_fields.reindex(time=ds.time).values


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pairs", type=Path)
    parser.add_argument("region", choices=("SE", "IT"))
    parser.add_argument("additive", type=Path)
    parser.add_argument("kriging", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    ds = xr.load_dataset(args.pairs)
    if args.region == "SE":
        ds = ds.sel(time=ds.time > np.datetime64("2015-08-01T00:00"))
    predictions = predict(ds)
    predictions["aditivo_publicado"] = read_nearest_cells(args.additive, ds)
    predictions["ked_publicado"] = read_nearest_cells(args.kriging, ds)
    records = evaluate(
        ds, predictions, "fixo_10", np.ones(ds.sizes["time"], dtype=bool),
        args.region, 20_000,
    )
    report = pd.DataFrame(records)
    print(report[["recorte", "metodo", "pares", "pares_5", "eam_5", "eam_10",
                  "falsos_alarmes_5", "taxa_deteccao_5", "delta_ic025", "delta_ic975"]]
          .to_string(index=False, float_format=lambda v: f"{v:.4f}"))
    report.to_csv(args.output, index=False, float_format="%.8f")
