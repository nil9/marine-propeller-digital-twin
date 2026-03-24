from digital_twin.fuelcast import build_power_curve_twin, load_fuelcast_preview


def main() -> None:
    rows = load_fuelcast_preview("data/fuelcast_cps_poseidon_preview.csv")
    twin = build_power_curve_twin(rows, calibration_samples=3)
    reports = twin.evaluate([row.to_operating_point() for row in rows])
    baseline = twin.fleet_baseline(report.operating_point for report in reports)

    print("FuelCast preview evaluation")
    print("=" * 40)
    for report in reports:
        power_gap = 0.0
        if report.expected_shaft_power_w and report.actual_shaft_power_w:
            power_gap = report.actual_shaft_power_w - report.expected_shaft_power_w
        print(
            f"{report.operating_point.timestamp}: actual={report.actual_efficiency:.4f}, "
            f"deviation={report.efficiency_deviation_pct:+.2f}%, anomaly={'YES' if report.anomaly_detected else 'no'}, "
            f"power_gap={power_gap:+.0f} W, trend={report.degradation_trend_pct_per_sample:+.2f}%/sample, "
            f"headwind={report.relative_head_wind_mps:+.2f} m/s, current={report.current_aiding_mps:+.2f} m/s, "
            f"beaufort={report.beaufort_scale}, wave_proxy={report.wave_proxy_index:.2f}"
        )

    print("\nFleet baseline")
    for key, value in baseline.items():
        print(f"- {key}: {value:.4f}")


if __name__ == "__main__":
    main()
