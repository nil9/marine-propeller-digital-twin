from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


FLOAT_FIELDS = {
    "actual_efficiency",
    "efficiency_deviation_pct",
    "anomaly_score",
    "anomaly_threshold_pct",
    "degradation_trend_pct_per_sample",
    "expected_shaft_power_w",
    "actual_shaft_power_w",
    "power_gap_w",
    "relative_head_wind_mps",
    "current_aiding_mps",
    "wave_proxy_index",
}
INT_FIELDS = {"beaufort_scale"}
BOOL_FIELDS = {"anomaly_detected"}


def _coerce_value(field: str, value: str):
    if value == "":
        return None
    if field in BOOL_FIELDS:
        return value == "1" or value.lower() == "true"
    if field in INT_FIELDS:
        return int(value)
    if field in FLOAT_FIELDS:
        return float(value)
    return value


def convert_metrics_csv_to_json(metrics_csv: Path, baseline_json: Path, output_json: Path) -> None:
    with metrics_csv.open(newline="") as handle:
        reader = csv.DictReader(handle)
        metrics = []
        for row in reader:
            metrics.append({field: _coerce_value(field, value) for field, value in row.items()})

    baseline = json.loads(baseline_json.read_text())
    payload = {
        "metrics": metrics,
        "baseline": baseline,
    }

    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(payload, indent=2))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert FuelCast CSV + baseline JSON into a JSON payload suitable for Grafana JSON API."
    )
    parser.add_argument(
        "--metrics-csv",
        default="data/grafana/fuelcast_metrics.csv",
        type=Path,
        help="Path to FuelCast metrics CSV",
    )
    parser.add_argument(
        "--baseline-json",
        default="data/grafana/fuelcast_baseline.json",
        type=Path,
        help="Path to FuelCast baseline JSON",
    )
    parser.add_argument(
        "--output-json",
        default="data/grafana/fuelcast_metrics_api.json",
        type=Path,
        help="Path to output merged JSON for Grafana JSON API datasource",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    convert_metrics_csv_to_json(args.metrics_csv, args.baseline_json, args.output_json)
