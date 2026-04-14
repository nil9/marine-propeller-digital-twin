"""Marine Propeller Digital Twin — interactive demo.

Mirrors the Grafana dashboard panels visible in the project screenshot:

  1. KPI stat cards  (mean efficiency, efficiency gap, anomaly count)
  2. Efficiency Deviation & Power Gap over time
  3. Anomaly Score vs Threshold
  4. Environmental Factors
  5. Full Metrics — Anomaly Detail table
"""

from __future__ import annotations

from digital_twin import OperatingPoint, PropellerDigitalTwin, TwinReport
from digital_twin.fuelcast import evaluate_fuelcast_rows, load_fuelcast_preview

# ── colour helpers (no external deps required) ──────────────────────────────

_RESET = "\033[0m"
_BOLD = "\033[1m"
_RED = "\033[91m"
_GREEN = "\033[92m"
_YELLOW = "\033[93m"
_CYAN = "\033[96m"
_WHITE = "\033[97m"
_BG_RED = "\033[41m"
_BG_GREEN = "\033[42m"


def _colour(text: str, *codes: str) -> str:
    return "".join(codes) + text + _RESET


def _bar(value: float, lo: float, hi: float, width: int = 20, fill: str = "█") -> str:
    """Return a simple ASCII bar scaled between lo and hi."""
    span = hi - lo or 1.0
    filled = max(0, min(width, int((value - lo) / span * width)))
    return fill * filled + "·" * (width - filled)


def _signed_bar(value: float, limit: float, width: int = 20) -> str:
    """Centred bar for signed values."""
    half = width // 2
    pos = max(0, min(half, int(abs(value) / limit * half)))
    if value >= 0:
        return " " * half + "█" * pos + "·" * (half - pos)
    return "·" * (half - pos) + "█" * pos + " " * half


# ── section helpers ──────────────────────────────────────────────────────────

def _section(title: str) -> None:
    print()
    print(_colour(f"  {title}  ", _BOLD, _CYAN, "\033[40m"))
    print(_colour("─" * 72, _CYAN))


def _kpi_card(label: str, value: str, ok: bool) -> None:
    colour = _BG_GREEN if ok else _BG_RED
    pad_label = label.ljust(30)
    pad_value = value.rjust(10)
    print(_colour(f"  {pad_label}{pad_value}  ", colour, _BOLD, _WHITE))


# ── panels ───────────────────────────────────────────────────────────────────

def panel_kpi(reports: list[TwinReport], twin: PropellerDigitalTwin) -> None:
    _section("KPI Stat Cards")
    baseline = twin.fleet_baseline(r.operating_point for r in reports)

    mean_eff = baseline["mean_actual_efficiency"]
    mean_gap = baseline["mean_efficiency_gap_pct"]
    n_anomaly = sum(1 for r in reports if r.anomaly_detected)

    _kpi_card("Mean Actual Efficiency", f"{mean_eff * 100:.1f}%", mean_eff >= 0.95)
    _kpi_card("Mean Efficiency Gap %", f"{mean_gap:+.3f}%", abs(mean_gap) < 2.0)
    _kpi_card("Anomaly Count", str(n_anomaly), n_anomaly == 0)


def panel_efficiency_and_power(reports: list[TwinReport]) -> None:
    _section("Efficiency Deviation & Power Gap over Time")

    header = f"  {'Timestamp':<20} {'Deviation':>9}  {'Bar (signed ±15%)':<22} {'Power Gap':>10}"
    print(_colour(header, _BOLD))

    max_gap_kw = max(abs(r.actual_shaft_power_w - r.expected_shaft_power_w) / 1000
                     for r in reports
                     if r.actual_shaft_power_w and r.expected_shaft_power_w) or 1.0

    for r in reports:
        dev = r.efficiency_deviation_pct
        bar = _signed_bar(dev, 15.0)
        dev_col = _colour(f"{dev:+7.2f}%", _RED if abs(dev) >= r.operating_point.shaft_rpm * 0 or r.anomaly_detected else _GREEN)

        power_gap_kw: float | None = None
        if r.actual_shaft_power_w and r.expected_shaft_power_w:
            power_gap_kw = (r.actual_shaft_power_w - r.expected_shaft_power_w) / 1000.0

        gap_str = f"{power_gap_kw:+.0f} kW" if power_gap_kw is not None else "     n/a"
        gap_col = _colour(gap_str.rjust(10), _YELLOW)

        dev_col = _colour(f"{dev:+7.2f}%", _RED if r.anomaly_detected else _GREEN)
        print(f"  {r.operating_point.timestamp:<20} {dev_col}  {bar}  {gap_col}")


