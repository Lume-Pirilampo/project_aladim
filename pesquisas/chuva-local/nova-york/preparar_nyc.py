"""Prepara OpenMesh 2.0, radar NOAA sem pluviômetros e estações ASOS."""
import argparse
from contextlib import nullcontext
from functools import partial
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
import pandas as pd
import xarray as xr

import showcase
from showcase import fill_blackouts as original_fill_blackouts, rain_chain

from preparar_validacao import HOURLY, normalize_italy_radar, project_links, raster_reference

NYC_CRS = "EPSG:32618"
RAIN_PRODUCT = "RadarOnly_QPE_01H"


def candidates(links):
    polar = np.char.lower(links.polarization.values.astype(str))
    valid_polar = np.isin(polar, ["h", "v", "horizontal", "vertical"])
    usable = (links.frequency >= 24_000) & valid_polar
    cutoff = usable.any("sublink_id") & (links.length > 0)
    return links.sel(cml_id=cutoff), usable.sel(cml_id=cutoff)


def hourly_gauges(asos, start, end, include_flag2):
    times = slice(start - pd.Timedelta(hours=1), end)
    rain = asos.rainfall_amount.sel(time=times)
    flag = asos.rainfall_flag.sel(time=times)
    valid_codes = [0, 2] if include_flag2 else [0]
    valid = flag.isin(valid_codes) & (rain >= 0)
    count_flag2 = int((flag == 2).sum())
    groups = rain.where(valid).resample(**HOURLY)
    return groups.sum().where(groups.count() == 60).rename("gauge_rate"), count_flag2


def bounded_blackouts(level, db_above_min, *, max_minutes):
    filled, marked = original_fill_blackouts(level, db_above_min)
    retained = marked.values.copy()
    for line in retained:
        changes = np.diff(np.r_[False, line, False].astype("int8"))
        starts = np.flatnonzero(changes == 1)
        stops = np.flatnonzero(changes == -1)
        for start, stop in zip(starts, stops, strict=True):
            if stop - start > max_minutes:
                line[start:stop] = False
    short = marked.copy(data=retained)
    return filled.where(~marked | short), short


def hourly_links(links, usable, start, end, blackout_db):
    days = pd.date_range((start - pd.Timedelta(hours=1)).normalize(), end.normalize())
    signal = links[["rsl", "rsl_avg"]].sel(
        time=slice(days[0] - pd.Timedelta(days=1), days[-1] + pd.Timedelta(days=1))
    ).load()
    paths = links.length.to_series().rename("length").to_frame()
    context = SimpleNamespace(links=signal, paths=paths)
    by_day = []
    for i, day in enumerate(days, start=1):
        span = slice(day - pd.Timedelta(days=1), day + pd.Timedelta(days=1))
        availability = signal.rsl.sel(time=span).notnull().mean("time")
        mask = usable & (availability > 0.3)
        sublinks = []
        for key in links.cml_id.values[mask.any("sublink_id").values]:
            names = links.sublink_id.values[mask.sel(cml_id=key).values]
            rain = rain_chain(
                context, key, day, sublinks=names, wet_method="rsd", blackout_db=blackout_db,
            )[["R", "blackout"]]
            rain = rain.squeeze("cml_id", drop=True) if "cml_id" in rain.dims else rain
            sublinks.append(rain.reset_coords(drop=True).expand_dims(cml_id=[key]))
        if sublinks:
            by_day.append(xr.concat(sublinks, dim="cml_id", join="outer"))
        if i % 10 == 0:
            print(f"Enlaces: {i}/{len(days)} dias", flush=True)
    if not by_day:
        raise ValueError("Sem subenlaces de micro-ondas com sinal disponível no intervalo")
    direct = xr.concat(by_day, dim="time", join="outer").sortby("time").drop_duplicates("time")
    direct = direct.reindex(cml_id=links.cml_id)
    hours = direct.R.resample(**HOURLY)
    enough = hours.count() >= 30
    rate = hours.mean().where(enough).mean("sublink_id")
    used_fill = direct.blackout.fillna(0).where(direct.R.notnull(), 0)
    filled_minutes = used_fill.resample(**HOURLY).sum().where(enough, 0).sum("sublink_id")
    measured_minutes = (signal.rsl.notnull() & usable).sum("sublink_id").resample(**HOURLY).sum()
    measured_share = measured_minutes / (60 * usable.sum("sublink_id"))
    return xr.Dataset({
        "link_rate": rate, "measured_share": measured_share.reindex(time=rate.time),
        "filled_minutes": filled_minutes,
    })


def prepare_unit(radar_file, links, usable, asos, include_flag2, blackout_db):
    radar = normalize_italy_radar(xr.load_dataset(radar_file)[RAIN_PRODUCT])
    start, end = (pd.Timestamp(radar.time.values[i]) for i in (0, -1))
    gauges, flags = hourly_gauges(asos, start, end, include_flag2)
    geo, _ = raster_reference(radar, links, gauges, 60, crs=NYC_CRS)
    rates = hourly_links(links, usable, start, end, blackout_db)
    common = xr.merge((geo, rates, gauges), join="inner", compat="no_conflicts")
    # Mantém todas as horas efetivamente obtidas na janela de radar.
    common = common.sel(time=radar.time.values)
    print(radar_file.name, dict(common.sizes), "minutos ASOS com flag 2:", flags, flush=True)
    print("Enlaces com ao menos uma hora:", int(common.link_rate.notnull().any("time").sum()), flush=True)
    return common


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("openmesh", type=Path)
    parser.add_argument("radar", type=Path, nargs="+")
    parser.add_argument("output", type=Path)
    parser.add_argument("--include-flag2", action="store_true")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--without-blackout-fill", action="store_true")
    mode.add_argument("--max-blackout-min", type=int)
    args = parser.parse_args()
    if args.max_blackout_min is not None and args.max_blackout_min < 1:
        parser.error("--max-blackout-min deve ser positivo")
    override = nullcontext() if args.max_blackout_min is None else patch.object(
        showcase, "fill_blackouts", partial(bounded_blackouts, max_minutes=args.max_blackout_min)
    )
    record = args.openmesh / "data"
    with (
        override,
        xr.open_dataset(record / "links/openmesh_links.nc") as source,
        xr.open_dataset(record / "weather/asos/openmesh_asos.nc") as asos,
    ):
        links, eligible = candidates(source)
        links = project_links(links, crs=NYC_CRS)
        outputs = [
            prepare_unit(f, links, eligible, asos, args.include_flag2,
                         None if args.without_blackout_fill else 6)
            for f in args.radar
        ]
    pairs = xr.concat(outputs, dim="time", data_vars="minimal", coords="minimal", compat="equals").sortby("time")
    if not pairs.get_index("time").is_unique:
        raise ValueError("Janelas de avaliação sobrepostas")
    pairs.to_netcdf(args.output, encoding={
        name: {"zlib": True, "complevel": 3} for name in pairs.data_vars
    })
