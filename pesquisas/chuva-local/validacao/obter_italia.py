"""Extrai meses selecionados dos TAR públicos OpenRainER, via HTTP Range."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import gzip
from pathlib import Path
import shutil
import tarfile
import time
from urllib.request import Request, urlopen

BASE = "https://zenodo.org/records/14731404/files"
ARCHIVES = ("CML", "AWS", "RADrain")
CHUNK = 4 * 1024 * 1024


def read_range(url, start, size):
    end = start + size - 1
    expected = f"bytes {start}-{end}/"
    for attempt in range(3):
        try:
            request = Request(url, headers={"Range": f"bytes={start}-{end}"})
            with urlopen(request, timeout=30) as response:
                if response.status != 206 or not response.headers.get(
                    "Content-Range", ""
                ).startswith(expected):
                    raise ValueError("Resposta incompatível com o intervalo pedido")
                data = response.read(size + 1)
            if len(data) != size:
                raise ValueError(f"Intervalo incompleto ({len(data)}/{size})")
            return data
        except (OSError, ValueError) as error:
            if attempt == 2:
                raise
            print(f"Nova tentativa de intervalo {start}-{end}: {error}", flush=True)
            time.sleep(1 + attempt)


def archive_members(url):
    position = 0
    while True:
        block = read_range(url, position, tarfile.BLOCKSIZE)
        if block == bytes(tarfile.BLOCKSIZE):
            return
        member = tarfile.TarInfo.frombuf(block, encoding="utf-8", errors="strict")
        offset = position + tarfile.BLOCKSIZE
        yield member, offset
        padded_size = (member.size + tarfile.BLOCKSIZE - 1) // tarfile.BLOCKSIZE
        position = offset + padded_size * tarfile.BLOCKSIZE


def download_months(archive, months, output):
    url = f"{BASE}/{archive}.tar?download=1"
    pending = set(months)
    for member, offset in archive_members(url):
        name = Path(member.name).name
        month = next((m for m in pending if name.startswith(f"{archive}_{m}")), None)
        if not member.isfile() or not name.endswith(".nc.gz") or month is None:
            continue
        print(f"{archive} {month}: {name}, {member.size:,} bytes", flush=True)
        compressed = output / name
        partial = output / f"{name}.part"
        uncompressed = output / name.removesuffix(".gz")
        if not uncompressed.exists():
            if not compressed.exists():
                with partial.open("wb") as file:
                    for start in range(0, member.size, CHUNK):
                        size = min(CHUNK, member.size - start)
                        file.write(read_range(url, offset + start, size))
                partial.replace(compressed)
            temp_netcdf = output / f"{uncompressed.name}.tmp"
            with gzip.open(compressed, "rb") as source, temp_netcdf.open("wb") as target:
                shutil.copyfileobj(source, target)
            temp_netcdf.replace(uncompressed)
        pending.remove(month)
        if not pending:
            return
    raise FileNotFoundError(f"{archive}: meses ausentes: {sorted(pending)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("months", nargs="+")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(max_workers=len(ARCHIVES)) as pool:
        downloads = [
            pool.submit(download_months, archive, args.months, args.output)
            for archive in ARCHIVES
        ]
        for task in downloads:
            task.result()
