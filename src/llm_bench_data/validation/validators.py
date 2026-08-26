"""Domain validators for measurements and runs."""

from decimal import Decimal

from llm_bench_data.core.models import ChatResponse
from llm_bench_data.storage.models import Measurement


class MeasurementValidator:
    """Validate a measurement row before persistence."""

    @staticmethod
    def validate(measurement: Measurement) -> list[str]:
        """Return a list of validation error messages."""
        errors: list[str] = []
        if not measurement.model_slug:
            errors.append("model_slug is required")
        if measurement.status == "success":
            if measurement.prompt_tokens is None or measurement.prompt_tokens < 0:
                errors.append("prompt_tokens must be a non-negative integer")
            if measurement.completion_tokens is None or measurement.completion_tokens < 0:
                errors.append("completion_tokens must be a non-negative integer")
            if measurement.output_words is not None and measurement.output_words < 0:
                errors.append("output_words must be a non-negative integer")
            if measurement.elapsed_ms is not None and measurement.elapsed_ms < 0:
                errors.append("elapsed_ms must be a non-negative integer")
            if measurement.cost is not None and measurement.cost < Decimal("0"):
                errors.append("cost must be non-negative")
        return errors


class ResponseValidator:
    """Validate raw API responses before they become measurements."""

    @staticmethod
    def validate(response: ChatResponse) -> list[str]:
        """Return validation errors for a chat response."""
        errors: list[str] = []
        if response.prompt_tokens < 0 or response.completion_tokens < 0:
            errors.append("token counts must be non-negative")
        if response.elapsed_ms < 0:
            errors.append("elapsed_ms must be non-negative")
        return errors
