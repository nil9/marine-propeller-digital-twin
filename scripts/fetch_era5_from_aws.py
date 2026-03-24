from __future__ import annotations

import argparse
import shutil
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

AWS_ERA5_BASE = "https://era5-pds.s3.amazonaws.com"
LOCAL_SAMPLE_PATH = Path(__file__).resolve().parents[1] / "data" / "era5" / "era5_sample_subset.csv"


def download_era5_file(year: int, month: int, filename: str, output_dir: Path) -> Path:
    month_fragment = f"{month:02d}"
    source_url = f"{AWS_ERA5_BASE}/{year}/{month_fragment}/{filename}"

    output_dir.mkdir(parents=True, exist_ok=True)
    destination = output_dir / f"{year}_{month_fragment}_{filename}"

    with urlopen(source_url) as response, destination.open("wb") as handle:
        shutil.copyfileobj(response, handle)

    return destination


def copy_local_sample(output_dir: Path, year: int, month: int) -> Path:
    if not LOCAL_SAMPLE_PATH.exists():
        raise FileNotFoundError(f"Local fallback sample missing: {LOCAL_SAMPLE_PATH}")

    output_dir.mkdir(parents=True, exist_ok=True)
    destination = output_dir / f"{year}_{month:02d}_era5_sample_subset.csv"
    shutil.copyfile(LOCAL_SAMPLE_PATH, destination)
    return destination


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Download an ERA5 mirror file from AWS Open Data into data/era5. "
            "If network access is blocked, optionally copy a bundled sample dataset instead."
        )
    )
    parser.add_argument("--year", type=int, required=True, help="Year path in era5-pds (e.g. 2024)")
    parser.add_argument("--month", type=int, required=True, help="Month path in era5-pds (1-12)")
    parser.add_argument(
        "--filename",
        default="data.nc",
        help="File name within year/month path (default: data.nc)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data") / "era5",
        help="Local destination directory (default: data/era5)",
    )
    parser.add_argument(
        "--fallback-to-local-sample",
        action="store_true",
        help="Copy bundled sample ERA5 data to output dir if download fails.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        destination = download_era5_file(args.year, args.month, args.filename, args.output_dir)
    except (HTTPError, URLError) as exc:
        print(f"Download failed: {exc}")
        if not args.fallback_to_local_sample:
            return 1

        sample_destination = copy_local_sample(args.output_dir, args.year, args.month)
        print(f"Saved local fallback ERA5 sample to {sample_destination}")
        return 0

    print(f"Saved ERA5 mirror file to {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
