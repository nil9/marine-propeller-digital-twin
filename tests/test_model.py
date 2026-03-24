from digital_twin import OperatingPoint, PropellerDigitalTwin
from digital_twin.fuelcast import evaluate_fuelcast_rows, load_fuelcast_preview



def sample_history() -> list[OperatingPoint]:
    return [
        OperatingPoint("t0", 100, 15.0, 820, 170),
        OperatingPoint("t1", 100, 14.6, 845, 164),
        OperatingPoint("t2", 100, 14.1, 870, 156),
        OperatingPoint("t3", 100, 13.5, 905, 146),
    ]



def test_evaluate_flags_anomaly_and_negative_trend_with_thrust_data() -> None:
    twin = PropellerDigitalTwin(6.2, 0.95, 100, 15.0, anomaly_threshold_pct=5.0)

    reports = twin.evaluate(sample_history())

    assert len(reports) == 4
    assert reports[-1].anomaly_detected is True
    assert reports[-1].degradation_trend_pct_per_sample < 0



def test_fuelcast_preview_evaluation_produces_proxy_efficiency_and_trend() -> None:
    rows = load_fuelcast_preview("data/fuelcast_cps_poseidon_preview.csv")
    calibration_samples = 3

    reports = evaluate_fuelcast_rows(rows, calibration_samples=calibration_samples)

    assert len(reports) == len(rows) - calibration_samples
    assert reports[0].expected_shaft_power_w is not None
    assert reports[-1].actual_efficiency > 0
    assert sum(report.anomaly_detected for report in reports) >= 2
    assert min(report.efficiency_deviation_pct for report in reports) < -1.0


def test_environmental_features_increase_expected_power_under_headwind() -> None:
    history = [
        OperatingPoint("c0", 98, 13.0, 780, shaft_power_w=2_000_000),
        OperatingPoint("c1", 99, 13.5, 790, shaft_power_w=2_100_000),
        OperatingPoint("c2", 100, 14.0, 800, shaft_power_w=2_200_000),
    ]
    twin = PropellerDigitalTwin.from_power_curve(
        history,
        diameter_m=6.2,
        pitch_ratio=0.92,
        design_rpm=99.0,
        design_speed_knots=13.5,
    )

    baseline = OperatingPoint(
        "e0",
        100,
        14.0,
        800,
        shaft_power_w=2_250_000,
        vessel_heading_deg=90.0,
    )
    headwind_case = OperatingPoint(
        "e1",
        100,
        14.0,
        800,
        shaft_power_w=2_250_000,
        vessel_heading_deg=90.0,
        wind_speed_mps=14.0,
        wind_from_deg=90.0,
        current_speed_mps=1.5,
        current_to_deg=270.0,
        wave_height_m=2.5,
    )

    baseline_power = twin.expected_shaft_power(baseline)
    env_power = twin.expected_shaft_power(headwind_case)

    assert baseline_power is not None
    assert env_power is not None
    assert env_power > baseline_power

    report = twin.evaluate([headwind_case])[0]
    assert report.relative_head_wind_mps > 0
    assert report.current_aiding_mps < 0
    assert report.beaufort_scale >= 6
    assert report.wave_proxy_index > 0
