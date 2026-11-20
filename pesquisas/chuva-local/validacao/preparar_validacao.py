"""Prepara pares horários radar–enlace e radar–pluviômetro para validação."""
import argparse
from pathlib import Path

import bottleneck as bn
import numpy as np
import pandas as pd
import poligrain as plg
import pycomlink as pc
from pyproj import Transformer
from scipy.ndimage import binary_dilation
from scipy.sparse import csr_matrix
from scipy.spatial import cKDTree
import xarray as xr

HOURLY = dict(time="1h", closed="right", label="right")
CRS = "EPSG:32632"
STEREO = "+proj=stere +lat_ts=60 +ellps=bessel +lon_0=14 +lat_0=90"


def projected(ds, lon, lat):
    return plg.spatial.project_point_coordinates(ds[lon], ds[lat], CRS)


def project_links(links):
    start_x, start_y = projected(links, "site_0_lon", "site_0_lat")
    end_x, end_y = projected(links, "site_1_lon", "site_1_lat")
    return links.assign_coords(
        site_0_x=start_x, site_0_y=start_y, site_1_x=end_x, site_1_y=end_y,
        link_x=(start_x + end_x) / 2, link_y=(start_y + end_y) / 2,
    )


def normalize_italy_radar(radar):
    if radar.lon.ndim == 1:
        lon, lat = np.meshgrid(radar.lon.values, radar.lat.values)
        radar = radar.rename({"lon": "x", "lat": "y"})
        radar = radar.assign_coords(lon=(("y", "x"), lon), lat=(("y", "x"), lat))
    return radar


def radar_slices(radar, minutes, weights, cell_indices):
    """Calcula radar nos enlaces e nas células dos pluviômetros sem reter todo o volume."""
    dates = pd.DatetimeIndex(radar.time.values)
    if not dates.is_unique or not dates.is_monotonic_increasing:
        raise ValueError("Horários de radar devem ser únicos e crescentes")
    rows, cols = cell_indices
    path_parts = []
    gauge_parts = []
    hourly_link_parts = []
    full_time = pd.date_range(dates[0].floor("D"), dates[-1].ceil("D"), freq=f"{minutes}min")
    last_day = full_time[-1] - pd.Timedelta(days=1)
    for day in pd.date_range(full_time[0], last_day, freq="D"):
        # O dia rotulado inclui o instante final, excluindo o instante inicial.
        times = full_time[(full_time > day) & (full_time <= day + pd.Timedelta(days=1))]
        chunk = radar.sel(time=slice(times[0], times[-1])).reindex(time=times)
        block = chunk.transpose("time", "y", "x").values.astype("f")
        block[(block < 0) | (~np.isfinite(block))] = np.nan
        steps_per_hour = 60 // minutes
        valid = np.isfinite(block)
        by_hour = block.reshape(-1, steps_per_hour, *block.shape[1:])
        coverage = valid.reshape(by_hour.shape).sum(axis=1)
        hourly = np.where(
            coverage == steps_per_hour,
            np.nansum(by_hour, axis=1) * minutes / 60,
            np.nan,
        )
        # mergeplg aplica o limiar às células antes de calcular a taxa no enlace.
        wet_hourly = np.where(np.isfinite(hourly), np.where(hourly > 0.01, hourly, 0), np.nan)
        at_links = (weights @ block.reshape(len(block), -1).T).T
        hourly_at_links = (weights @ wet_hourly.reshape(len(hourly), -1).T).T
        path_parts.append(at_links)
        gauge_parts.append(hourly[:, rows, cols])
        hourly_link_parts.append(hourly_at_links)
    times = full_time[1:]
    return (
        times,
        np.concatenate(path_parts),
        np.concatenate(gauge_parts),
        np.concatenate(hourly_link_parts),
    )


