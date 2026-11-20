"""Compara radar e correção aditiva por IDW na amostra pública OpenMRG."""
import argparse
from pathlib import Path

import numpy as np
import poligrain as plg
import xarray as xr
from mergeplg.merge import MergeDifferenceIDW
from scipy.spatial import cKDTree


def main(data_path):
    with (
        xr.open_dataset(data_path / "openmrg_rad_8d.nc") as radar_ds,
        xr.open_dataset(data_path / "openmrg_cml_8d.nc") as links,
        xr.open_dataset(data_path / "openmrg_municp_gauge_8d.nc") as gauges,
    ):
        radar = radar_ds.R.resample(time="1h").mean().load()
        # O pluviômetro registra o volume no fim do minuto.
        minute_amount = gauges.rainfall_amount.resample(
            time="1h", closed="right", label="left"
        )
        reference = minute_amount.sum().where(minute_amount.count() == 60).load()
        # Usa as intensidades em mm/h já derivadas no notebook da amostra.
        link_rate = links.R.isel(sublink_id=0).drop_vars("sublink_id")
        link_hours = link_rate.resample(time="1h")
        link_rate = link_hours.mean().where(link_hours.count() >= 180).load()

        crs = "EPSG:32632"
        grid_x, grid_y = plg.spatial.project_point_coordinates(radar.lon, radar.lat, crs)
        radar = radar.assign_coords(x_grid=grid_x, y_grid=grid_y)
        gauge_x, gauge_y = plg.spatial.project_point_coordinates(gauges.lon, gauges.lat, crs)
        start_x, start_y = plg.spatial.project_point_coordinates(
            links.site_0_lon, links.site_0_lat, crs
        )
        end_x, end_y = plg.spatial.project_point_coordinates(
            links.site_1_lon, links.site_1_lat, crs
        )
        link_rate = link_rate.assign_coords(
            site_0_x=start_x, site_0_y=start_y, site_1_x=end_x, site_1_y=end_y,
            x=(start_x + end_x) / 2, y=(start_y + end_y) / 2,
        )

        grid_points = np.column_stack((grid_x.values.ravel(), grid_y.values.ravel()))
        gauge_points = np.column_stack((gauge_x.values, gauge_y.values))
        distances, indices = cKDTree(grid_points).query(gauge_points)
        row, col = np.unravel_index(indices, grid_x.shape)
        rows = xr.DataArray(row, dims="id", coords={"id": gauges.id})
        cols = xr.DataArray(col, dims="id", coords={"id": gauges.id})

    radar, link_rate, reference = xr.align(radar, link_rate, reference, join="inner")
    radar_at_gauges = radar.isel(y=rows, x=cols).transpose("time", "id")
    predictions = {"radar": radar_at_gauges.values}
    for label, limit in (("IDW 5 mm/h", 5), ("IDW 10 mm/h", 10)):
        merger = MergeDifferenceIDW(
            ds_rad=radar, ds_cmls=link_rate, nnear=70,
            method="additive", range_checks={"diff_check": limit},
        )
        series = []
        for hour in range(radar.sizes["time"]):
            adjusted = merger(
                da_rad=radar.isel(time=hour), da_cmls=link_rate.isel(time=hour)
            ).rainfall
            series.append(adjusted.isel(y=rows, x=cols).values)
        predictions[label] = np.stack(series)

    observed = reference.transpose("time", "id").values
    valid = np.isfinite(observed) & np.isfinite(list(predictions.values())).all(axis=0)
    rainy = valid & (observed > 0)
    intense = valid & (observed >= 5)
    print(f"Horas: {radar.sizes['time']}; enlaces: {link_rate.sizes['cml_id']}")
    print(f"Distância máxima pluviômetro–centro da célula: {distances.max():.0f} m")
    print(f"Pares hora–pluviômetro: {valid.sum()}; com chuva: {rainy.sum()}")
    dates = np.unique(radar.time.values[intense.any(axis=1)].astype("datetime64[D]"))
    print(f"Pares com ≥5 mm: {intense.sum()}; dias: {', '.join(map(str, dates))}")
    print("Método | EAM total | EAM com chuva | EAM ≥5 mm | Diferença vs. radar")
    for label, predicted in predictions.items():
        error = np.abs(predicted - observed)
        changed = np.count_nonzero(valid & ~np.isclose(predicted, predictions["radar"]))
        print(
            f"{label} | {error[valid].mean():.3f} | {error[rainy].mean():.3f}"
            f" | {error[intense].mean():.3f} | {changed}"
        )
    strict = predictions["IDW 5 mm/h"]
    standard = predictions["IDW 10 mm/h"]
    differing = valid & ~np.isclose(strict, standard)
    print(f"5 vs. 10 mm/h: {differing.sum()} pares, sendo {(differing & intense).sum()} ≥5 mm")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("data_path", type=Path, help="Diretório dos três arquivos NetCDF")
    main(parser.parse_args().data_path)
