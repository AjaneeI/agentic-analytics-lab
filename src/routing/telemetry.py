"""Structured telemetry contracts for control-plane evaluation."""

from __future__ import annotations

from dataclasses import dataclass

from src.routing.control_plane import ReasonCode, RouteDecision
from src.routing.validation import ValidationResult


@dataclass(frozen=True)
class RouteTelemetry:
    """One task-level record for routing, validation, and system economics."""

    task_id: str
    router_version: str
    route: str
    route_reason_code: str
    router_latency_seconds: float
    router_input_tokens: int
    router_output_tokens: int
    worker: str | None
    tool_calls: int
    worker_input_tokens: int
    worker_output_tokens: int
    validator_disposition: str | None
    validator_reason: str | None
    escalation_reason: str | None
    total_model_calls: int
    total_latency_seconds: float
    estimated_cost_usd: float | None
    task_success: bool | None
    human_intervention: bool

    def __post_init__(self) -> None:
        if not self.task_id.strip():
            raise ValueError("task_id must be a non-empty string.")
        if not self.router_version.strip():
            raise ValueError("router_version must be a non-empty string.")

        numeric_fields = {
            "router_latency_seconds": self.router_latency_seconds,
            "router_input_tokens": self.router_input_tokens,
            "router_output_tokens": self.router_output_tokens,
            "tool_calls": self.tool_calls,
            "worker_input_tokens": self.worker_input_tokens,
            "worker_output_tokens": self.worker_output_tokens,
            "total_model_calls": self.total_model_calls,
            "total_latency_seconds": self.total_latency_seconds,
        }
        for name, value in numeric_fields.items():
            if value < 0:
                raise ValueError(f"{name} must be non-negative.")

        if self.estimated_cost_usd is not None and self.estimated_cost_usd < 0:
            raise ValueError("estimated_cost_usd must be non-negative when provided.")


def build_route_telemetry(
    *,
    task_id: str,
    router_version: str,
    decision: RouteDecision,
    router_latency_seconds: float,
    validation: ValidationResult | None = None,
    router_input_tokens: int = 0,
    router_output_tokens: int = 0,
    worker: str | None = None,
    tool_calls: int = 0,
    worker_input_tokens: int = 0,
    worker_output_tokens: int = 0,
    escalation_reason: str | None = None,
    total_model_calls: int = 0,
    total_latency_seconds: float = 0.0,
    estimated_cost_usd: float | None = None,
    task_success: bool | None = None,
    human_intervention: bool = False,
) -> RouteTelemetry:
    """Build a telemetry record without granting the router any authority."""

    return RouteTelemetry(
        task_id=task_id,
        router_version=router_version,
        route=decision.route.value,
        route_reason_code=_reason_value(decision.reason_code),
        router_latency_seconds=router_latency_seconds,
        router_input_tokens=router_input_tokens,
        router_output_tokens=router_output_tokens,
        worker=worker,
        tool_calls=tool_calls,
        worker_input_tokens=worker_input_tokens,
        worker_output_tokens=worker_output_tokens,
        validator_disposition=(
            validation.disposition.value if validation is not None else None
        ),
        validator_reason=(
            validation.reason.value if validation is not None else None
        ),
        escalation_reason=escalation_reason,
        total_model_calls=total_model_calls,
        total_latency_seconds=total_latency_seconds,
        estimated_cost_usd=estimated_cost_usd,
        task_success=task_success,
        human_intervention=human_intervention,
    )


def _reason_value(reason: ReasonCode) -> str:
    return reason.value
