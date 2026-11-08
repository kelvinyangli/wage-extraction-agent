"""Safe loader for versioned, mock-only service fixtures."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from pydantic import Field

from wage_extraction_agent.adapters.base import PromptStage
from wage_extraction_agent.adapters.errors import FixtureConfigurationError
from wage_extraction_agent.models.common import StrictModel


class FixtureManifest(StrictModel):
    fixture_version: str = Field(min_length=1)
    schema_version: int = Field(ge=1)
    mock_only: bool
    description: str = Field(min_length=1)
    files: dict[str, str]


class FixtureRepository:
    """Load fixture JSON from one explicitly selected version directory."""

    def __init__(self, root: Path, version: str = "v1") -> None:
        self.root = root.resolve()
        self.version_dir = (self.root / version).resolve()
        if self.root not in self.version_dir.parents:
            raise FixtureConfigurationError("fixture version escapes fixture root")

        manifest_data = self._read_json(self.version_dir / "manifest.json")
        try:
            self.manifest = FixtureManifest.model_validate(manifest_data)
        except Exception as exc:  # Pydantic error detail is retained as the cause.
            raise FixtureConfigurationError("invalid fixture manifest") from exc

        if not self.manifest.mock_only:
            raise FixtureConfigurationError("prototype fixtures must be marked mock_only")
        if self.manifest.schema_version != 1:
            raise FixtureConfigurationError("unsupported fixture schema version")

        self._document_payloads = self._load_named_file("document_intelligence")
        self._llm_payloads = self._load_named_file("llm_responses")

    @property
    def version(self) -> str:
        return self.manifest.fixture_version

    def document_payload(self, document_name: str) -> dict[str, Any]:
        try:
            payload = self._document_payloads[document_name]
        except KeyError as exc:
            raise FixtureConfigurationError(
                f"unknown document fixture: {document_name}"
            ) from exc
        return deepcopy(payload)

    def llm_payload(
        self, stage: PromptStage, fixture_key: str = "default"
    ) -> dict[str, Any]:
        try:
            payload = self._llm_payloads[stage.value][fixture_key]
        except KeyError as exc:
            raise FixtureConfigurationError(
                f"unknown LLM fixture: {stage.value}/{fixture_key}"
            ) from exc
        return deepcopy(payload)

    def _load_named_file(self, name: str) -> dict[str, Any]:
        try:
            relative_name = self.manifest.files[name]
        except KeyError as exc:
            raise FixtureConfigurationError(
                f"manifest does not define fixture file: {name}"
            ) from exc

        path = (self.version_dir / relative_name).resolve()
        if self.version_dir not in path.parents:
            raise FixtureConfigurationError(f"fixture file escapes version directory: {name}")
        data = self._read_json(path)
        if not isinstance(data, dict):
            raise FixtureConfigurationError(f"fixture file must contain an object: {name}")
        return data

    @staticmethod
    def _read_json(path: Path) -> Any:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise FixtureConfigurationError(f"cannot load fixture JSON: {path}") from exc

