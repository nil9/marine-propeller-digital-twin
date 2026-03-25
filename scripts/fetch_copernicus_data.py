from __future__ import annotations

import argparse
import csv
import shutil
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

DEFAULT_OUTPUT_DIR = Path("data") / "Copernicus"


def download_copernicus_file(source_url: str, destination_path: Path) -> Path:
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    with urlopen(source_url) as response, destination_path.open("wb") as handle:
        shutil.copyfileobj(response, handle)
    return destination_path


def write_fallback_sample(destination_path: Path) -> Path:
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    with destination_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "time",
                "latitude",
                "longitude",
                "sea_surface_temperature_c",
                "significant_wave_height_m",
                "wind_speed_10m_ms",
            ]
        )
        writer.writerows(
            [
                ["2024-01-01T00:00:00Z", 36.00, -5.60, 16.4, 1.2, 7.8],
                ["2024-01-01T06:00:00Z", 36.00, -5.60, 16.1, 1.5, 9.2],
                ["2024-01-01T12:00:00Z", 36.00, -5.60, 16.0, 1.1, 6.4],
                ["2024-01-01T18:00:00Z", 36.00, -5.60, 15.8, 0.9, 5.7],
            ]
        )
    return destination_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Download Copernicus data into data/Copernicus. "
            "If download fails (for example due to a corporate proxy), "
            "optionally create a local fallback sample CSV."
        )
    )
    parser.add_argument(
        "--source-url",
        required=True,
        help="Public Copernicus data URL to download.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Destination directory (default: data/Copernicus)",
    )
    parser.add_argument(
        "--filename",
        default="copernicus_download.bin",
        help="Output file name for successful download (default: copernicus_download.bin)",
    )
    parser.add_argument(
        "--fallback-to-sample",
        action="store_true",
        help="Create copernicus_sample_subset.csv if download fails.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_path = args.output_dir / args.filename

    try:
        saved_path = download_copernicus_file(args.source_url, output_path)
        print(f"Saved Copernicus file to {saved_path}")
        return 0
    except (HTTPError, URLError, TimeoutError) as exc:
        print(f"Download failed: {exc}")
        if not args.fallback_to_sample:
            return 1

        sample_path = write_fallback_sample(args.output_dir / "copernicus_sample_subset.csv")
        print(f"Saved fallback Copernicus sample to {sample_path}")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
