from __future__ import annotations

import csv
import json
from pathlib import Path

from digital_twin.fuelcast import build_power_curve_twin, load_fuelcast_preview
from digital_twin.maintenance import MaintenancePolicyConfig, assess_maintenance_state
from scripts.export_fuelcast_metrics import export_metrics


def test_assess_maintenance_state_detects_red_condition() -> None:
    rows = load_fuelcast_preview("data/fuelcast_combo_a_joined_sample.csv")
    twin = build_power_curve_twin(rows, calibration_samples=3)
    reports = twin.evaluate([rows[-1].to_operating_point()])

    assessment = assess_maintenance_state(reports[0], twin.anomaly_threshold_pct)

    assert assessment.health_risk_index >= 35.0
    assert assessment.maintenance_state in {"AMBER", "RED"}
    assert assessment.projected_wait_cost_usd > 0.0
    assert assessment.projected_act_now_cost_usd > 0.0


def test_export_metrics_includes_maintenance_fields(tmp_path: Path) -> None:
    output_csv = tmp_path / "fuelcast_metrics.csv"
    baseline_json = tmp_path / "fuelcast_baseline.json"
    config = MaintenancePolicyConfig(sample_interval_hours=1.0, forecast_days=14)

    export_metrics(
        input_csv=Path("data/fuelcast_cps_poseidon_preview.csv"),
        output_csv=output_csv,
        baseline_json=baseline_json,
        calibration_samples=3,
        maintenance_config=config,
    )

    with output_csv.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows
    first = rows[0]
    for field in (
        "health_risk_index",
        "maintenance_state",
        "recommended_action",
        "projected_wait_cost_usd",
        "projected_act_now_cost_usd",
        "projected_cost_delta_usd",
        "drydock_recommended",
    ):
        assert field in first

    baseline = json.loads(baseline_json.read_text())
    assert "maintenance_policy" in baseline