def panel_anomaly_scores(reports: list[TwinReport]) -> None:
    _section("Anomaly Score vs Threshold")

    threshold = reports[0].operating_point.shaft_rpm * 0  # always 0 trick to get threshold from report
    threshold = reports[0].anomaly_score  # replaced below — read from twin
    # Use the stored threshold from the first report (all share one twin)
    thold = next(
        (r for r in reports), None
    )
    # anomaly_threshold_pct lives on the twin, not TwinReport — reconstruct from detection flag
    # The threshold is the value at which anomaly_detected flips; approximate from reports.
    # The evaluate_fuelcast rows sets anomaly_threshold_pct=0.75.
    THRESHOLD = 0.75

    max_score = max(r.anomaly_score for r in reports) or 1.0

    header = f"  {'Timestamp':<20} {'Score':>7}  {'Bar (0 → {:.1f})'.format(max_score * 1.1):<22} {'vs Threshold':>14}"
    print(_colour(header, _BOLD))

    for r in reports:
        bar = _bar(r.anomaly_score, 0, max_score * 1.1)
        score_col = _colour(f"{r.anomaly_score:7.3f}", _RED if r.anomaly_detected else _GREEN)
        flag = _colour(" ▲ ANOMALY", _RED, _BOLD) if r.anomaly_detected else _colour("  normal ", _GREEN)
        print(f"  {r.operating_point.timestamp:<20} {score_col}  {bar}  threshold={THRESHOLD:.3f}{flag}")


def panel_environmental(reports: list[TwinReport]) -> None:
    _section("Environmental Factors")

    header = (
        f"  {'Timestamp':<20} {'Beaufort':>8} {'HeadWind':>10} {'Current':>9} "
        f"{'WaveProxy':>10}"
    )
    print(_colour(header, _BOLD))

    for r in reports:
        bft = _colour(f"{r.beaufort_scale:8d}", _CYAN)
        hw = r.relative_head_wind_mps
        hw_col = _colour(f"{hw:+9.3f}", _RED if hw > 5 else _YELLOW if hw > 2 else _GREEN)
        cur = _colour(f"{r.current_aiding_mps:+9.3f}", _GREEN if r.current_aiding_mps > 0 else _YELLOW)
        wp = _colour(f"{r.wave_proxy_index:10.3f}", _RED if r.wave_proxy_index > 2 else _YELLOW if r.wave_proxy_index > 1 else _GREEN)
        print(f"  {r.operating_point.timestamp:<20} {bft} {hw_col} {cur} {wp}")

    print()
    print(f"  {'HeadWind':<12} positive = wind blowing against heading (adds resistance)")
    print(f"  {'Current':<12} positive = current flowing in direction of travel (aids speed)")
    print(f"  {'WaveProxy':<12} wave height weighted by headwind exposure")


