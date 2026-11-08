from pathlib import Path

from wage_extraction_agent.config import AppConfig
from wage_extraction_agent.models.enums import AdapterMode


def test_config_uses_portable_defaults(monkeypatch):
    for key in (
        "WAGE_AGENT_ADAPTER_MODE",
        "WAGE_AGENT_MAX_CONCURRENCY",
        "WAGE_AGENT_OUTPUT_DIR",
        "WAGE_AGENT_FIXTURE_ROOT",
        "WAGE_AGENT_PROMPT_ROOT",
        "WAGE_AGENT_PROMPT_VERSION",
        "WAGE_AGENT_EXTERNAL_TIMEOUT_SECONDS",
    ):
        monkeypatch.delenv(key, raising=False)

    config = AppConfig.from_env()

    assert config.adapter_mode is AdapterMode.MOCK
    assert config.max_concurrency == 2
    assert config.output_dir == Path("output")
    assert config.fixture_root == Path("fixtures/mock_services")
    assert config.prompt_root == Path("prompts")
    assert config.prompt_version == "v2"
    assert config.external_timeout_seconds == 30.0


def test_config_reads_environment(monkeypatch):
    monkeypatch.setenv("WAGE_AGENT_ADAPTER_MODE", "azure")
    monkeypatch.setenv("WAGE_AGENT_MAX_CONCURRENCY", "4")
    monkeypatch.setenv("WAGE_AGENT_OUTPUT_DIR", "results")
    monkeypatch.setenv("WAGE_AGENT_FIXTURE_ROOT", "test-fixtures")
    monkeypatch.setenv("WAGE_AGENT_PROMPT_ROOT", "test-prompts")
    monkeypatch.setenv("WAGE_AGENT_PROMPT_VERSION", "v2")
    monkeypatch.setenv("WAGE_AGENT_EXTERNAL_TIMEOUT_SECONDS", "12.5")

    config = AppConfig.from_env()

    assert config.adapter_mode is AdapterMode.AZURE
    assert config.max_concurrency == 4
    assert config.output_dir == Path("results")
    assert config.fixture_root == Path("test-fixtures")
    assert config.prompt_root == Path("test-prompts")
    assert config.prompt_version == "v2"
    assert config.external_timeout_seconds == 12.5

