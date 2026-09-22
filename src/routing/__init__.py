"""Control-plane routing primitives."""

from src.routing.control_plane import (
    ExecutionRoute,
    ReasonCode,
    RouteDecision,
    RouteFeatures,
    TaskContext,
    classify_route,
    extract_route_features,
    parse_execution_route,
    route_task,
)
from src.routing.deterministic_handlers import (
    DeterministicHandlerDeclined,
    HandlerKey,
    HandlerResult,
    execute_deterministic_handler,
)
from src.routing.telemetry import RouteTelemetry, build_route_telemetry
from src.routing.validation import (
    ValidationContext,
    ValidationDisposition,
    ValidationReason,
    ValidationResult,
    validate_execution,
)

__all__ = [
    "ExecutionRoute",
    "ReasonCode",
    "RouteDecision",
    "RouteFeatures",
    "TaskContext",
    "classify_route",
    "extract_route_features",
    "parse_execution_route",
    "route_task",
    "DeterministicHandlerDeclined",
    "HandlerKey",
    "HandlerResult",
    "execute_deterministic_handler",
    "RouteTelemetry",
    "build_route_telemetry",
    "ValidationContext",
    "ValidationDisposition",
    "ValidationReason",
    "ValidationResult",
    "validate_execution",
]
