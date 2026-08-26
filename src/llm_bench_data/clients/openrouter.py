"""OpenRouter API client with retries, error classification, and usage parsing."""

import time
from typing import Any

import httpx
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from llm_bench_data.clients.base import LLMClient
from llm_bench_data.core.config import Settings
from llm_bench_data.core.exceptions import (
    APIError,
    ModelNotFoundError,
    RateLimitError,
    TimeoutError,
)
from llm_bench_data.core.models import ChatRequest, ChatResponse


class OpenRouterClient(LLMClient):
    """HTTP client for the OpenRouter chat completions endpoint."""

    BASE_URL = "https://openrouter.ai/api/v1"

    def __init__(self, settings: Settings | None = None) -> None:
        """Initialize an HTTP client with the user's settings and API key."""
        self.settings = settings or Settings()
        if self.settings.openrouter_api_key is None:
            raise ValueError("OPENROUTER_API_KEY is required for the OpenRouter provider")
        api_key = self.settings.openrouter_api_key.get_secret_value()
        self._client = httpx.Client(
            base_url=self.BASE_URL,
            timeout=httpx.Timeout(self.settings.default_timeout),
            headers={
                "Authorization": f"Bearer {api_key}",
                "HTTP-Referer": self.settings.referer,
                "Content-Type": "application/json",
            },
        )

    def _is_retryable(self, exception: BaseException) -> bool:
        """Determine whether a failed request is worth retrying."""
        if isinstance(
            exception,
            (
                httpx.TimeoutException,
                httpx.NetworkError,
                httpx.RemoteProtocolError,
                httpx.ConnectError,
            ),
        ):
            return True
        return getattr(exception, "retryable", False)

    def _raise_for_status(self, response: httpx.Response) -> None:
        """Map HTTP errors to typed domain exceptions."""
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            body = exc.response.text[:200]
            if status == 404:
                raise ModelNotFoundError(f"Model not found: {body}") from exc
            if status == 429:
                raise RateLimitError(f"Rate limited: {body}") from exc
            if status >= 500:
                raise APIError(f"Server error {status}: {body}", retryable=True) from exc
            raise APIError(f"HTTP {status}: {body}") from exc

    def _post_with_retries(self, request: ChatRequest) -> httpx.Response:
        """POST to /chat/completions with tenacity-powered retries."""

        @retry(
            retry=retry_if_exception(self._is_retryable),
            stop=stop_after_attempt(self.settings.default_retries),
            wait=wait_exponential(multiplier=1, min=1, max=10),
            reraise=True,
        )
        def _post() -> httpx.Response:
            response = self._client.post("/chat/completions", json=request.to_api_body())
            self._raise_for_status(response)
            return response

        return _post()

    def chat(self, request: ChatRequest) -> ChatResponse:
        """Send a chat request and return a parsed response."""
        start = time.monotonic()
        try:
            response = self._post_with_retries(request)
        except httpx.TimeoutException as exc:
            elapsed = int((time.monotonic() - start) * 1000)
            raise TimeoutError(f"OpenRouter request timed out after {elapsed} ms") from exc
        except httpx.ConnectError as exc:
            raise APIError(f"Could not connect to OpenRouter: {exc}", retryable=True) from exc

        elapsed_ms = int((time.monotonic() - start) * 1000)
        return self._parse_response(response.json(), request.model_id, elapsed_ms)

    def _parse_response(
        self,
        payload: dict[str, Any],
        model_id: str,
        elapsed_ms: int,
    ) -> ChatResponse:
        """Build a ChatResponse from the OpenRouter JSON payload."""
        try:
            content = payload["choices"][0]["message"]["content"] or ""
            usage = payload.get("usage", {})
            prompt_tokens = int(usage.get("prompt_tokens", 0))
            completion_tokens = int(usage.get("completion_tokens", 0))
            total_tokens = int(usage.get("total_tokens", 0)) if "total_tokens" in usage else None
            reasoning_tokens = usage.get("completion_tokens_details", {}).get("reasoning_tokens")
        except (KeyError, IndexError, TypeError) as exc:
            raise APIError(f"Unexpected OpenRouter response shape: {payload}") from exc

        response = ChatResponse(
            model_id=model_id,
            content=content,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            reasoning_tokens=reasoning_tokens,
            total_tokens=total_tokens,
            elapsed_ms=elapsed_ms,
        )

        # Validate before returning: a malformed provider payload with negative
        # token counts must not flow into Measurement rows undetected. Deferred
        # import avoids a module-load cycle between clients and validation.
        from llm_bench_data.validation.validators import ResponseValidator

        errors = ResponseValidator.validate(response)
        if errors:
            raise APIError("Invalid OpenRouter response: " + "; ".join(errors))

        return response

    def close(self) -> None:
        """Close the underlying HTTP client."""
        self._client.close()

    def __enter__(self) -> "OpenRouterClient":
        """Enter the runtime context for the client."""
        return self

    def __exit__(self, *exc: object) -> None:
        """Exit the runtime context and close the HTTP client."""
        self.close()
