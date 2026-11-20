"""Compara a avaliação restrita aos pluviômetros com mapas completos do mergeplg."""
import numpy as np
import xarray as xr
from mergeplg.merge import MergeDifferenceIDW
from scipy.spatial import cKDTree
from avaliar_validacao import predict, coordinates
from preparar_validacao import HOURLY, projected, project_links

with xr.open_dataset("data/openmrg_rad_8d.nc") as source, xr.open_dataset("data/openmrg_cml_8d.nc") as ds:
    radar_groups = source.R.resample(**HOURLY)
    hourly = radar_groups.mean().where(radar_groups.count() == 12).load()
    hourly = hourly.astype("f")
    gx, gy = projected(hourly, "lon", "lat")
    hourly = hourly.assign_coords(x_grid=gx, y_grid=gy)
    links = project_links(ds)
    prepared = xr.load_dataset("suecia_amostra_pares.nc")
    rates = prepared.link_rate.assign_coords(
        x=links.link_x, y=links.link_y,
        site_0_x=links.site_0_x, site_0_y=links.site_0_y,
        site_1_x=links.site_1_x, site_1_y=links.site_1_y,
    )
    tree = cKDTree(np.column_stack((gy.values.ravel(), gx.values.ravel())))
    _, indices = tree.query(coordinates(prepared, "target_x", "target_y"))
    rows, cols = np.unravel_index(indices, gx.shape)
    rows = xr.DataArray(rows, dims="id", coords={"id": prepared.id})
    cols = xr.DataArray(cols, dims="id", coords={"id": prepared.id})
    predictions = predict(prepared)
    peaks = np.where((prepared.gauge_rate.values >= 5).any(axis=1))[0]
    for key, limit in (("sem_filtro", None), ("fixo_5", 5), ("fixo_10", 10)):
        check = {} if limit is None else {"diff_check": limit}
        merge = MergeDifferenceIDW(ds_rad=hourly, ds_cmls=rates, nnear=70, range_checks=check)
        errors = []
        for i in peaks:
            time = rates.time.values[i]
            # Impede o comparador nativo de usar trajetos com células ausentes.
            inputs = rates.sel(time=time).where(prepared.radar_at_link.sel(time=time).notnull())
            grid = merge(da_rad=hourly.sel(time=time), da_cmls=inputs).rainfall
            expected = grid.isel(y=rows, x=cols).values
            comparison = prepared.radar_at_gauge.values[i]
            finite = np.isfinite(comparison)
            errors.extend(np.abs(expected[finite] - predictions[key][i, finite]))
        print(key, len(peaks), len(errors), max(errors), flush=True)
        assert max(errors) < 1e-5
