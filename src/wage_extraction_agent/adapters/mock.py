"""Deterministic mock adapters with injectable failure sequences."""

from __future__ import annotations

from collections import deque
from collections.abc import Mapping, Sequence
from typing import Any

from pydantic import ValidationError

from wage_extraction_agent.adapters.base import FaultMode, PromptStage
from wage_extraction_agent.adapters.errors import (
    AdapterTimeoutError,
    MalformedAdapterResponseError,
    PermanentAdapterError,
    TransientAdapterError,
)
from wage_extraction_agent.adapters.fixtures import FixtureRepository
from wage_extraction_agent.models.evidence import DocumentEvidence


class FaultPlan:
    """Consume predeclared faults by call key without sleeping or using randomness."""

    def __init__(
        self, faults: Mapping[str, Sequence[FaultMode | str]] | None = None
    ) -> None:
        self._faults = {
            key: deque(FaultMode(mode) for mode in modes)
            for key, modes in (faults or {}).items()
        }

    def consume(self, call_key: str) -> FaultMode | None:
        queue = self._faults.get(call_key)
        return queue.popleft() if queue else None


def _raise_transport_fault(mode: FaultMode | None, call_key: str) -> bool:
    if mode is FaultMode.TIMEOUT:
        raise AdapterTimeoutError("injected mock timeout", call_key=call_key)
    if mode is FaultMode.TRANSIENT:
        raise TransientAdapterError("injected transient failure", call_key=call_key)
    if mode is FaultMode.PERMANENT:
        raise PermanentAdapterError("injected permanent failure", call_key=call_key)
    return mode is FaultMode.MALFORMED


class MockDocumentIntelligenceAdapter:
    def __init__(
        self, repository: FixtureRepository, fault_plan: FaultPlan | None = None
    ) -> None:
        self.repository = repository
        self.fault_plan = fault_plan or FaultPlan()
        self.version = f"mock-di/{repository.version}"

    async def analyze(self, document_name: str) -> DocumentEvidence:
        call_key = f"document_intelligence:{document_name}"
        malformed = _raise_transport_fault(
            self.fault_plan.consume(call_key), call_key
        )
        payload: Any = self.repository.document_payload(document_name)
        if malformed:
            payload = {"pages": "not-a-list"}
        try:
            return DocumentEvidence.model_validate(payload)
        except ValidationError as exc:
            raise MalformedAdapterResponseError(
                "mock Document Intelligence response failed normalization",
                call_key=call_key,
            ) from exc


class MockLlmAdapter:
    def __init__(
        self, repository: FixtureRepository, fault_plan: FaultPlan | None = None
    ) -> None:
        self.repository = repository
        self.fault_plan = fault_plan or FaultPlan()
        self.version = f"mock-llm/{repository.version}"

    async def invoke(
        self, stage: PromptStage, fixture_key: str = "default"
    ) -> dict[str, Any]:
        call_key = f"llm:{stage.value}:{fixture_key}"
        malformed = _raise_transport_fault(
            self.fault_plan.consume(call_key), call_key
        )
        if malformed:
            return {"__malformed_mock_response__": True}
        return self.repository.llm_payload(stage, fixture_key)

