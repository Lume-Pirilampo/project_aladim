"""Compara disponibilidade bruta em horas secas e fortes no mesmo enlace e dia."""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr


def matching_days(ds):
    recorded = ds.measured_share.transpose("time", "cml_id").values
    path = ds.radar_at_link.transpose("time", "cml_id").values
    valid = np.isfinite(path) & np.isfinite(recorded)
    dry = valid & (path <= 0.01)
    heavy = valid & (path >= 5)
    active = ((recorded >= 0.5) & dry).sum(axis=0) >= 10
    days = (pd.DatetimeIndex(ds.time.values) - pd.Timedelta(seconds=1)).normalize()
    rows = []
    for day in days.unique():
        index = (days == day)
        for c in np.flatnonzero(active):
            observed_dry = dry[index, c]
            observed_heavy = heavy[index, c]
            if observed_dry.sum() < 4 or not observed_heavy.any():
                continue
            level = recorded[index, c]
            rows.append({
                "dia_utc": day.date().isoformat(),
                "enlace": str(ds.cml_id.values[c]),
                "horas_secas": int(observed_dry.sum()),
                "horas_fortes": int(observed_heavy.sum()),
                "disponibilidade_seca": level[observed_dry].mean(),
                "disponibilidade_forte": level[observed_heavy].mean(),
            })
    table = pd.DataFrame(rows)
    if table.empty:
        raise ValueError("Sem dias comparáveis pela regra de cobertura")
    table["dif_forte_menos_seca"] = table.disponibilidade_forte - table.disponibilidade_seca
    return table


def grouped_interval(paired):
    # Cada dia recebe o mesmo peso, com todos os enlaces daquele dia no bloco.
    daily = paired.groupby("dia_utc").dif_forte_menos_seca.mean().values
    if len(daily) < 10:
        return np.nan, np.nan
    rng = np.random.default_rng(20261120)
    indices = rng.integers(len(daily), size=(4000, len(daily)))
    return np.quantile(daily[indices].mean(axis=1), [.025, .975])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pairs", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    with xr.open_dataset(args.pairs) as ds:
        pairs = matching_days(ds)
    daily = pairs.groupby("dia_utc").dif_forte_menos_seca.mean()
    print("Dias:", len(daily), "enlaces:", pairs.enlace.nunique(), "pares dia–enlace:", len(pairs))
    print("Média por dia:", daily.mean(), "mediana:", daily.median(),
          "intervalo:", grouped_interval(pairs))
    print("Horários secos:", pairs.horas_secas.sum(), "fortes:", pairs.horas_fortes.sum())
    pairs.to_csv(args.output, index=False, float_format="%.8f")
