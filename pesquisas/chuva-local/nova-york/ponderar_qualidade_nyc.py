"""Testa se a qualidade horária do MRMS é informativa para modular a fusão."""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree
import xarray as xr

from avaliar_validacao import coordinates, evaluate, predict
from preparar_validacao import normalize_italy_radar, projected


def get_quality(paths, ds):
    parts = []
    for path in paths:
        with xr.open_dataset(path) as file:
            layer = normalize_italy_radar(file.RadarQualityIndex)
            gx, gy = projected(layer, "lon", "lat", "EPSG:32618")
            points = np.column_stack((gy.values.ravel(), gx.values.ravel()))
            distances, nearest = cKDTree(points).query(coordinates(ds, "target_x", "target_y"))
            if distances.max() > 2:
                raise ValueError(f"A malha do índice diverge da precipitação em {path.name}")
            y, x = np.unravel_index(nearest, gx.shape)
            samples = layer.transpose("time", "y", "x").values[:, y, x]
            parts.append(xr.DataArray(samples, dims=("time", "id"),
                                      coords={"time": layer.time, "id": ds.id}))
    values = xr.concat(parts, dim="time").reindex(time=ds.time).values
    finite = values[np.isfinite(values)]
    if not finite.size or finite.min() < 0 or finite.max() > 1:
        raise ValueError("Qualidade ausente ou fora da escala documentada")
    return values


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pairs", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("quality", nargs="+", type=Path)
    args = parser.parse_args()
    ds = xr.load_dataset(args.pairs)
    quality = get_quality(args.quality, ds)
    results = predict(ds)
    raw, blended = results["radar"], results["sem_filtro"]
    weight = 1 - quality
    constant = float(np.nanmean(weight))
    correction = blended - raw
    estimates = {
        "radar": raw, "fusão plena": blended,
        "peso médio": raw + constant * correction,
        "peso do índice NOAA": raw + weight * correction,
    }
    selected = np.ones(ds.sizes["time"], dtype=bool)
    rows = evaluate(ds, estimates, "peso médio", selected, "NYC abril e julho", 20_000)
    report = pd.DataFrame(rows)
    print("Peso médio:", constant, "Desvio padrão:", np.nanstd(weight),
          "Índice carregado:", int(np.isfinite(quality).sum()), "/", quality.size)
    print(report[["metodo","pares","pares_5","eventos_5","eam_5","falsos_alarmes_5",
                  "detectados_5","delta_ic025","delta_ic975"]].to_string(index=False))
    report.to_csv(args.output, index=False, float_format="%.8f")
