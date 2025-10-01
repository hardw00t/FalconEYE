"""Factory for creating output formatters."""

from typing import Optional
from .base_formatter import OutputFormatter
from .console_formatter import ConsoleFormatter
from .json_formatter import JSONFormatter
from .sarif_formatter import SARIFFormatter


class FormatterFactory:
    """
    Factory for creating output formatters.

    Provides a centralized way to create formatters based on format name.
    """

    @staticmethod
    def create(
        format_name: str,
        use_color: bool = True,
        verbose: bool = False,
        pretty_json: bool = True,
    ) -> OutputFormatter:
        """
        Create formatter by name.

        Args:
            format_name: Format name ("console", "json", "sarif")
            use_color: Enable colors (console formatter)
            verbose: Enable verbose output (console formatter)
            pretty_json: Enable pretty printing (JSON formatter)

        Returns:
            OutputFormatter instance

        Raises:
            ValueError: If format_name is not recognized
        """
        format_name = format_name.lower()

        if format_name == "console":
            return ConsoleFormatter(use_color=use_color, verbose=verbose)
        elif format_name == "json":
            return JSONFormatter(pretty=pretty_json)
        elif format_name == "sarif":
            return SARIFFormatter()
        else:
            raise ValueError(
                f"Unknown format: {format_name}. "
                f"Supported formats: console, json, sarif"
            )

    @staticmethod
    def get_supported_formats() -> list[str]:
        """
        Get list of supported format names.

        Returns:
            List of format names
        """
        return ["console", "json", "sarif"]