"""Strict loader for complete, versioned prompt bundles."""

from __future__ import annotations

import hashlib
from pathlib import Path
from string import Template

from pydantic import Field

from wage_extraction_agent.adapters import PromptStage
from wage_extraction_agent.models.common import StrictModel


class PromptBundleError(RuntimeError):
    pass


class PromptStageSpec(StrictModel):
    file: str = Field(min_length=1)
    required_variables: list[str] = Field(default_factory=list)


class PromptManifest(StrictModel):
    bundle_version: str = Field(min_length=1)
    schema_version: str = Field(min_length=1)
    status: str = Field(min_length=1)
    created_date: str = Field(min_length=1)
    approval: str = Field(min_length=1)
    evaluation_reference: str = Field(min_length=1)
    common_files: list[str]
    stages: dict[PromptStage, PromptStageSpec]


class RenderedPrompt(StrictModel):
    bundle_version: str
    bundle_sha256: str
    stage: PromptStage
    system: str
    user: str


class PromptBundle:
    """Load one complete prompt release and reject incomplete substitutions."""

    def __init__(self, root: Path, version: str = "v2") -> None:
        self.root = root.resolve()
        self.version_dir = (self.root / version).resolve()
        if self.root not in self.version_dir.parents:
            raise PromptBundleError("prompt version escapes prompt root")

        manifest_path = self.version_dir / "manifest.json"
        try:
            manifest_bytes = manifest_path.read_bytes()
            self.manifest = PromptManifest.model_validate_json(manifest_bytes)
        except Exception as exc:
            raise PromptBundleError("invalid prompt manifest") from exc

        if set(self.manifest.stages) != set(PromptStage):
            raise PromptBundleError("prompt bundle must define all approved stages")

        self._common = [self._read_text(path) for path in self.manifest.common_files]
        self._stage_templates: dict[PromptStage, Template] = {}
        digest = hashlib.sha256(manifest_bytes)
        for relative, content in zip(self.manifest.common_files, self._common):
            digest.update(relative.encode())
            digest.update(content.encode())
        for stage in sorted(self.manifest.stages, key=lambda item: item.value):
            spec = self.manifest.stages[stage]
            content = self._read_text(spec.file)
            template = Template(content)
            identifiers = set(template.get_identifiers())
            expected = set(spec.required_variables)
            if identifiers != expected:
                raise PromptBundleError(
                    f"template variables do not match manifest for {stage.value}"
                )
            self._stage_templates[stage] = template
            digest.update(spec.file.encode())
            digest.update(content.encode())
        self.sha256 = digest.hexdigest()

    @property
    def version(self) -> str:
        return self.manifest.bundle_version

    def render(self, stage: PromptStage, **variables: str) -> RenderedPrompt:
        spec = self.manifest.stages[stage]
        expected = set(spec.required_variables)
        supplied = set(variables)
        missing = expected - supplied
        unexpected = supplied - expected
        if missing or unexpected:
            raise PromptBundleError(
                f"invalid variables for {stage.value}; "
                f"missing={sorted(missing)}, unexpected={sorted(unexpected)}"
            )
        try:
            user = self._stage_templates[stage].substitute(variables)
        except (KeyError, ValueError) as exc:
            raise PromptBundleError(f"cannot render prompt stage: {stage.value}") from exc
        return RenderedPrompt(
            bundle_version=self.version,
            bundle_sha256=self.sha256,
            stage=stage,
            system="\n\n".join(self._common),
            user=user,
        )

    def _read_text(self, relative_name: str) -> str:
        path = (self.version_dir / relative_name).resolve()
        if self.version_dir not in path.parents:
            raise PromptBundleError("prompt file escapes version directory")
        try:
            content = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise PromptBundleError(f"cannot read prompt file: {relative_name}") from exc
        if not content.strip():
            raise PromptBundleError(f"prompt file is empty: {relative_name}")
        return content