def raster_reference(radar, links, gauges, minutes):
    grid_x, grid_y = projected(radar, "lon", "lat")
    gauge_x, gauge_y = projected(gauges, "lon", "lat")
    grid_xy = np.column_stack((grid_x.values.ravel(), grid_y.values.ravel()))
    distances, cells = cKDTree(grid_xy).query(np.column_stack((gauge_x, gauge_y)))
    rows, cols = np.unravel_index(cells, grid_x.shape)
    if not np.isfinite(distances).all():
        raise ValueError("Pluviômetro sem célula de radar")
    weights = plg.spatial.calc_sparse_intersect_weights_for_several_cmls(
        x1_line=links.site_0_x.values, y1_line=links.site_0_y.values,
        x2_line=links.site_1_x.values, y2_line=links.site_1_y.values,
        cml_id=links.cml_id.values, x_grid=grid_x.values, y_grid=grid_y.values,
        grid_point_location="center",
    )
    intersections = weights.data.reshape((links.sizes["cml_id"], -1)).to_scipy_sparse()
    intersections = csr_matrix(intersections)
    times, path_rate, gauge_hour, path_hour = radar_slices(
        radar, minutes, intersections, (rows, cols)
    )
    no_support = np.asarray(intersections.sum(axis=1)).ravel() < 0.99
    path_rate[:, no_support] = np.nan
    path_hour[:, no_support] = np.nan
    hourly_time = times[(times.minute == 0)]
    hourly_labels = {"time": hourly_time, "cml_id": links.cml_id.values, "id": gauges.id.values}
    geo = xr.Dataset(
        data_vars={
            "radar_at_link": (("time", "cml_id"), path_hour),
            "radar_at_gauge": (("time", "id"), gauge_hour),
            "cell_distance": ("id", distances),
            "target_x": ("id", grid_x.values[rows, cols]),
            "target_y": ("id", grid_y.values[rows, cols]),
            "gauge_x": ("id", gauge_x.values),
            "gauge_y": ("id", gauge_y.values),
        },
        coords=hourly_labels,
    )
    geographic = {name: links[name] for name in (
        "site_0_x", "site_0_y", "site_1_x", "site_1_y", "link_x", "link_y"
    )}
    geo = geo.assign_coords(geographic)
    rates = xr.DataArray(
        path_rate, dims=("time", "cml_id"),
        coords={"time": times, "cml_id": links.cml_id}, name="radar_rate",
    )
    return geo, rates