def panel_full_metrics(reports: list[TwinReport]) -> None:
    _section("Full Metrics — Anomaly Detail")

    col_w = [22, 10, 10, 8, 8, 9, 10, 10, 9]
    headers = [
        "Timestamp", "Actual MW", "Expected MW", "Anomaly", "Score",
        "Deviation", "Trend/smp", "HeadWind", "Beaufort",
    ]
    header_line = "  " + "".join(h.ljust(w) for h, w in zip(headers, col_w))
    print(_colour(header_line, _BOLD))
    print("  " + "─" * sum(col_w))

    for r in reports:
        act_mw = f"{r.actual_shaft_power_w / 1e6:.2f}" if r.actual_shaft_power_w else "  n/a"
        exp_mw = f"{r.expected_shaft_power_w / 1e6:.2f}" if r.expected_shaft_power_w else "  n/a"
        anomaly_str = _colour("  ANOMALY", _BG_RED, _BOLD, _WHITE) if r.anomaly_detected else _colour("  Normal ", _BG_GREEN, _BOLD, _WHITE)
        score_col = _colour(f"{r.anomaly_score:8.3f}", _RED if r.anomaly_detected else _GREEN)
        dev_col = _colour(f"{r.efficiency_deviation_pct:+8.2f}%", _RED if r.anomaly_detected else _GREEN)
        trend_col = f"{r.degradation_trend_pct_per_sample:+8.2f}%"
        hw_col = f"{r.relative_head_wind_mps:+8.2f}"
        bft_col = f"{r.beaufort_scale:8d}"

        row = (
            f"  {r.operating_point.timestamp:<22}"
            f"{act_mw:>10}"
            f"{exp_mw:>10} "
            f"{anomaly_str} "
            f"{score_col} "
            f"{dev_col} "
            f"{trend_col} "
            f"{hw_col} "
            f"{bft_col}"
        )
        print(row)


# ── synthetic fallback history (used when running without the data file) ─────

def _synthetic_history() -> list[OperatingPoint]:
    return [
        OperatingPoint("2026-03-20T00:00:00Z", shaft_rpm=98, vessel_speed_knots=14.8, torque_kNm=820, thrust_kN=168),
        OperatingPoint("2026-03-20T00:05:00Z", shaft_rpm=98, vessel_speed_knots=14.5, torque_kNm=835, thrust_kN=164),
        OperatingPoint("2026-03-20T00:10:00Z", shaft_rpm=98, vessel_speed_knots=14.0, torque_kNm=860, thrust_kN=157),
        OperatingPoint("2026-03-20T00:15:00Z", shaft_rpm=98, vessel_speed_knots=13.6, torque_kNm=885, thrust_kN=149),
        OperatingPoint("2026-03-20T00:20:00Z", shaft_rpm=98, vessel_speed_knots=13.1, torque_kNm=910, thrust_kN=141),
    ]


# ── entry point ──────────────────────────────────────────────────────────────

def main() -> None:
    print()
    print(_colour("  Marine Propeller Digital Twin — Demo  ", _BOLD, "\033[44m", _WHITE))
    print(_colour("  Vessel: CPS Poseidon  |  Source: FuelCast benchmark preview  ", _BOLD, "\033[44m", _WHITE))

    # Try the real FuelCast data first; fall back to synthetic demo history.
    DATA_PATH = "data/fuelcast_cps_poseidon_preview.csv"
    try:
        rows = load_fuelcast_preview(DATA_PATH)
        print(f"\n  Loaded {len(rows)} rows from {DATA_PATH}")
        reports = evaluate_fuelcast_rows(rows, calibration_samples=3)
        from digital_twin.fuelcast import build_power_curve_twin
        twin = build_power_curve_twin(rows, calibration_samples=3)
        print(f"  Calibration samples: 3  |  Evaluation samples: {len(reports)}")
    except FileNotFoundError:
        print(f"\n  {DATA_PATH!r} not found — using synthetic data instead.")
        twin = PropellerDigitalTwin(
            diameter_m=6.2,
            pitch_ratio=0.92,
            design_rpm=100,
            design_speed_knots=15.0,
            design_slip=0.11,
            anomaly_threshold_pct=7.5,
        )
        reports = twin.evaluate(_synthetic_history())

    panel_kpi(reports, twin)
    panel_efficiency_and_power(reports)
    panel_anomaly_scores(reports)
    panel_environmental(reports)
    panel_full_metrics(reports)

    print()
    print(_colour("  Dashboard exports  ", _BOLD))
    print("  • Grafana metrics CSV : data/grafana/fuelcast_metrics.csv")
    print("  • Grafana baseline JSON: data/grafana/fuelcast_baseline.json")
    print("  Regenerate with: python scripts/export_fuelcast_metrics.py")
    print()


if __name__ == "__main__":
    main()
