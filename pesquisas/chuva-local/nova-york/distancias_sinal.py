"""Mede distâncias até enlaces disponíveis e compara retornos ao radar."""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

from avaliar_validacao import evaluate, gauge_coverage, gauge_to_link_distance, predict


def active_distance(ds):
    geometry = gauge_to_link_distance(ds)
    path = ds.radar_at_link.transpose("time", "cml_id").values
    estimates = ds.link_rate.transpose("time", "cml_id").values
    usable = (path > 0) & np.isfinite(estimates)
    return np.min(np.where(usable[:, None, :], geometry[None, :, :], np.inf), axis=2)


def assess(ds, name):
    dist = active_distance(ds)
    results = predict(ds)
    raw, full = results["radar"], results["sem_filtro"]
    fields = {
        "radar": raw, "fusão sem limite": full,
        "fusão até 5 km do sinal": np.where(dist <= 5000, full, raw),
        "fusão até 10 km do sinal": np.where(dist <= 10_000, full, raw),
    }
    strong = (
        np.isfinite(raw) & (ds.gauge_rate.transpose("time", "id").values >= 5)
        & (gauge_coverage(ds)[None, :] <= 20_000)
    )
    classified = pd.Series(np.select(
        [dist[strong] <= 5000, dist[strong] <= 10_000, np.isfinite(dist[strong])],
        ["até 5 km", "5 a 10 km", "acima de 10 km"], default="sem sinal disponível",
    )).value_counts()
    print(name, classified.to_dict(), flush=True)
    return evaluate(ds, fields, "radar", np.ones(len(ds.time), dtype=bool), name, 20_000)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pairs", type=Path, nargs="+")
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    rows = []
    for path in args.pairs:
        rows.extend(assess(xr.load_dataset(path), path.stem))
    result = pd.DataFrame(rows)
    print(result[["recorte", "metodo", "pares_5", "eam_5", "detectados_5",
                  "falsos_alarmes_5", "delta_ic025", "delta_ic975"]].to_string(index=False))
    result.to_csv(args.output,index=False,float_format="%.8f")