def first_valid_in_minute(values):
    shape = values.shape
    grouped = values.reshape(shape[0] // 6, 6, *shape[1:])
    first = np.isfinite(grouped).argmax(axis=1, keepdims=True)
    return np.take_along_axis(grouped, first, axis=1)[:, 0]


def sweden_links(directory):
    meta = pd.read_csv(directory / "cml/cml_metadata.csv").set_index("Sublink")
    with xr.open_dataset(directory / "cml/cml.nc") as source:
        meta = meta.reindex(source.sublink.values)
        if meta["Direction"].isna().any():
            raise ValueError("Metadados não correspondem a todos os subenlaces")
        dimensions = ("time", "sublink")
        times = pd.DatetimeIndex(source.time.values)
        if not ((np.diff(times.values) == np.timedelta64(10, "s")).all()
                and (times[::6].second == 0).all()):
            raise ValueError("A grade original de 10 s precisa ser reindexada")
        # O último minuto do arquivo contém só o carimbo de fim da série.
        complete_samples = len(times) - len(times) % 6
        times = times[:complete_samples]
        names = ("rsl", "tsl")
        resampled = {
            name: np.empty((len(times) // 6, len(meta)), dtype="f") for name in names
        }
        block = 6 * 1440
        for start in range(0, len(times), block):
            stop = min(start + block, len(times))
            for name in names:
                data = source[name].isel(time=slice(start, stop)).transpose(*dimensions).values
                resampled[name][start // 6:stop // 6] = first_valid_in_minute(data)
        hourly_ids = np.sort(meta["Link"].unique())
        order = meta.reset_index().set_index(["Link", "Direction"])
        index = pd.MultiIndex.from_product((hourly_ids, ["A", "B"]))
        source_position = pd.Series(np.arange(len(meta)), index=meta.index)
        order = order.reindex(index)
        positions = source_position.loc[order["Sublink"]].values
        links = xr.Dataset(
            {name: (("time", "cml_id", "sublink_id"), arr[:, positions].reshape(-1, len(hourly_ids), 2))
             for name, arr in resampled.items()},
            coords={"time": times[::6], "cml_id": hourly_ids, "sublink_id": ["A", "B"]},
        )
        coord_names = {
            "NearLatitude_DecDeg": "site_0_lat", "NearLongitude_DecDeg": "site_0_lon",
            "FarLatitude_DecDeg": "site_1_lat", "FarLongitude_DecDeg": "site_1_lon",
            "Length_km": "length",
        }
        for original, coord in coord_names.items():
            values = order[original].values[::2] * (1000 if coord == "length" else 1)
            links = links.assign_coords({coord: ("cml_id", values)})
        return links.assign_coords(
            frequency=(("cml_id", "sublink_id"), order["Frequency_GHz"].values.reshape(-1, 2) * 1000),
            polarization=(("cml_id", "sublink_id"),
                          np.where(order["Polarization"].values.reshape(-1, 2) == "Vertical", "v", "h")),
        )


def sweden_gauges(base, *, sample=False):
    if sample:
        with xr.open_dataset(base / "openmrg_municp_gauge_8d.nc") as ds:
            rainfall = ds.rainfall_amount.load()
        group = rainfall.resample(**HOURLY)
        return group.sum().where(group.count() == 60)
    city = base / "gauges/city"
    series = pd.read_csv(city / "CityGauges-2015JJA.csv", index_col=0, parse_dates=True)
    stations = pd.read_csv(city / "CityGauges-metadata.csv", index_col=0)
    if set(stations.index) != set(series.columns):
        raise ValueError("Identificadores dos pluviômetros municipais não correspondem")
    series = series.reindex(columns=stations.index).tz_convert(None)
    time_sum = series.resample("1h", closed="right", label="right").sum(min_count=60)
    official = pd.read_csv(
        base / "gauges/smhi/GbgA-71420-2015JJA.csv", index_col=0, parse_dates=True
    )
    official = official.tz_convert(None)
    good_volume = official.Pvol_mm.where(official.Pvol_QC == "G")
    time_sum["SMHI"] = good_volume.resample("1h", closed="right", label="right").sum(min_count=4)
    lat = np.r_[stations.Latitude_DecDeg.values, 57.7156]
    lon = np.r_[stations.Longitude_DecDeg.values, 11.9924]
    return xr.DataArray(
        time_sum.values, dims=("time", "id"),
        coords={
            "time": time_sum.index.to_numpy(), "id": time_sum.columns.to_numpy(),
            "lat": ("id", lat), "lon": ("id", lon),
        },
    )


def classify_and_convert(links, path_rate, minutes):
    """Aplica controle e conversão dos notebooks dos autores na grade de um minuto."""
    links = links.sortby("cml_id")
    times = pd.date_range(pd.Timestamp(links.time.values[0]), pd.Timestamp(links.time.values[-1]), freq="min")
    loss = (links.tsl - links.rsl).transpose("cml_id", "sublink_id", "time").reindex(time=times)
    # A diferença de canal é calculada sobre séries interpoladas só para controle.
    gap_filled = loss.interpolate_na(dim="time", method="linear")
    channels = gap_filled.diff(dim="sublink_id").values[:, 0]
    bad_channel = np.stack((channels < -30, channels > 30), axis=1)
    loss = loss.where(~bad_channel).astype("f")
    values = loss.values
    slow_std = bn.move_std(values, 300, min_count=300, axis=-1)
    hourly_std = bn.move_std(values, 60, min_count=60, axis=-1)
    valid = (
        ((slow_std > 2).mean(axis=-1) <= 0.10)
        & ((hourly_std > 0.8).mean(axis=-1) <= 0.35)
        & ((hourly_std > 0.8).mean(axis=-1) >= 0.01)
    )
    del slow_std, hourly_std, gap_filled
    loss = loss.where(valid[:, :, None]).dropna("cml_id", how="all")
    if not loss.sizes["cml_id"]:
        raise ValueError("Nenhum enlace sobreviveu ao controle de qualidade")
    radar_amount = path_rate.sel(cml_id=loss.cml_id) * minutes / 60
    wet = (radar_amount.reindex(time=times) > 0.01).transpose("cml_id", "time")
    # Convenção temporal de dilatação do notebook 2_cml_processing.
    expanded = binary_dilation(
        wet.values, structure=np.ones((1, minutes + 5), dtype=bool),
        origin=(0, int((minutes + 5) / 2 - 6)),
    )
    wet = wet.copy(data=expanded).broadcast_like(loss)
    print(f"Enlaces após controle: {loss.sizes['cml_id']}/{links.sizes['cml_id']}", flush=True)
    aggregate_parts = []
    for start in range(0, loss.sizes["cml_id"], 12):
        group = loss.isel(cml_id=slice(start, start + 12))
        group_wet = wet.sel(cml_id=group.cml_id)
        base = pc.processing.baseline.baseline_constant(group, group_wet, n_average_last_dry=5)
        attenuation = (group - base).clip(min=0)
        antenna = pc.processing.wet_antenna.waa_pastorek_2021_from_A_obs(
            A_obs=attenuation,
            f_Hz=group.frequency * 1e6,
            pol=group.polarization.values,
            L_km=group.length / 1000,
            A_max=6, zeta=0.7, d=0.15,
        )
        rain = pc.processing.k_R_relation.calc_R_from_A(
            A=(attenuation - antenna).clip(min=0),
            L_km=group.length / 1000,
            f_GHz=group.frequency / 1000,
            pol=group.polarization,
        )
        grouped = rain.resample(**HOURLY)
        aggregate = grouped.mean().where(grouped.count() >= 30).mean("sublink_id")
        aggregate_parts.append(aggregate)
    return xr.concat(aggregate_parts, dim="cml_id").transpose("time", "cml_id").rename("link_rate")


def output_pairs(radar, links, gauges, minutes, output, *, already_derived=False):
    links = project_links(links)
    print(f"Radar: {radar.sizes['time']} quadros; enlaces iniciais: {links.sizes['cml_id']}", flush=True)
    geo, along_link = raster_reference(radar, links, gauges, minutes)
    if already_derived:
        interval = links.R.isel(sublink_id=0).drop_vars("sublink_id").resample(**HOURLY)
        rate = interval.mean().where(interval.count() >= 180).rename("link_rate")
    else:
        rate = classify_and_convert(links, along_link, minutes)
    pairs = xr.merge((geo.sel(cml_id=rate.cml_id), rate.reset_coords(drop=True), gauges.rename("gauge_rate")), join="inner")
    pairs = pairs.dropna("time", how="all", subset=["gauge_rate"])
    pairs = pairs.transpose("time", "cml_id", "id", missing_dims="ignore")
    pairs.to_netcdf(output, encoding={name: {"zlib": True, "complevel": 3} for name in pairs.data_vars})
    print(output, dict(pairs.sizes), flush=True)


def load_italy(path, mode):
    if mode == "italy-sample":
        return (
            xr.open_dataset(path / "openrainer_radar_8d.nc").R,
            xr.open_dataset(path / "openrainer_cml_8d.nc"),
            xr.open_dataset(path / "openrainer_gauges_8d.nc").rainfall_amount,
        )
    if mode in ("italy", "italy-2021"):
        year = 2021 if mode == "italy-2021" else 2022
        months = [f"{year}{month:02d}" for month in (6, 7, 8)]
        datasets = [load_italy(path, month) for month in months]
        radars, links, gauges = [list(group) for group in zip(*datasets, strict=True)]
        common_ids = sorted(set.intersection(*(set(item.cml_id.values) for item in links)))
        common_gauges = sorted(set.intersection(*(set(item.id.values) for item in gauges)))
        return (
            xr.concat([item.chunk({"time": 96}) for item in radars], dim="time",
                      coords="minimal", compat="equals"),
            xr.concat([item.sel(cml_id=common_ids) for item in links], dim="time",
                      data_vars="minimal", coords="minimal", compat="equals"),
            xr.concat([item.sel(id=common_gauges) for item in gauges], dim="time",
                      coords="minimal", compat="equals"),
        )
    return (
        xr.open_dataset(next(path.glob(f"RADrain_{mode}*.nc"))).rainfall_amount,
        xr.open_dataset(next(path.glob(f"CML_{mode}*.nc"))),
        xr.open_dataset(next(path.glob(f"AWS_{mode}*.nc"))).rainfall_amount,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", help="sweden, sweden-sample, italy, italy-2021, italy-sample ou mês italiano AAAAMM")
    parser.add_argument("data", type=Path)
    parser.add_argument("output", type=Path)
    arg = parser.parse_args()
    if arg.mode == "sweden":
        links = sweden_links(arg.data)
        gauges = sweden_gauges(arg.data)
        radar_ds = xr.open_dataset(arg.data / "radar/radar.nc")
        x_mesh, y_mesh = np.meshgrid(radar_ds.x.values, radar_ds.y.values)
        convert = Transformer.from_crs(STEREO, "EPSG:4326", always_xy=True)
        mesh_lon, mesh_lat = convert.transform(x_mesh, y_mesh)
        radar = ((10 ** (radar_ds.data / 10) / 200) ** (5 / 8)).assign_coords(
            lon=(("y", "x"), mesh_lon), lat=(("y", "x"), mesh_lat)
        )
        output_pairs(radar, links, gauges, 5, arg.output)
    elif arg.mode == "sweden-sample":
        output_pairs(
            xr.open_dataset(arg.data / "openmrg_rad_8d.nc").R,
            xr.open_dataset(arg.data / "openmrg_cml_8d.nc"),
            sweden_gauges(arg.data, sample=True),
            5, arg.output, already_derived=True,
        )
    else:
        radar, links, gauges = load_italy(arg.data, arg.mode)
        rename = {old: new for old, new in (("longitude", "lon"), ("latitude", "lat")) if old in gauges.coords}
        gauges = gauges.rename(rename)
        group = gauges.resample(**HOURLY)
        gauges = group.sum().where(group.count() == 4)
        output_pairs(normalize_italy_radar(radar) * 4, links, gauges, 15, arg.output)
