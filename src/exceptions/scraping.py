"""Scraping-specific exception classes."""

from __future__ import annotations

from src.exceptions.base import WatchtowerError


class ScrapingError(WatchtowerError):
    """Base exception for scraping-related errors."""

    def __init__(
        self,
        message: str,
        url: str | None = None,
        **kwargs,
    ):
        """Initialize scraping error.

        Args:
            message: Error message.
            url: URL being scraped when error occurred.
            **kwargs: Additional arguments for base class.
        """
        context = kwargs.get("context", {})
        if url:
            context["url"] = url

        kwargs["context"] = context
        kwargs["error_code"] = kwargs.get("error_code", "WT_SCRAPING_ERROR")

        super().__init__(message, **kwargs)


class RequestError(ScrapingError):
    """Exception raised for HTTP request errors."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response_text: str | None = None,
        **kwargs,
    ):
        """Initialize request error.

        Args:
            message: Error message.
            status_code: HTTP status code.
            response_text: Response text (truncated).
            **kwargs: Additional arguments for base class.
        """
        context = kwargs.get("context", {})
        if status_code:
            context["status_code"] = status_code
        if response_text:
            context["response_text"] = response_text[:500]  # Limit size

        kwargs["context"] = context
        kwargs["error_code"] = kwargs.get("error_code", "WT_REQUEST_ERROR")

        super().__init__(message, **kwargs)


class ParsingError(ScrapingError):
    """Exception raised for content parsing errors."""

    def __init__(
        self,
        message: str,
        parser_type: str | None = None,
        content_sample: str | None = None,
        **kwargs,
    ):
        """Initialize parsing error.

        Args:
            message: Error message.
            parser_type: Type of parser used (html, xml, json, etc.).
            content_sample: Sample of content that failed to parse.
            **kwargs: Additional arguments for base class.
        """
        context = kwargs.get("context", {})
        if parser_type:
            context["parser_type"] = parser_type
        if content_sample:
            context["content_sample"] = content_sample[:300]  # Limit size

        kwargs["context"] = context
        kwargs["error_code"] = kwargs.get("error_code", "WT_PARSING_ERROR")

        super().__init__(message, **kwargs)


class RateLimitError(ScrapingError):
    """Exception raised when rate limits are exceeded."""

    def __init__(
        self,
        message: str,
        retry_after: int | None = None,
        **kwargs,
    ):
        """Initialize rate limit error.

        Args:
            message: Error message.
            retry_after: Seconds to wait before retrying.
            **kwargs: Additional arguments for base class.
        """
        context = kwargs.get("context", {})
        if retry_after:
            context["retry_after"] = retry_after

        kwargs["context"] = context
        kwargs["error_code"] = kwargs.get("error_code", "WT_RATE_LIMIT_ERROR")
        kwargs["user_message"] = (
            f"Rate limit exceeded. Please try again in {retry_after or 'a few'} seconds."
        )

        super().__init__(message, **kwargs)


class TimeoutError(ScrapingError):
    """Exception raised for request timeouts."""

    def __init__(
        self,
        message: str,
        timeout_seconds: int | None = None,
        **kwargs,
    ):
        """Initialize timeout error.

        Args:
            message: Error message.
            timeout_seconds: Timeout value in seconds.
            **kwargs: Additional arguments for base class.
        """
        context = kwargs.get("context", {})
        if timeout_seconds:
            context["timeout_seconds"] = timeout_seconds

        kwargs["context"] = context
        kwargs["error_code"] = kwargs.get("error_code", "WT_TIMEOUT_ERROR")
        kwargs["user_message"] = (
            "Request timed out. Please check your connection and try again."
        )

        super().__init__(message, **kwargs)
