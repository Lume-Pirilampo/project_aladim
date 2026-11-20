"""Compara a classificação de minutos chuvosos do rádio e do radar no mesmo recorte."""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

from avaliar_validacao import evaluate, predict


def after_spinup(values):
    stamps = pd.DatetimeIndex(values)
    starts = np.zeros(len(stamps), dtype=bool)
    starts[0] = True
    starts[1:] = (
        (np.diff(stamps.to_numpy()) > np.timedelta64(1, "h"))
        | (np.diff((stamps - pd.Timedelta(seconds=1)).month) != 0)
    )
    first = pd.Series(np.where(starts, stamps.to_numpy(), np.datetime64("NaT"))).ffill()
    return (stamps.to_numpy() - first.to_numpy()) >= np.timedelta64(24, "h")


def compare(signal, path, label):
    xr.align(signal, path, join="exact")
    for name in ("radar_at_gauge", "radar_at_link", "gauge_rate", "measured_share"):
        xr.testing.assert_equal(signal[name], path[name])
    forecasts_signal, forecasts_path = predict(signal), predict(path)
    forecasts = {
        "radar": forecasts_signal["radar"],
        "sinal_sem_filtro": forecasts_signal["sem_filtro"],
        "sinal_fixo_10": forecasts_signal["fixo_10"],
        "radar_no_enlace_sem_filtro": forecasts_path["sem_filtro"],
        "radar_no_enlace_fixo_10": forecasts_path["fixo_10"],
    }
    if "window_start" in signal.coords:
        xr.testing.assert_equal(signal.window_start, path.window_start)
        keep = (signal.time.values - signal.window_start.values) >= np.timedelta64(24, "h")
    else:
        keep = after_spinup(signal.time.values)
    stats = pd.DataFrame(evaluate(signal, forecasts, "sinal_sem_filtro", keep, label, 20_000))
    return stats


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("signal", type=Path)
    parser.add_argument("radar_wet", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("recorte")
    args = parser.parse_args()
    result = compare(xr.load_dataset(args.signal), xr.load_dataset(args.radar_wet), args.recorte)
    print(result[["recorte","metodo","pares","pares_5","eventos_5","eam_5","eam_10",
                  "detectados_5","falsos_alarmes_5","delta_ic025","delta_ic975"]].to_string(index=False))
    result.to_csv(args.output,index=False,float_format="%.8f")
