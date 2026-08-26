"""Domain exceptions for the LLM Cost Comparison pipeline."""


class LLMCCError(Exception):
    """Base exception for the package."""


class ConfigurationError(LLMCCError):
    """Raised when configuration is missing or invalid."""


class CatalogError(LLMCCError):
    """Raised when a catalog file or lookup fails."""


class APIError(LLMCCError):
    """Raised when an external API call fails."""

    def __init__(self, message: str, *, retryable: bool = False) -> None:
        """Create an API error with an optional retry flag."""
        super().__init__(message)
        self.retryable = retryable


class ModelNotFoundError(APIError):
    """Raised when the requested model is not available on the provider."""

    def __init__(self, message: str) -> None:
        """Create a non-retryable model-not-found error."""
        super().__init__(message, retryable=False)


class RateLimitError(APIError):
    """Raised when a provider rate limit is hit."""

    def __init__(self, message: str) -> None:
        """Create a retryable rate-limit error."""
        super().__init__(message, retryable=True)


class TimeoutError(APIError):
    """Raised when an API call times out."""

    def __init__(self, message: str) -> None:
        """Create a retryable timeout error."""
        super().__init__(message, retryable=True)


class ValidationError(LLMCCError):
    """Raised when data fails a validation check."""


class StorageError(LLMCCError):
    """Raised when a database operation fails."""
