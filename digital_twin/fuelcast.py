from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .model import OperatingPoint, PropellerDigitalTwin, TwinReport


@dataclass(slots=True)
class FuelCastRow:
    subset: str
    index: int
    consumer_total_momentary_fuel_kg_s: float
    consumer_total_shaft_power_w: float
    environment_seafloor_depth_m: float
    propeller_port_rotation_speed_rpm: float
    propeller_port_shaft_power_w: float
    propeller_port_shaft_torque_nm: float
    propeller_starboard_rotation_speed_rpm: float
    propeller_starboard_shaft_power_w: float
    propeller_starboard_shaft_torque_nm: float
    propeller_total_shaft_power_w: float
    ship_bearing_deg: float | None
    ship_heading_deg: float
    ship_speed_over_ground_mps: float
    ship_speed_through_water_mps: float

    def to_operating_point(self) -> OperatingPoint:
        mean_rpm = (self.propeller_port_rotation_speed_rpm + self.propeller_starboard_rotation_speed_rpm) / 2.0
        mean_torque_knm = (
            self.propeller_port_shaft_torque_nm + self.propeller_starboard_shaft_torque_nm
        ) / 2.0 / 1000.0
        return OperatingPoint(
            timestamp=f"{self.subset}:{self.index}",
            shaft_rpm=mean_rpm,
            vessel_speed_knots=self.ship_speed_over_ground_mps / 0.514444,
            torque_kNm=mean_torque_knm,
            thrust_kN=None,
            shaft_power_w=self.propeller_total_shaft_power_w,
            speed_through_water_mps=self.ship_speed_through_water_mps,
            fuel_consumption_kg_s=self.consumer_total_momentary_fuel_kg_s,
        )


def load_fuelcast_preview(path: str | Path) -> list[FuelCastRow]:
    with Path(path).open(newline="") as handle:
        reader = csv.DictReader(handle)
        rows: list[FuelCastRow] = []
        for raw in reader:
            rows.append(
                FuelCastRow(
                    subset=raw["subset"],
                    index=int(raw["index"]),
                    consumer_total_momentary_fuel_kg_s=float(raw["consumer_total_momentary_fuel_kg_s"]),
                    consumer_total_shaft_power_w=float(raw["consumer_total_shaft_power_w"]),
                    environment_seafloor_depth_m=float(raw["environment_seafloor_depth_m"]),
                    propeller_port_rotation_speed_rpm=float(raw["propeller_port_rotation_speed_rpm"]),
                    propeller_port_shaft_power_w=float(raw["propeller_port_shaft_power_w"]),
                    propeller_port_shaft_torque_nm=float(raw["propeller_port_shaft_torque_nm"]),
                    propeller_starboard_rotation_speed_rpm=float(raw["propeller_starboard_rotation_speed_rpm"]),
                    propeller_starboard_shaft_power_w=float(raw["propeller_starboard_shaft_power_w"]),
                    propeller_starboard_shaft_torque_nm=float(raw["propeller_starboard_shaft_torque_nm"]),
                    propeller_total_shaft_power_w=float(raw["propeller_total_shaft_power_w"]),
                    ship_bearing_deg=float(raw["ship_bearing_deg"]) if raw["ship_bearing_deg"] else None,
                    ship_heading_deg=float(raw["ship_heading_deg"]),
                    ship_speed_over_ground_mps=float(raw["ship_speed_over_ground_mps"]),
                    ship_speed_through_water_mps=float(raw["ship_speed_through_water_mps"]),
                )
            )
        return rows


def build_power_curve_twin(rows: Iterable[FuelCastRow], calibration_samples: int = 3) -> PropellerDigitalTwin:
    operating_points = [row.to_operating_point() for row in rows]
    calibration_history = operating_points[:calibration_samples]
    if not calibration_history:
        raise ValueError("Need at least one calibration sample")
    design_rpm = sum(point.shaft_rpm for point in calibration_history) / len(calibration_history)
    design_speed_knots = sum(point.vessel_speed_knots for point in calibration_history) / len(calibration_history)
    return PropellerDigitalTwin.from_power_curve(
        calibration_history,
        diameter_m=6.2,
        pitch_ratio=0.92,
        design_rpm=design_rpm,
        design_speed_knots=design_speed_knots,
        anomaly_threshold_pct=0.75,
    )


def evaluate_fuelcast_rows(rows: Iterable[FuelCastRow], calibration_samples: int = 3) -> list[TwinReport]:
    rows = list(rows)
    twin = build_power_curve_twin(rows, calibration_samples=calibration_samples)
    return twin.evaluate([row.to_operating_point() for row in rows])
