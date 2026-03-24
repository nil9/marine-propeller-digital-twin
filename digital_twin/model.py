from __future__ import annotations

from dataclasses import dataclass
from statistics import mean
from typing import Iterable, Sequence


@dataclass(slots=True)
class OperatingPoint:
    timestamp: str
    shaft_rpm: float
    vessel_speed_knots: float
    torque_kNm: float
    thrust_kN: float | None = None
    shaft_power_w: float | None = None
    speed_through_water_mps: float | None = None
    fuel_consumption_kg_s: float | None = None

    @property
    def vessel_speed_mps(self) -> float:
        if self.speed_through_water_mps is not None:
            return self.speed_through_water_mps
        return self.vessel_speed_knots * 0.514444


@dataclass(slots=True)
class TwinReport:
    operating_point: OperatingPoint
    expected_efficiency: float
    actual_efficiency: float
    efficiency_deviation_pct: float
    anomaly_score: float
    anomaly_detected: bool
    degradation_trend_pct_per_sample: float
    expected_shaft_power_w: float | None = None
    actual_shaft_power_w: float | None = None


class PropellerDigitalTwin:
    """Baseline digital twin for marine propeller performance.

    The model supports two modes:
    1. A physics-style efficiency estimate when thrust is available.
    2. A calibrated ideal power-curve mode for real telemetry where thrust is
       not available, such as the FuelCast benchmark preview data.
    """

    def __init__(
        self,
        diameter_m: float,
        pitch_ratio: float,
        design_rpm: float,
        design_speed_knots: float,
        design_slip: float = 0.12,
        anomaly_threshold_pct: float = 8.0,
        design_shaft_power_w: float | None = None,
        speed_power_exponent: float = 3.0,
        calibrated_power_coefficient: float | None = None,
    ) -> None:
        self.diameter_m = diameter_m
        self.pitch_ratio = pitch_ratio
        self.design_rpm = design_rpm
        self.design_speed_knots = design_speed_knots
        self.design_slip = design_slip
        self.anomaly_threshold_pct = anomaly_threshold_pct
        self.design_shaft_power_w = design_shaft_power_w
        self.speed_power_exponent = speed_power_exponent
        self.calibrated_power_coefficient = calibrated_power_coefficient

    @classmethod
    def from_power_curve(
        cls,
        history: Sequence[OperatingPoint],
        *,
        diameter_m: float,
        pitch_ratio: float,
        design_rpm: float,
        design_speed_knots: float,
        design_slip: float = 0.12,
        anomaly_threshold_pct: float = 2.0,
        speed_power_exponent: float = 3.0,
    ) -> "PropellerDigitalTwin":
        coefficient = cls._fit_power_coefficient(history, speed_power_exponent)
        design_shaft_power = mean(
            point.shaft_power_w for point in history if point.shaft_power_w is not None
        )
        return cls(
            diameter_m=diameter_m,
            pitch_ratio=pitch_ratio,
            design_rpm=design_rpm,
            design_speed_knots=design_speed_knots,
            design_slip=design_slip,
            anomaly_threshold_pct=anomaly_threshold_pct,
            design_shaft_power_w=design_shaft_power,
            speed_power_exponent=speed_power_exponent,
            calibrated_power_coefficient=coefficient,
        )

    @property
    def pitch_m(self) -> float:
        return self.diameter_m * self.pitch_ratio

    def expected_efficiency(self, point: OperatingPoint) -> float:
        advance_ratio = self._advance_ratio(point.shaft_rpm, point.vessel_speed_mps)
        slip = max(0.02, min(0.45, self.design_slip + 0.08 * (advance_ratio - 0.9)))
        open_water_efficiency = max(0.35, min(0.82, 0.72 - abs(advance_ratio - 0.95) * 0.18))
        loading_penalty = min(0.12, point.torque_kNm / 1500.0)
        return max(0.2, open_water_efficiency - loading_penalty * slip)

    def expected_shaft_power(self, point: OperatingPoint) -> float | None:
        if self.calibrated_power_coefficient is not None:
            return self.calibrated_power_coefficient * (point.vessel_speed_mps ** self.speed_power_exponent)
        if self.design_shaft_power_w is None:
            return None
        design_speed_mps = self.design_speed_knots * 0.514444
        speed_ratio = point.vessel_speed_mps / max(design_speed_mps, 0.1)
        rpm_ratio = max(point.shaft_rpm / max(self.design_rpm, 1.0), 0.1)
        return self.design_shaft_power_w * (speed_ratio ** self.speed_power_exponent) * (0.35 + 0.65 * rpm_ratio)

    def actual_efficiency(self, point: OperatingPoint) -> tuple[float, float | None]:
        if point.thrust_kN is not None:
            shaft_power_w = point.shaft_power_w or self._shaft_power_w(point.shaft_rpm, point.torque_kNm)
            useful_power_w = point.thrust_kN * 1000.0 * point.vessel_speed_mps
            if shaft_power_w <= 0:
                return 0.0, shaft_power_w
            return max(0.0, min(1.0, useful_power_w / shaft_power_w)), shaft_power_w

        if point.shaft_power_w is None:
            return 0.0, None

        expected_power = self.expected_shaft_power(point)
        if not expected_power or point.shaft_power_w <= 0:
            return 0.0, point.shaft_power_w
        efficiency_proxy = expected_power / point.shaft_power_w
        return max(0.0, min(1.2, efficiency_proxy)), point.shaft_power_w

    def evaluate(self, history: Sequence[OperatingPoint]) -> list[TwinReport]:
        if not history:
            return []

        reports: list[TwinReport] = []
        deviations: list[float] = []

        for point in history:
            expected_eff = self.expected_efficiency(point) if point.thrust_kN is not None else 1.0
            actual_eff, actual_power = self.actual_efficiency(point)
            expected_power = self.expected_shaft_power(point)
            deviation_pct = (actual_eff - expected_eff) / expected_eff * 100.0 if expected_eff else 0.0
            deviations.append(deviation_pct)
            trend = self._degradation_trend(deviations)
            anomaly_score = abs(deviation_pct)
            reports.append(
                TwinReport(
                    operating_point=point,
                    expected_efficiency=expected_eff,
                    actual_efficiency=actual_eff,
                    efficiency_deviation_pct=deviation_pct,
                    anomaly_score=anomaly_score,
                    anomaly_detected=anomaly_score >= self.anomaly_threshold_pct,
                    degradation_trend_pct_per_sample=trend,
                    expected_shaft_power_w=expected_power,
                    actual_shaft_power_w=actual_power,
                )
            )

        return reports

    def fleet_baseline(self, points: Iterable[OperatingPoint]) -> dict[str, float]:
        points = list(points)
        expected = [self.expected_efficiency(point) if point.thrust_kN is not None else 1.0 for point in points]
        actual = [self.actual_efficiency(point)[0] for point in points]
        return {
            "mean_expected_efficiency": mean(expected) if expected else 0.0,
            "mean_actual_efficiency": mean(actual) if actual else 0.0,
            "mean_efficiency_gap_pct": (
                mean(((a - e) / e) * 100.0 for a, e in zip(actual, expected) if e)
                if expected
                else 0.0
            ),
        }

    @staticmethod
    def _fit_power_coefficient(history: Sequence[OperatingPoint], exponent: float) -> float:
        coefficients = [
            point.shaft_power_w / max(point.vessel_speed_mps, 0.1) ** exponent
            for point in history
            if point.shaft_power_w is not None and point.vessel_speed_mps > 0
        ]
        if not coefficients:
            raise ValueError("Need shaft power and vessel speed to fit power coefficient")
        return mean(coefficients)

    def _advance_ratio(self, shaft_rpm: float, vessel_speed_mps: float) -> float:
        rev_per_sec = max(shaft_rpm / 60.0, 0.01)
        return vessel_speed_mps / (rev_per_sec * self.diameter_m)

    @staticmethod
    def _shaft_power_w(shaft_rpm: float, torque_kNm: float) -> float:
        omega = (shaft_rpm * 2.0 * 3.141592653589793) / 60.0
        return omega * torque_kNm * 1000.0

    @staticmethod
    def _degradation_trend(deviations: Sequence[float]) -> float:
        if len(deviations) < 2:
            return 0.0
        first = deviations[0]
        last = deviations[-1]
        return (last - first) / (len(deviations) - 1)
