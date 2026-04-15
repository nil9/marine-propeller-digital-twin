from __future__ import annotations

from dataclasses import dataclass
from math import exp

from .model import TwinReport


@dataclass(slots=True)
class MaintenancePolicyConfig:
    sample_interval_hours: float = 1.0
    forecast_days: int = 30
    fuel_price_usd_per_ton: float = 650.0
    sfoc_kg_per_kwh: float = 0.18
    planned_drydock_cost_usd: float = 250_000.0
    planned_offhire_cost_usd: float = 120_000.0
    unplanned_failure_cost_usd: float = 900_000.0
    decision_margin_pct: float = 0.15
    anomaly_weight: float = 0.35
    efficiency_weight: float = 0.25
    power_gap_weight: float = 0.20
    trend_weight: float = 0.20


@dataclass(slots=True)
class MaintenanceAssessment:
    health_risk_index: float
    maintenance_state: str
    recommended_action: str
    projected_wait_cost_usd: float
    projected_act_now_cost_usd: float
    projected_cost_delta_usd: float
    drydock_recommended: bool


def assess_maintenance_state(
    report: TwinReport,
    threshold: float,
    *,
    config: MaintenancePolicyConfig | None = None,
) -> MaintenanceAssessment:
    cfg = config or MaintenancePolicyConfig()

    anomaly_subscore = _bounded_100(report.anomaly_score / max(3.0 * threshold, 0.001) * 100.0)
    efficiency_subscore = _bounded_100(max(0.0, -report.efficiency_deviation_pct) / 12.0 * 100.0)

    expected_power = report.expected_shaft_power_w
    actual_power = report.actual_shaft_power_w
    power_gap_kw = 0.0
    if expected_power is not None and actual_power is not None:
        power_gap_kw = max(0.0, (actual_power - expected_power) / 1000.0)
    power_gap_subscore = _bounded_100(power_gap_kw / 600.0 * 100.0)

    trend_subscore = _bounded_100(max(0.0, report.degradation_trend_pct_per_sample) / 12.5 * 100.0)

    health_risk_index = (
        cfg.anomaly_weight * anomaly_subscore
        + cfg.efficiency_weight * efficiency_subscore
        + cfg.power_gap_weight * power_gap_subscore
        + cfg.trend_weight * trend_subscore
    )

    maintenance_state = _maintenance_state(health_risk_index, report, threshold)
    recommended_action = _recommended_action(maintenance_state)

    wait_cost = _projected_wait_cost(report, cfg)
    act_now_cost = cfg.planned_drydock_cost_usd + cfg.planned_offhire_cost_usd
    margin = act_now_cost * cfg.decision_margin_pct
    delta = wait_cost - act_now_cost
    drydock_recommended = maintenance_state == "RED" and delta > margin

    return MaintenanceAssessment(
        health_risk_index=health_risk_index,
        maintenance_state=maintenance_state,
        recommended_action=recommended_action,
        projected_wait_cost_usd=wait_cost,
        projected_act_now_cost_usd=act_now_cost,
        projected_cost_delta_usd=delta,
        drydock_recommended=drydock_recommended,
    )


def _projected_wait_cost(report: TwinReport, cfg: MaintenancePolicyConfig) -> float:
    horizon_hours = cfg.forecast_days * 24.0
    steps = max(1, int(horizon_hours / max(cfg.sample_interval_hours, 0.01)))
    projected_efficiency_loss_pct = max(
        0.0,
        -report.efficiency_deviation_pct + report.degradation_trend_pct_per_sample * steps,
    )

    expected_power_w = report.expected_shaft_power_w or report.actual_shaft_power_w or 0.0
    expected_power_kw = expected_power_w / 1000.0
    projected_extra_power_kw = expected_power_kw * (projected_efficiency_loss_pct / 100.0)

    extra_energy_kwh = projected_extra_power_kw * horizon_hours
    extra_fuel_kg = extra_energy_kwh * cfg.sfoc_kg_per_kwh
    fuel_penalty_usd = (extra_fuel_kg / 1000.0) * cfg.fuel_price_usd_per_ton

    normalized_risk = min(2.5, report.anomaly_score / max(0.01, 3.0 * 0.75))
    failure_probability = min(0.75, 0.03 * exp(normalized_risk))
    failure_risk_usd = failure_probability * cfg.unplanned_failure_cost_usd

    return fuel_penalty_usd + failure_risk_usd


def _maintenance_state(health_risk_index: float, report: TwinReport, threshold: float) -> str:
    severe_triplet = (
        report.anomaly_score > 5.0
        and report.expected_shaft_power_w is not None
        and report.actual_shaft_power_w is not None
        and (report.actual_shaft_power_w - report.expected_shaft_power_w) > 300_000.0
        and report.efficiency_deviation_pct < -5.0
    )
    if health_risk_index >= 60.0 or severe_triplet:
        return "RED"
    if health_risk_index >= 35.0 or report.anomaly_score >= threshold:
        return "AMBER"
    return "GREEN"


def _recommended_action(maintenance_state: str) -> str:
    if maintenance_state == "RED":
        return "Schedule drydock optimization and immediate engineering inspection"
    if maintenance_state == "AMBER":
        return "Increase monitoring cadence and run propulsion inspection checklist"
    return "Continue normal monitoring"


def _bounded_100(value: float) -> float:
    return max(0.0, min(100.0, value))
