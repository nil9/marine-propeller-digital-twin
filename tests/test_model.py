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
