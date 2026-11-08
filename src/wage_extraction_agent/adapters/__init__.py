"""External-service adapter interfaces and mock implementations."""

from wage_extraction_agent.adapters.base import (
    DocumentIntelligenceAdapter,
    FaultMode,
    LlmAdapter,
    PromptStage,
)
from wage_extraction_agent.adapters.errors import (
    AdapterError,
    AdapterTimeoutError,
    FixtureConfigurationError,
    MalformedAdapterResponseError,
    PermanentAdapterError,
    TransientAdapterError,
)
from wage_extraction_agent.adapters.fixtures import FixtureRepository
from wage_extraction_agent.adapters.mock import (
    FaultPlan,
    MockDocumentIntelligenceAdapter,
    MockLlmAdapter,
)

__all__ = [
    "AdapterError",
    "AdapterTimeoutError",
    "DocumentIntelligenceAdapter",
    "FaultMode",
    "FaultPlan",
    "FixtureConfigurationError",
    "FixtureRepository",
    "LlmAdapter",
    "MalformedAdapterResponseError",
    "MockDocumentIntelligenceAdapter",
    "MockLlmAdapter",
    "PermanentAdapterError",
    "PromptStage",
    "TransientAdapterError",
]
