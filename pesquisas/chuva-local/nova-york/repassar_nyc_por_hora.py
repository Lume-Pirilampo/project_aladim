"""Repete a cadeia OpenMesh com o sinal visível em cada hora e após 30 minutos."""
import argparse
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import xarray as xr

from preparar_nyc import candidates, rain_chain

TEST_DELAYS = (0, 30)
DATA = {}


def initialize(openmesh, ids, first, last):
    with xr.open_dataset(openmesh / "data/links/openmesh_links.nc") as source:
        links, radio = candidates(source)
        links, radio = links.sel(cml_id=ids), radio.sel(cml_id=ids)
        signal = links[["rsl", "rsl_avg"]].sel(
            time=slice(first - pd.Timedelta(days=1), last + pd.Timedelta(minutes=30))
        ).load()
        paths = links.length.to_series().rename("length").to_frame()
    DATA.update(signal=signal, radio=radio, paths=paths)


def retrieve_hour(stamp, delay):
    day = stamp.normalize()
    visible = DATA["signal"].sel(time=slice(
        day - pd.Timedelta(days=1), stamp + pd.Timedelta(minutes=delay)
    ))
    enough_signal = visible.rsl.notnull().mean("time") > 0.3
    usable = DATA["radio"] & enough_signal
    links = visible.cml_id.values
    context = SimpleNamespace(links=visible, paths=DATA["paths"])
    rates = np.full(len(links), np.nan)
    interval = slice(stamp - pd.Timedelta(minutes=59), stamp)
    for index in np.flatnonzero(usable.any("sublink_id").values):
        key = links[index]
        selection = visible.sublink_id.values[usable.sel(cml_id=key).values]
        estimate = rain_chain(context, key, day, sublinks=selection, wet_method="rsd").R
        estimate = estimate.sel(time=interval)
        valid_directions = estimate.count("time") >= 30
        rates[index] = estimate.mean("time").where(valid_directions).mean().item()
    return rates


def replay_day(stamps):
    results = {delay: np.stack([retrieve_hour(stamp, delay) for stamp in stamps]) for delay in TEST_DELAYS}
    return stamps, results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("openmesh", type=Path)
    parser.add_argument("original_pairs", type=Path)
    parser.add_argument("output_prefix", type=Path)
    parser.add_argument("--days", type=int)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    pairs = xr.load_dataset(args.original_pairs)
    times = pd.DatetimeIndex(pairs.time.values)
    times = times[times.hour != 0]
    dates = times.normalize().unique()
    if args.days:
        dates = dates[:args.days]
    batches = [list(times[times.normalize() == date]) for date in dates]
    results = {delay: [] for delay in TEST_DELAYS}
    final_times = []
    with ProcessPoolExecutor(
        max_workers=args.workers, initializer=initialize,
        initargs=(args.openmesh, pairs.cml_id.values, dates[0], max(batches[-1])),
    ) as pool:
        for count, (stamps, rates) in enumerate(pool.map(replay_day, batches), start=1):
            final_times.extend(stamps)
            for delay in TEST_DELAYS:
                results[delay].append(rates[delay])
            if count in (1, len(batches)) or count % 5 == 0:
                print(f"{count}/{len(batches)} dias de sinais repassados", flush=True)
    final = pairs.sel(time=pd.DatetimeIndex(final_times))
    coordinates = {"time": final.time, "cml_id": final.cml_id}
    final.to_netcdf(f"{args.output_prefix}-retrospectivo.nc")
    for delay in TEST_DELAYS:
        final = final.assign(link_rate=xr.DataArray(
            np.concatenate(results[delay]), coords=coordinates, dims=("time", "cml_id")
        ))
        final.attrs.update(telemetry_cutoff_minutes=delay)
        final.to_netcdf(f"{args.output_prefix}-{delay}min.nc")
