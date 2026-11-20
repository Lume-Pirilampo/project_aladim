"""Obtém MRMS radar-only para os eventos líquidos com resolução de minuto do OpenMesh."""
import argparse
import json
from pathlib import Path

import pandas as pd
from fetch_data.mrms import MRMSClient, NYC

PRODUCT = "RadarOnly_QPE_01H"


def windows(catalog):
    table = pd.read_csv(catalog, comment="#", parse_dates=["start", "end"])
    cases = table.loc[(table.cls == "rain") & (table.start < pd.Timestamp("2024-07-15"))]
    for row in cases.sort_values("rank").itertuples():
        start = row.start.ceil("h") - pd.Timedelta(hours=6)
        end = row.end.ceil("h") + pd.Timedelta(hours=6)
        yield row.event, start, end


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("catalog", type=Path)
    parser.add_argument("output", type=Path)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--month", help="Mês inteiro UTC no formato AAAA-MM")
    group.add_argument("--interval", nargs=3, metavar=("NOME", "INICIO", "FIM"))
    parser.add_argument("--quality", action="store_true", help="Obtém qualidade do radar por hora")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    client = MRMSClient(
        cache_dir=args.output / "cache", max_workers=6, processes=0, retries=2, timeout=28,
    )
    if args.month:
        month = pd.Period(args.month, freq="M")
        beginning = month.start_time + pd.Timedelta(hours=1)
        ending = (month + 1).start_time
        intervals = [(str(month), beginning, ending)]
    elif args.interval:
        label, start, end = args.interval
        intervals = [(label, pd.Timestamp(start), pd.Timestamp(end))]
    else:
        intervals = windows(args.catalog)
    product = "RadarQualityIndex" if args.quality else PRODUCT
    for name, start, end in intervals:
        print("Radar", name, start, end, flush=True)
        radar = client.load(product, start, end, NYC, freq="1h")
        radar.attrs["missing_times"] = json.dumps(radar.attrs.get("missing_times", []))
        radar.to_netcdf(
            args.output / f"{name}.nc",
            encoding={radar.name: {"zlib": True, "complevel": 3}},
        )
        print(name, radar.sizes["time"], "horas", radar.attrs["missing_times"], flush=True)
