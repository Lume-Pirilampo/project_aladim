"""Isola a mediana espacial na correção multiplicativa inspirada em Nielsen et al."""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.spatial.distance import cdist
import xarray as xr

from avaliar_validacao import coordinates, evaluate, gauge_coverage, predict


def window_totals(values, times, hours, rolling):
    table = pd.DataFrame(values, index=times)
    period = f"{hours}h"
    if rolling:
        return table.rolling(period, closed="right", min_periods=1).sum().values
    labels = times.ceil(period)
    return table.groupby(labels).transform("sum").values


def ratios(ds, hours, rolling):
    radio = ds.link_rate.transpose("time", "cml_id").values
    radar = ds.radar_at_link.transpose("time", "cml_id").values
    wet = np.isfinite(radio) & np.isfinite(radar) & (radio > 0) & (radar > 0)
    times = ds.get_index("time")
    radio_total = window_totals(np.where(wet, radio, 0), times, hours, rolling)
    radar_total = window_totals(np.where(wet, radar, 0), times, hours, rolling)
    quotient = np.divide(
        radio_total, radar_total, out=np.full_like(radar_total, np.nan), where=radar_total > 0,
    )
    return np.minimum(quotient, 10)


def spatial_factors(quotient, distances, *, minimum=10, radius=10_000):
    nearest = np.argsort(distances, axis=1, kind="stable")
    ordered = np.take_along_axis(distances, nearest, axis=1)
    median = np.ones((len(quotient), len(nearest)))
    weighted = np.ones_like(median)
    support = np.zeros_like(median, dtype=bool)
    for hour in np.flatnonzero(np.isfinite(quotient).sum(axis=1) >= minimum):
        for target, order in enumerate(nearest):
            sources = quotient[hour, order]
            valid = np.isfinite(sources)
            observed = sources[valid]
            meters = ordered[target, valid]
            use = meters <= max(radius, meters[minimum - 1])
            nearby, distance = observed[use], meters[use]
            median[hour, target] = np.median(nearby)
            exact = distance == 0
            if exact.any():
                weighted[hour, target] = nearby[exact].mean()
            else:
                weighted[hour, target] = np.average(nearby, weights=1 / distance ** 2)
            support[hour, target] = True
    return median, weighted, support


def daily_stats(times, reference, field, complete):
    labels = times.ceil("24h")
    if not len(labels):
        return 0, np.nan, np.nan
    valid = pd.DataFrame(complete).groupby(labels).sum().values == 24
    sums = [
        pd.DataFrame(np.where(complete, values, 0)).groupby(labels).sum().values[valid]
        for values in (reference, field)
    ]
    observed, predicted = sums
    if not len(observed):
        return 0, np.nan, np.nan
    squared = (observed - predicted) ** 2
    spread = np.sum((observed - observed.mean()) ** 2)
    efficiency = 1 - squared.sum() / spread if spread > 0 else np.nan
    return len(observed), np.sqrt(squared.mean()), efficiency


def run(ds, name, hours):
    times = ds.get_index("time")
    if not times.is_unique or not times.is_monotonic_increasing:
        raise ValueError("Horários devem ser únicos e ordenados")
    targets = coordinates(ds, "target_x", "target_y")
    links = coordinates(ds, "link_x", "link_y")
    distance = cdist(targets, links)
    base = predict(ds)
    evaluated = times > pd.Timestamp("2015-08-01T00:00") if name == "SE agosto" else np.ones(len(times), dtype=bool)
    gauge = ds.gauge_rate.transpose("time", "id").values
    severe = evaluated[:, None] & (gauge >= 5) & np.isfinite(base["radar"])
    severe &= gauge_coverage(ds)[None, :] <= 20_000
    result = []
    for rolling in (False, True):
        label = f"{hours} h até o fim da hora" if rolling else f"bloco retrospectivo de {hours} h"
        median, weighted, support = spatial_factors(ratios(ds, hours, rolling), distance)
        raw = base["radar"]
        estimates = {
            "radar": raw, "aditivo fixo 10": base["fixo_10"],
            "aditivo por intensidade": base["intensidade"],
            "multiplicativo IDW": raw * weighted, "multiplicativo mediana": raw * median,
        }
        rows = evaluate(ds, estimates, "multiplicativo IDW", evaluated, name, 20_000)
        common = np.isfinite(gauge) & (gauge_coverage(ds)[None, :] <= 20_000)
        for values in estimates.values():
            common &= np.isfinite(values)
        for row in rows:
            days, daily_rmse, daily_nse = daily_stats(
                times[evaluated], gauge[evaluated], estimates[row["metodo"]][evaluated],
                common[evaluated],
            )
            row.update(
                janela_do_fator=label, fortes_com_suporte=int((support & severe).sum()),
                pares_diarios=days, reemq_diaria=daily_rmse, nse_diario=daily_nse,
            )
        result.extend(rows)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pairs", type=Path)
    parser.add_argument("name")
    parser.add_argument("output", type=Path)
    parser.add_argument("--period", type=int, choices=(6, 24), default=6)
    args = parser.parse_args()
    report = pd.DataFrame(run(xr.load_dataset(args.pairs), args.name, args.period))
    report.to_csv(args.output, index=False, float_format="%.8f")
    print(report[["janela_do_fator", "metodo", "pares_5", "fortes_com_suporte", "eam_5",
                  "detectados_5", "falsos_alarmes_5", "delta_ic025", "delta_ic975"]].to_string(index=False))
