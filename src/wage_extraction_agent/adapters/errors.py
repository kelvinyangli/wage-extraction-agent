"""Stable adapter errors used by deterministic retry routing."""


class AdapterError(RuntimeError):
    """Base external-adapter error with a machine-readable retry decision."""

    code = "ADAPTER_ERROR"
    retryable = False

    def __init__(self, message: str, *, call_key: str | None = None) -> None:
        super().__init__(message)
        self.call_key = call_key


class AdapterTimeoutError(AdapterError):
    code = "ADAPTER_TIMEOUT"
    retryable = True


class TransientAdapterError(AdapterError):
    code = "ADAPTER_TRANSIENT_FAILURE"
    retryable = True


class PermanentAdapterError(AdapterError):
    code = "ADAPTER_PERMANENT_FAILURE"
    retryable = False


class MalformedAdapterResponseError(AdapterError):
    code = "ADAPTER_MALFORMED_RESPONSE"
    retryable = False


class FixtureConfigurationError(AdapterError):
    code = "FIXTURE_CONFIGURATION_ERROR"
    retryable = False

