"""
Tests for logging context management.

Following TDD methodology - these tests are written BEFORE implementation.
Tests cover thread-local storage, context managers, and correlation ID propagation.
"""

import threading
import time
from pathlib import Path
import json
import pytest

from falconeye.infrastructure.logging import FalconEyeLogger
from falconeye.infrastructure.logging.context import LogContext, logging_context


class TestLogContext:
    """Test suite for LogContext - Thread-local context management."""

    def test_get_context_empty_by_default(self):
        """Test that context is empty by default."""
        LogContext.clear()
        context = LogContext.get_context()
        assert context == {}, "Context should be empty by default"

    def test_set_and_get_single_field(self):
        """Test setting and getting a single context field."""
        LogContext.clear()
        LogContext.set("command_id", "cmd-123")

        context = LogContext.get_context()
        assert context["command_id"] == "cmd-123"

    def test_set_and_get_multiple_fields(self):
        """Test setting and getting multiple context fields."""
        LogContext.clear()
        LogContext.set("command_id", "cmd-456")
        LogContext.set("project_id", "proj-789")
        LogContext.set("user_id", "user-abc")

        context = LogContext.get_context()
        assert context["command_id"] == "cmd-456"
        assert context["project_id"] == "proj-789"
        assert context["user_id"] == "user-abc"

    def test_clear_context(self):
        """Test that clear() removes all context fields."""
        LogContext.clear()
        LogContext.set("command_id", "cmd-999")
        LogContext.set("project_id", "proj-999")

        LogContext.clear()
        context = LogContext.get_context()
        assert context == {}, "Context should be empty after clear()"

    def test_thread_isolation(self):
        """Test that context is isolated between threads."""
        LogContext.clear()

        # Set context in main thread
        LogContext.set("command_id", "main-thread")

        # Storage for thread results
        thread_results = {}

        def thread_function(thread_id):
            """Function to run in separate thread."""
            # Each thread sets its own context
            LogContext.set("command_id", f"thread-{thread_id}")
            time.sleep(0.01)  # Small delay to ensure concurrency

            # Get context in this thread
            context = LogContext.get_context()
            thread_results[thread_id] = context.get("command_id")

        # Start multiple threads
        threads = []
        for i in range(3):
            t = threading.Thread(target=thread_function, args=(i,))
            threads.append(t)
            t.start()

        # Wait for all threads
        for t in threads:
            t.join()

        # Verify each thread had its own context
        assert thread_results[0] == "thread-0"
        assert thread_results[1] == "thread-1"
        assert thread_results[2] == "thread-2"

        # Main thread context should be unchanged
        main_context = LogContext.get_context()
        assert main_context["command_id"] == "main-thread"

    def test_update_multiple_fields_at_once(self):
        """Test update() method to set multiple fields at once."""
        LogContext.clear()

        LogContext.update({
            "command_id": "cmd-bulk",
            "project_id": "proj-bulk",
            "metrics": {"count": 42}
        })

        context = LogContext.get_context()
        assert context["command_id"] == "cmd-bulk"
        assert context["project_id"] == "proj-bulk"
        assert context["metrics"]["count"] == 42

    def test_get_specific_field(self):
        """Test get() method to retrieve a specific field."""
        LogContext.clear()
        LogContext.set("command_id", "cmd-specific")

        value = LogContext.get("command_id")
        assert value == "cmd-specific"

        # Non-existent field should return None
        value = LogContext.get("non_existent")
        assert value is None

        # Non-existent field with default
        value = LogContext.get("non_existent", "default_value")
        assert value == "default_value"


