from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from digital_twin.fuelcast import build_power_curve_twin, load_fuelcast_preview


def export_metrics(input_csv: Path, output_csv: Path, baseline_json: Path, calibration_samples: int) -> None:
    rows = load_fuelcast_preview(input_csv)
    twin = build_power_curve_twin(rows, calibration_samples=calibration_samples)
    operating_points = [row.to_operating_point() for row in rows]
    evaluation_points = operating_points[calibration_samples:]
    reports = twin.evaluate(evaluation_points)
    baseline = twin.fleet_baseline(report.operating_point for report in reports)

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "timestamp",
                "actual_efficiency",
                "efficiency_deviation_pct",
                "anomaly_detected",
                "anomaly_score",
                "anomaly_threshold_pct",
                "degradation_trend_pct_per_sample",
                "expected_shaft_power_w",
                "actual_shaft_power_w",
                "power_gap_w",
                "relative_head_wind_mps",
                "current_aiding_mps",
                "beaufort_scale",
                "wave_proxy_index",
            ],
        )
        writer.writeheader()
        for report in reports:
            expected_power = report.expected_shaft_power_w
            actual_power = report.actual_shaft_power_w
            power_gap = None
            if expected_power is not None and actual_power is not None:
                power_gap = actual_power - expected_power
            writer.writerow(
                {
                    "timestamp": report.operating_point.timestamp,
                    "actual_efficiency": f"{report.actual_efficiency:.6f}",
                    "efficiency_deviation_pct": f"{report.efficiency_deviation_pct:.6f}",
                    "anomaly_detected": int(report.anomaly_detected),
                    "anomaly_score": f"{report.anomaly_score:.6f}",
                    "anomaly_threshold_pct": f"{twin.anomaly_threshold_pct:.6f}",
                    "degradation_trend_pct_per_sample": f"{report.degradation_trend_pct_per_sample:.6f}",
                    "expected_shaft_power_w": "" if expected_power is None else f"{expected_power:.6f}",
                    "actual_shaft_power_w": "" if actual_power is None else f"{actual_power:.6f}",
                    "power_gap_w": "" if power_gap is None else f"{power_gap:.6f}",
                    "relative_head_wind_mps": f"{report.relative_head_wind_mps:.6f}",
                    "current_aiding_mps": f"{report.current_aiding_mps:.6f}",
                    "beaufort_scale": report.beaufort_scale,
                    "wave_proxy_index": f"{report.wave_proxy_index:.6f}",
                }
            )

    baseline_json.parent.mkdir(parents=True, exist_ok=True)
    anomaly_count = sum(1 for report in reports if report.anomaly_detected)
    payload = {
        "mean_actual_efficiency": baseline["mean_actual_efficiency"],
        "mean_efficiency_gap_pct": baseline["mean_efficiency_gap_pct"],
        "anomaly_count": anomaly_count,
        "anomaly_threshold_pct": twin.anomaly_threshold_pct,
        "rows_evaluated": len(reports),
        "calibration_samples": calibration_samples,
    }
    baseline_json.write_text(json.dumps(payload, indent=2))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export FuelCast evaluation metrics for Grafana dashboards")
    parser.add_argument(
        "--input",
        default="data/fuelcast_cps_poseidon_preview.csv",
        type=Path,
        help="Path to FuelCast preview CSV",
    )
    parser.add_argument(
        "--output",
        default="data/grafana/fuelcast_metrics.csv",
        type=Path,
        help="Path to output time-series CSV",
    )
    parser.add_argument(
        "--baseline-output",
        default="data/grafana/fuelcast_baseline.json",
        type=Path,
        help="Path to output KPI baseline JSON",
    )
    parser.add_argument(
        "--calibration-samples",
        default=3,
        type=int,
        help="Number of initial samples used for calibration (excluded from dashboard output)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    export_metrics(args.input, args.output, args.baseline_output, args.calibration_samples)
