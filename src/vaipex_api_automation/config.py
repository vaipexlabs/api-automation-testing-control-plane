"""Validated runtime configuration shared by local and CI execution."""

import os
from dataclasses import dataclass
from urllib.parse import urlparse


@dataclass(frozen=True, slots=True)
class ApiEnvironment:
    base_url: str = "http://127.0.0.1:8080"
    timeout_seconds: float = 5.0
    correlation_prefix: str = "vaipex-api-test"

    def __post_init__(self) -> None:
        parsed = urlparse(self.base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("API base URL must be an absolute HTTP or HTTPS URL.")
        if self.timeout_seconds <= 0:
            raise ValueError("API timeout must be greater than zero.")
        if not self.correlation_prefix.strip():
            raise ValueError("Correlation prefix cannot be empty.")

    @classmethod
    def from_env(cls) -> "ApiEnvironment":
        timeout_value = os.getenv("VAIPEX_API_TIMEOUT_SECONDS", "5")
        try:
            timeout = float(timeout_value)
        except ValueError as error:
            raise ValueError("VAIPEX_API_TIMEOUT_SECONDS must be a number.") from error
        return cls(
            base_url=os.getenv("VAIPEX_API_BASE_URL", "http://127.0.0.1:8080").rstrip(
                "/"
            ),
            timeout_seconds=timeout,
            correlation_prefix=os.getenv(
                "VAIPEX_API_CORRELATION_PREFIX", "vaipex-api-test"
            ),
        )
