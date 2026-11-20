"""Compara radar e fusão em pluviômetros comunitários com observações de cinco minutos."""
import argparse
from pathlib import Path

import netCDF4
import numpy as np
import pandas as pd
import xarray as xr

from avaliar_validacao import evaluate, predict
from distancias_sinal import active_distance
from preparar_nyc import NYC_CRS, RAIN_PRODUCT
from preparar_validacao import HOURLY, normalize_italy_radar, raster_reference


def station_hours(station, times, jitter_minutes):
    data = station.rainfall_amount.squeeze("id", drop=True).sel(
        time=slice(times[0] - pd.Timedelta(hours=1), times[-1] + pd.Timedelta(minutes=2))
    )
    if data.attrs.get("units") != "mm":
        raise ValueError("Unidade inesperada de precipitação")
    steps = data.to_series()
    nominal = steps.index.round("5min")
    valid = (
        np.isfinite(steps) & (steps >= 0)
        & (abs(steps.index - nominal) <= pd.Timedelta(minutes=jitter_minutes))
    )
    steps = pd.Series(steps.where(valid).values, index=nominal)
    # Duas amostras na mesma marca deixam o intervalo ambíguo.
    steps = steps.loc[~steps.index.duplicated(keep=False)]
    grouped = steps.resample("1h", closed=HOURLY["closed"], label=HOURLY["label"])
    return grouped.sum(min_count=12).reindex(times)


def load_gauges(path, times, jitter_minutes):
    result = []
    with netCDF4.Dataset(path) as source:
        groups = list(source.groups)
    for group in groups:
        with xr.open_dataset(path, group=group) as station:
            hours = station_hours(station, times, jitter_minutes)
            result.append(xr.DataArray(
                hours.values, dims=("time",), coords={"time": times}, name="gauge_rate",
            ).expand_dims(id=[group]).assign_coords(
                lat=("id", [station.lat.item()]), lon=("id", [station.lon.item()]),
            ))
    out = xr.concat(result, dim="id")
    return out.sel(id=out.notnull().any("time") & np.isfinite(out.lat) & np.isfinite(out.lon))


def prepare_panel(raw_links, radar, gauges):
    geo, _ = raster_reference(radar, raw_links, gauges, 60, crs=NYC_CRS)
    path = geo.radar_at_link.sel(time=raw_links.time)
    xr.testing.assert_allclose(
        path.reset_coords(drop=True), raw_links.radar_at_link.reset_coords(drop=True)
    )
    return xr.merge(
        (geo, raw_links[["link_rate"]], gauges), join="inner", compat="no_conflicts"
    )


def evaluate_network(ds, jitter_minutes):
    estimates = predict(ds)
    nearest = active_distance(ds)
    strong = (ds.gauge_rate.transpose("time", "id").values >= 5)
    raw = estimates["radar"]
    subsets = (
        ("todos com geometria até 20 km", np.ones_like(nearest, dtype=bool)),
        ("até 5 km de enlace ativo", nearest <= 5000),
        ("5 a 10 km de enlace ativo", (nearest > 5000) & (nearest <= 10_000)),
        ("acima de 10 km ou sem enlace ativo", nearest > 10_000),
    )
    rows = []
    for label, eligible in subsets:
        observations = ds.gauge_rate.transpose("time", "id")
        filtered = ds.assign(gauge_rate=observations.where(eligible))
        stats = evaluate(
            filtered, estimates, "radar", np.ones(len(ds.time), dtype=bool), label, 20_000
        )
        for row in stats:
            row["jitter_minutos"] = jitter_minutes
        rows.extend(stats)
    nearest_all = (ds.gauge_rate.transpose("time", "id").notnull() & np.isfinite(raw)).values
    group = (nearest <= 5000) & nearest_all & strong
    near = np.abs(raw - ds.gauge_rate.transpose("time", "id").values)[group]
    print(
        f"Tolerância {jitter_minutes} min, {len(ds.id)} estações com cobertura. "
        f"Erro mediano do radar nos {len(near)} pares fortes próximos: "
        f"{np.median(near) if len(near) else float('nan'):.3f} mm", flush=True
    )
    return rows


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pws", type=Path)
    parser.add_argument("pairs", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("radar", type=Path, nargs="+")
    args = parser.parse_args()
    links = xr.load_dataset(args.pairs).drop_dims("id")
    radar = xr.concat(
        [normalize_italy_radar(xr.load_dataset(path)[RAIN_PRODUCT]) for path in args.radar],
        dim="time", coords="minimal", compat="equals",
    ).sortby("time")
    if not radar.get_index("time").is_unique:
        raise ValueError("Janelas de radar sobrepostas")
    rows = []
    for tolerance in (2, 1):
        gauges = load_gauges(args.pws, links.get_index("time"), tolerance)
        rows.extend(evaluate_network(prepare_panel(links, radar, gauges), tolerance))
    report = pd.DataFrame(rows)
    report.to_csv(args.output, index=False, float_format="%.8f")
    print(report[["jitter_minutos", "recorte", "metodo", "pluviometros", "pares", "pares_5",
                  "eventos_5", "eam_5", "detectados_5", "falsos_alarmes_5",
                  "delta_ic025", "delta_ic975"]].to_string(index=False))
