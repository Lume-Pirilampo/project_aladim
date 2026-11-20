"""Mede a resposta dos filtros a subconjuntos aninhados de enlaces."""
import argparse
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.spatial.distance import cdist
import xarray as xr

from avaliar_validacao import coordinates, evaluate, predict

FRACTIONS = (0.10, 0.25, 0.50, 0.75)
SHARED = {}


def initialize(input_path, region, fixed):
    with xr.open_dataset(input_path) as source:
        if region == "SE":
            source = source.sel(time=source.time > np.datetime64("2015-08-01T00:00"))
        dataset = source.load()
    SHARED.update(dataset=dataset, region=region, fixed=fixed)


def local_support(dataset):
    xy = coordinates(dataset, "link_x", "link_y")
    adjacent = cdist(xy, xy) <= 10_000
    np.fill_diagonal(adjacent, False)
    valid = (
        dataset.link_rate.notnull()
        & dataset.radar_at_link.notnull()
        & (dataset.radar_at_link > 0)
    ).transpose("time", "cml_id").values
    counts = valid.astype(np.int16) @ adjacent.astype(np.int16)
    total = np.count_nonzero(valid)
    return np.count_nonzero(valid & (counts >= 8)) / total if total else np.nan


def trial(job):
    replicate, fraction, indices = job
    full = SHARED["dataset"]
    thin = full.isel(cml_id=indices)
    predictions = predict(thin)
    result = evaluate(
        full, predictions, SHARED["fixed"], np.ones(full.sizes["time"], dtype=bool),
        SHARED["region"], 20_000,
    )
    support = local_support(thin)
    for row in result:
        row.update(
            replica=replicate, fracao=fraction, enlaces=len(indices),
            suporte_local=support,
        )
    return result


def jobs_for_network(size):
    rng = np.random.default_rng(20261120)
    yield 0, 1.0, np.arange(size)
    for replicate in range(1, 25):
        order = rng.permutation(size)
        for fraction in FRACTIONS:
            yield replicate, fraction, np.sort(order[:round(fraction * size)])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("region", choices=("SE", "IT"))
    parser.add_argument("fixed", choices=("fixo_5", "fixo_10"))
    parser.add_argument("output", type=Path)
    parser.add_argument("--workers", type=int, default=3)
    args = parser.parse_args()
    with xr.open_dataset(args.input) as source:
        size = source.sizes["cml_id"]
    rows = []
    with ProcessPoolExecutor(
        max_workers=args.workers, initializer=initialize,
        initargs=(args.input, args.region, args.fixed),
    ) as pool:
        for i, part in enumerate(pool.map(trial, jobs_for_network(size)), start=1):
            rows.extend(part)
            if i % 12 == 1:
                print(f"{args.region}: {i}/97 combinações executadas", flush=True)
    table = pd.DataFrame(rows)
    table.to_csv(args.output, index=False, float_format="%.8f")
    grouped = table.groupby(["fracao", "metodo"])[["delta_eam_5_vs_fixo", "suporte_local"]]
    print(grouped.median().to_string(float_format=lambda value: f"{value:.4f}"))