class TestLoggingContextManager:
    """Test suite for logging_context() context manager."""

    def test_context_manager_sets_and_clears_context(self):
        """Test that context manager sets context and clears on exit."""
        LogContext.clear()

        with logging_context(command_id="cmd-ctx-1", project_id="proj-ctx-1"):
            context = LogContext.get_context()
            assert context["command_id"] == "cmd-ctx-1"
            assert context["project_id"] == "proj-ctx-1"

        # Context should be cleared after exit
        context = LogContext.get_context()
        assert "command_id" not in context
        assert "project_id" not in context

    def test_context_manager_nested_contexts(self):
        """Test nested context managers."""
        LogContext.clear()

        with logging_context(command_id="outer-cmd"):
            # Outer context
            context = LogContext.get_context()
            assert context["command_id"] == "outer-cmd"

            with logging_context(project_id="inner-proj"):
                # Inner context adds to outer
                context = LogContext.get_context()
                assert context["command_id"] == "outer-cmd"
                assert context["project_id"] == "inner-proj"

            # After inner context exits, only outer remains
            context = LogContext.get_context()
            assert context["command_id"] == "outer-cmd"
            assert "project_id" not in context

        # After outer context exits, all cleared
        context = LogContext.get_context()
        assert context == {}

    def test_context_manager_exception_handling(self):
        """Test that context is cleared even if exception occurs."""
        LogContext.clear()

        try:
            with logging_context(command_id="cmd-exception"):
                context = LogContext.get_context()
                assert context["command_id"] == "cmd-exception"
                raise ValueError("Test exception")
        except ValueError:
            pass

        # Context should still be cleared after exception
        context = LogContext.get_context()
        assert "command_id" not in context

    def test_context_manager_preserves_existing_context(self):
        """Test that context manager preserves fields set before it."""
        LogContext.clear()

        # Set a field before context manager
        LogContext.set("existing_field", "existing_value")

        with logging_context(command_id="cmd-new"):
            context = LogContext.get_context()
            assert context["existing_field"] == "existing_value"
            assert context["command_id"] == "cmd-new"

        # After exit, only the context manager's fields should be removed
        context = LogContext.get_context()
        assert context["existing_field"] == "existing_value"
        assert "command_id" not in context


class TestLoggingIntegrationWithContext:
    """Integration tests for logging with context."""

    def test_logging_with_automatic_context_propagation(self, tmp_path):
        """Test that log messages automatically include context fields."""
        log_file = tmp_path / "context_integration.log"

        # Reset singleton
        FalconEyeLogger._instance = None

        logger = FalconEyeLogger.get_instance(
            level="INFO",
            log_file=log_file,
            console=False
        )

        LogContext.clear()

        with logging_context(command_id="cmd-auto-123", project_id="proj-auto-456"):
            # Log without explicitly passing extra fields
            logger.info("Processing started")
            logger.info("Processing file", extra={"file_path": "/test/file.py"})

        # Read log file
        with open(log_file) as f:
            lines = f.readlines()

        assert len(lines) == 2

        # Verify both logs have context fields
        for line in lines:
            log_data = json.loads(line.strip())
            assert log_data["command_id"] == "cmd-auto-123"
            assert log_data["project_id"] == "proj-auto-456"

        # Second log should also have extra field
        second_log = json.loads(lines[1].strip())
        assert second_log["file_path"] == "/test/file.py"

    def test_logging_without_context_still_works(self, tmp_path):
        """Test that logging works normally without context."""
        log_file = tmp_path / "no_context.log"

        # Reset singleton
        FalconEyeLogger._instance = None

        logger = FalconEyeLogger.get_instance(
            level="INFO",
            log_file=log_file,
            console=False
        )

        LogContext.clear()

        # Log without context
        logger.info("Message without context")

        with open(log_file) as f:
            log_data = json.loads(f.read().strip())

        assert log_data["message"] == "Message without context"
        # Should not have command_id or project_id
        assert "command_id" not in log_data
        assert "project_id" not in log_data

    def test_context_overrides_with_explicit_extra(self, tmp_path):
        """Test that explicit extra fields override context."""
        log_file = tmp_path / "context_override.log"

        # Reset singleton
        FalconEyeLogger._instance = None

        logger = FalconEyeLogger.get_instance(
            level="INFO",
            log_file=log_file,
            console=False
        )

        LogContext.clear()

        with logging_context(command_id="ctx-cmd"):
            # Explicitly override command_id
            logger.info(
                "Override test",
                extra={"command_id": "explicit-cmd"}
            )

        with open(log_file) as f:
            log_data = json.loads(f.read().strip())

        # Explicit extra should take precedence
        assert log_data["command_id"] == "explicit-cmd"

    def test_context_across_multiple_function_calls(self, tmp_path):
        """Test that context propagates across function call stack."""
        log_file = tmp_path / "context_stack.log"

        # Reset singleton
        FalconEyeLogger._instance = None

        logger = FalconEyeLogger.get_instance(
            level="INFO",
            log_file=log_file,
            console=False
        )

        LogContext.clear()

        def inner_function():
            """Inner function that logs."""
            logger.info("Inner function log")

        def middle_function():
            """Middle function that calls inner."""
            logger.info("Middle function log")
            inner_function()

        def outer_function():
            """Outer function that sets context."""
            with logging_context(command_id="cmd-stack", operation="stack_test"):
                logger.info("Outer function log")
                middle_function()

        outer_function()

        # Read all logs
        with open(log_file) as f:
            lines = f.readlines()

        assert len(lines) == 3

        # All logs should have context
        for line in lines:
            log_data = json.loads(line.strip())
            assert log_data["command_id"] == "cmd-stack"
            assert log_data["operation"] == "stack_test"
