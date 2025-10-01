"""
Tests for ErrorPresenter - user-friendly error message generation.

Following TDD methodology - tests written before implementation.
"""

import pytest
import traceback
from pathlib import Path

from falconeye.infrastructure.presentation.error_presenter import ErrorPresenter
from falconeye.domain.exceptions import (
    OllamaConnectionError,
    OllamaModelNotFoundError,
    OllamaTimeoutError,
)


class TestErrorPresenter:
    """Test suite for ErrorPresenter."""

    def test_connection_error_non_verbose(self):
        """Test connection error shows user-friendly message without verbose."""
        error = OllamaConnectionError("Connection refused")

        result = ErrorPresenter.present(error, verbose=False)

        # Should contain friendly message
        assert "Could not connect to Ollama" in result
        # Should contain helpful actions
        assert "docker ps" in result or "ollama serve" in result
        # Should NOT contain stack trace
        assert "Traceback" not in result
        assert "Connection refused" not in result

    def test_connection_error_verbose(self):
        """Test connection error shows technical details with verbose."""
        error = OllamaConnectionError("Connection refused")

        result = ErrorPresenter.present(error, verbose=True)

        # Should contain friendly message
        assert "Could not connect to Ollama" in result
        # Should contain technical details
        assert "OllamaConnectionError" in result
        assert "Connection refused" in result
        # Should contain stack trace
        assert "Traceback" in result or "Error Details" in result

    def test_model_not_found_error(self):
        """Test model not found error with model name."""
        model_name = "qwen3-coder:30b"
        error = OllamaModelNotFoundError(f"Model '{model_name}' not found")

        result = ErrorPresenter.present(error, verbose=False)

        # Should mention the model name
        assert model_name in result or "not found" in result
        # Should suggest pulling the model
        assert "ollama pull" in result
        assert "ollama list" in result

    def test_timeout_error(self):
        """Test timeout error with configuration suggestion."""
        error = OllamaTimeoutError("Request timed out after 120s")

        result = ErrorPresenter.present(error, verbose=False)

        # Should explain timeout
        assert "timed out" in result.lower() or "timeout" in result.lower()
        # Should suggest increasing timeout
        assert "timeout" in result.lower()
        assert "config" in result.lower() or "increase" in result.lower()

    def test_file_not_found_error(self):
        """Test file not found error with file path."""
        file_path = "/path/to/nonexistent.py"
        error = FileNotFoundError(f"File not found: {file_path}")

        result = ErrorPresenter.present(error, verbose=False)

        # Should mention file not found
        assert "not found" in result.lower() or "does not exist" in result.lower()
        # Should show the path
        assert file_path in result
        # Should suggest checking the path
        assert "check" in result.lower() or "ensure" in result.lower()

    def test_permission_error(self):
        """Test permission denied error with actionable advice."""
        file_path = "/root/restricted.py"
        error = PermissionError(f"Permission denied: {file_path}")

        result = ErrorPresenter.present(error, verbose=False)

        # Should mention permission denied
        assert "permission" in result.lower() or "access" in result.lower()
        # Should show the path
        assert file_path in result
        # Should suggest checking permissions
        assert "permission" in result.lower() or "ls -la" in result.lower()

    def test_generic_exception_non_verbose(self):
        """Test generic exception shows friendly message without stack trace."""
        error = ValueError("Invalid configuration value")

        result = ErrorPresenter.present(error, verbose=False)

        # Should contain some error info
        assert len(result) > 0
        # Should mention error occurred
        assert "error" in result.lower() or "failed" in result.lower()
        # Should NOT contain full stack trace
        assert "Traceback" not in result

    def test_generic_exception_verbose(self):
        """Test generic exception shows full details with verbose."""
        error = ValueError("Invalid configuration value")

        result = ErrorPresenter.present(error, verbose=True)

        # Should contain error details
        assert "ValueError" in result
        assert "Invalid configuration value" in result
        # Should contain stack trace or technical details
        assert "Traceback" in result or "Error Details" in result

    def test_unicode_error(self):
        """Test unicode decode error with helpful message."""
        error = UnicodeDecodeError('utf-8', b'\xff\xfe', 0, 1, 'invalid start byte')

        result = ErrorPresenter.present(error, verbose=False)

        # Should mention encoding issue
        assert "encoding" in result.lower() or "decode" in result.lower()
        # Should be helpful
        assert len(result) > 0

    def test_keyboard_interrupt(self):
        """Test keyboard interrupt (Ctrl+C) shows clean message."""
        error = KeyboardInterrupt()

        result = ErrorPresenter.present(error, verbose=False)

        # Should mention user cancellation
        assert "cancel" in result.lower() or "interrupt" in result.lower() or "stopped" in result.lower()
        # Should be brief and clean
        assert len(result) < 200

    def test_nested_exception_verbose(self):
        """Test nested exception shows full chain with verbose."""
        try:
            try:
                raise ConnectionError("Network issue")
            except ConnectionError as e:
                raise OllamaConnectionError("Could not connect") from e
        except OllamaConnectionError as error:
            result = ErrorPresenter.present(error, verbose=True)

            # Should show both exceptions
            assert "OllamaConnectionError" in result
            assert "ConnectionError" in result or "Network issue" in result

    def test_error_without_message(self):
        """Test error with no message still produces output."""
        error = RuntimeError()

        result = ErrorPresenter.present(error, verbose=False)

        # Should still produce some message
        assert len(result) > 0
        assert "error" in result.lower() or "failed" in result.lower()

    def test_multiple_suggestions(self):
        """Test error with multiple suggestions formats them properly."""
        error = OllamaConnectionError("Service not available")

        result = ErrorPresenter.present(error, verbose=False)

        # Should have multiple suggestions
        # They should be formatted as a list (bullets or numbered)
        suggestion_count = result.count("•") + result.count("-") + result.count("1.") + result.count("2.")
        assert suggestion_count >= 2

    def test_error_message_formatting(self):
        """Test error message is well-formatted and readable."""
        error = FileNotFoundError("test.py not found")

        result = ErrorPresenter.present(error, verbose=False)

        # Should have clear structure
        assert len(result) > 0
        # Should not be too long for non-verbose
        assert len(result) < 1000
        # Should be readable (no raw Python objects)
        assert "<" not in result or "object at 0x" not in result

    def test_database_lock_error(self):
        """Test database lock error with retry suggestion."""
        error = Exception("database is locked")

        result = ErrorPresenter.present(error, verbose=False)

        # Should mention database lock
        assert "locked" in result.lower() or "database" in result.lower()
        # Should suggest waiting or closing other processes
        assert "wait" in result.lower() or "process" in result.lower() or "close" in result.lower()
