"""Compara medições de enlaces curtos com os pluviômetros próximos."""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

from avaliar_validacao import gauge_to_link_distance


def diagnose(ds, region):
    distance = gauge_to_link_distance(ds)
    length = np.hypot(ds.site_1_x - ds.site_0_x, ds.site_1_y - ds.site_0_y).values
    eligible = (distance <= 1000) & (length[None, :] <= 3000)
    masked_distance = np.where(eligible, distance, np.inf)
    stations = np.flatnonzero(eligible.any(axis=1))
    links = masked_distance[stations].argmin(axis=1)
    index = xr.DataArray(links, dims="id")

    def take(name):
        return ds[name].transpose("time", "cml_id").isel(cml_id=index).values

    q = take("link_disagreement")
    link = take("link_rate")
    link_radar = take("radar_at_link")
    reference = ds.gauge_rate.transpose("time", "id").values[:, stations]
    radar = ds.radar_at_gauge.transpose("time", "id").values[:, stations]
    valid = np.isfinite(q) & np.isfinite(link) & np.isfinite(reference) & np.isfinite(radar)
    valid &= link_radar > 0
    rain_masks = [(0.5, 2.5), (2.5, 5), (5, np.inf)]
    disagreement_masks = (q <= 0.25, (q > 0.25) & (q <= 1), q > 1)
    rows = []
    for low, high in rain_masks:
        for group, mask in zip(("até 0,25", "0,25–1", "acima de 1"), disagreement_masks, strict=True):
            pairs = valid & (reference >= low) & (reference < high) & mask
            n = int(pairs.sum())
            link_error = np.abs(link[pairs] - reference[pairs])
            radar_error = np.abs(radar[pairs] - reference[pairs])
            rows.append({
                "recorte": region, "chuva_min_mm": low, "chuva_max_mm": high,
                "discordancia": group, "pares": n,
                "pluviometros_elegiveis": len(stations),
                "pluviometros_com_pares": int(pairs.any(axis=0).sum()),
                "eam_link": link_error.mean() if n else np.nan,
                "eam_radar": radar_error.mean() if n else np.nan,
                "delta_link_radar": (link_error - radar_error).mean() if n else np.nan,
            })
    return rows


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pairs", type=Path)
    parser.add_argument("region")
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    ds = xr.load_dataset(args.pairs)
    table = pd.DataFrame(diagnose(ds, args.region))
    print(table.to_string(index=False, float_format=lambda v: f"{v:.4f}"))
    table.to_csv(args.output, index=False, float_format="%.8f")
