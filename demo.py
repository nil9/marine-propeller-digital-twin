from digital_twin import OperatingPoint, PropellerDigitalTwin


def build_demo_history() -> list[OperatingPoint]:
    return [
        OperatingPoint("2026-03-20T00:00:00Z", shaft_rpm=98, vessel_speed_knots=14.8, torque_kNm=820, thrust_kN=168),
        OperatingPoint("2026-03-20T00:05:00Z", shaft_rpm=98, vessel_speed_knots=14.5, torque_kNm=835, thrust_kN=164),
        OperatingPoint("2026-03-20T00:10:00Z", shaft_rpm=98, vessel_speed_knots=14.0, torque_kNm=860, thrust_kN=157),
        OperatingPoint("2026-03-20T00:15:00Z", shaft_rpm=98, vessel_speed_knots=13.6, torque_kNm=885, thrust_kN=149),
        OperatingPoint("2026-03-20T00:20:00Z", shaft_rpm=98, vessel_speed_knots=13.1, torque_kNm=910, thrust_kN=141),
    ]


def main() -> None:
    twin = PropellerDigitalTwin(
        diameter_m=6.2,
        pitch_ratio=0.92,
        design_rpm=100,
        design_speed_knots=15.0,
        design_slip=0.11,
        anomaly_threshold_pct=7.5,
    )
    reports = twin.evaluate(build_demo_history())
    baseline = twin.fleet_baseline(report.operating_point for report in reports)

    print("Marine Propeller Digital Twin Demo")
    print("=" * 40)
    for report in reports:
        print(
            f"{report.operating_point.timestamp}: "
            f"expected={report.expected_efficiency:.3f}, "
            f"actual={report.actual_efficiency:.3f}, "
            f"deviation={report.efficiency_deviation_pct:+.2f}%, "
            f"anomaly={'YES' if report.anomaly_detected else 'no'}, "
            f"trend={report.degradation_trend_pct_per_sample:+.2f}%/sample"
        )

    print("\nFleet baseline")
    for key, value in baseline.items():
        print(f"- {key}: {value:.3f}")


if __name__ == "__main__":
    main()
