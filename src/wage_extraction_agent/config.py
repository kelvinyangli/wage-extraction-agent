"""Environment-based prototype configuration."""

from __future__ import annotations

import os
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from wage_extraction_agent.models.enums import AdapterMode


class AppConfig(BaseModel):
    """Runtime configuration with portable, non-secret defaults."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    adapter_mode: AdapterMode = AdapterMode.MOCK
    max_concurrency: int = Field(default=2, gt=0)
    output_dir: Path = Path("output")
    fixture_root: Path = Path("fixtures/mock_services")
    prompt_root: Path = Path("prompts")
    prompt_version: str = "v2"
    external_timeout_seconds: float = Field(default=30.0, gt=0)

    @classmethod
    def from_env(cls) -> "AppConfig":
        """Load supported settings without embedding computer-specific paths."""

        return cls(
            adapter_mode=os.getenv("WAGE_AGENT_ADAPTER_MODE", AdapterMode.MOCK.value),
            max_concurrency=os.getenv("WAGE_AGENT_MAX_CONCURRENCY", "2"),
            output_dir=os.getenv("WAGE_AGENT_OUTPUT_DIR", "output"),
            fixture_root=os.getenv(
                "WAGE_AGENT_FIXTURE_ROOT", "fixtures/mock_services"
            ),
            prompt_root=os.getenv("WAGE_AGENT_PROMPT_ROOT", "prompts"),
            prompt_version=os.getenv("WAGE_AGENT_PROMPT_VERSION", "v2"),
            external_timeout_seconds=os.getenv(
                "WAGE_AGENT_EXTERNAL_TIMEOUT_SECONDS", "30"
            ),
        )
