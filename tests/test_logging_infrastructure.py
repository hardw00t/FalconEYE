"""
Tests for logging infrastructure.

Following TDD methodology - these tests are written BEFORE implementation.
Tests use real file I/O and logging, not mocks.
"""

import json
import logging
from pathlib import Path
from datetime import datetime
import pytest
from io import StringIO
import sys

from falconeye.infrastructure.logging import FalconEyeLogger, get_logger


class TestFalconEyeLogger:
    """Test suite for FalconEyeLogger - Core logging functionality."""

    def test_singleton_pattern(self, tmp_path):
        """Test that FalconEyeLogger is a singleton."""
        log_file = tmp_path / "test.log"

        logger1 = FalconEyeLogger.get_instance(log_file=log_file)
        logger2 = FalconEyeLogger.get_instance(log_file=log_file)

        assert logger1 is logger2, "Should return same instance"

    def test_dual_output_console_and_file(self, tmp_path, capsys):
        """Test logger writes to both console (stderr) and file."""
        log_file = tmp_path / "test.log"

        # Reset singleton for clean test
        FalconEyeLogger._instance = None

        logger = FalconEyeLogger.get_instance(
            level="INFO",
            log_file=log_file,
            console=True
        )

        test_message = "Test log message"
        logger.info(test_message)

        # Verify console output (stderr)
        captured = capsys.readouterr()
        assert test_message in captured.err, "Message should appear in console output"

        # Verify file output exists
        assert log_file.exists(), "Log file should be created"

    def test_json_format_in_file(self, tmp_path):
        """Test that file logs use JSON format."""
        log_file = tmp_path / "test.log"

        # Reset singleton
        FalconEyeLogger._instance = None

        logger = FalconEyeLogger.get_instance(
            level="INFO",
            log_file=log_file,
            console=False  # Disable console for cleaner test
        )

        test_message = "JSON test message"
        logger.info(test_message)

        # Read and parse JSON log file
        with open(log_file) as f:
            log_content = f.read().strip()
            log_data = json.loads(log_content)

        assert log_data["message"] == test_message
        assert log_data["level"] == "INFO"
        assert "timestamp" in log_data
        assert "logger" in log_data

    def test_human_readable_console_format(self, tmp_path, capsys):
        """Test that console uses human-readable format."""
        log_file = tmp_path / "test.log"

        # Reset singleton
        FalconEyeLogger._instance = None

        logger = FalconEyeLogger.get_instance(
            level="INFO",
            log_file=log_file,
            console=True
        )

        test_message = "Human readable test"
        logger.info(test_message)

        captured = capsys.readouterr()

        # Should contain timestamp, level, and message (not JSON)
        assert test_message in captured.err
        assert "INFO" in captured.err
        assert "{" not in captured.err, "Console should not be JSON format"

    def test_log_levels(self, tmp_path):
        """Test different log levels work correctly."""
        log_file = tmp_path / "test.log"

        # Reset singleton
        FalconEyeLogger._instance = None

        logger = FalconEyeLogger.get_instance(
            level="DEBUG",
            log_file=log_file,
            console=False
        )

        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")
        logger.critical("Critical message")

        # Read all log lines
        with open(log_file) as f:
            lines = f.readlines()

        assert len(lines) == 5, "Should have 5 log entries"

        # Verify each level
        levels_found = []
        for line in lines:
            log_data = json.loads(line.strip())
            levels_found.append(log_data["level"])

        assert "DEBUG" in levels_found
        assert "INFO" in levels_found
        assert "WARNING" in levels_found
        assert "ERROR" in levels_found
        assert "CRITICAL" in levels_found

    def test_log_level_filtering(self, tmp_path):
        """Test that log level filtering works (e.g., INFO doesn't log DEBUG)."""
        log_file = tmp_path / "test.log"

        # Reset singleton
        FalconEyeLogger._instance = None

        logger = FalconEyeLogger.get_instance(
            level="INFO",  # Set to INFO
            log_file=log_file,
            console=False
        )

        logger.debug("Debug message - should not appear")
        logger.info("Info message - should appear")
        logger.warning("Warning message - should appear")

        with open(log_file) as f:
            lines = f.readlines()

        assert len(lines) == 2, "Should only log INFO and WARNING (not DEBUG)"

    def test_daily_rotation_configuration(self, tmp_path):
        """Test that daily rotation is configured correctly."""
        log_file = tmp_path / "test.log"

        # Reset singleton
        FalconEyeLogger._instance = None

        logger = FalconEyeLogger.get_instance(
            level="INFO",
            log_file=log_file,
            console=False,
            rotation="daily",
            retention_days=30
        )

        # Verify logger has TimedRotatingFileHandler
        file_handlers = [
            h for h in logger.logger.handlers
            if isinstance(h, logging.handlers.TimedRotatingFileHandler)
        ]

        assert len(file_handlers) == 1, "Should have one TimedRotatingFileHandler"
        handler = file_handlers[0]
        assert handler.when == 'MIDNIGHT', "Should rotate at midnight"
        assert handler.backupCount == 30, "Should keep 30 days of logs"

    def test_extra_fields_in_logs(self, tmp_path):
        """Test that extra fields can be added to log records."""
        log_file = tmp_path / "test.log"

        # Reset singleton
        FalconEyeLogger._instance = None

        logger = FalconEyeLogger.get_instance(
            level="INFO",
            log_file=log_file,
            console=False
        )

        logger.info(
            "Message with extras",
            extra={
                "command_id": "test-cmd-123",
                "project_id": "test-proj-456",
                "metrics": {"duration": 1.23}
            }
        )

        with open(log_file) as f:
            log_data = json.loads(f.read().strip())

        assert log_data["command_id"] == "test-cmd-123"
        assert log_data["project_id"] == "test-proj-456"
        assert log_data["metrics"]["duration"] == 1.23

    def test_get_logger_helper(self, tmp_path):
        """Test get_logger() helper function."""
        log_file = tmp_path / "test.log"

        # Reset singleton
        FalconEyeLogger._instance = None

        # Initialize via get_instance first
        FalconEyeLogger.get_instance(log_file=log_file)

        # Then use get_logger helper
        logger = get_logger(__name__)

        assert logger is not None
        assert hasattr(logger, 'info')
        assert hasattr(logger, 'error')


class TestLoggingConfiguration:
    """Test logging configuration from config.yaml."""

    def test_logging_config_structure(self):
        """Test that logging config can be loaded from config."""
        # This will be implemented when we integrate with ConfigLoader
        # For now, just verify the config structure is defined
        from falconeye.infrastructure.config.config_models import LoggingConfig

        config = LoggingConfig(
            level="DEBUG",
            file="./falconeye.log",
            console=True
        )

        assert config.level == "DEBUG"
        assert config.file == "./falconeye.log"
        assert config.console is True


class TestLoggingIntegration:
    """Integration tests for logging in real scenarios."""

    def test_logging_in_command_execution(self, tmp_path):
        """Test logging during a simulated command execution."""
        log_file = tmp_path / "integration.log"

        # Reset singleton
        FalconEyeLogger._instance = None

        logger = FalconEyeLogger.get_instance(
            level="INFO",
            log_file=log_file,
            console=False
        )

        # Simulate command execution with logging
        command_id = "cmd-integration-test"

        logger.info(
            "Command started",
            extra={"command_id": command_id, "command": "index"}
        )

        logger.info(
            "Processing files",
            extra={"command_id": command_id, "files_count": 10}
        )

        logger.info(
            "Command completed",
            extra={
                "command_id": command_id,
                "metrics": {
                    "duration_seconds": 5.2,
                    "files_processed": 10
                }
            }
        )

        # Verify all logs
        with open(log_file) as f:
            lines = f.readlines()

        assert len(lines) == 3

        # Verify command_id is in all logs
        for line in lines:
            log_data = json.loads(line.strip())
            assert log_data["command_id"] == command_id

    def test_exception_logging(self, tmp_path):
        """Test that exceptions are logged with stack traces."""
        log_file = tmp_path / "exception.log"

        # Reset singleton
        FalconEyeLogger._instance = None

        logger = FalconEyeLogger.get_instance(
            level="ERROR",
            log_file=log_file,
            console=False
        )

        try:
            # Deliberately cause an exception
            raise ValueError("Test exception for logging")
        except ValueError as e:
            logger.error(
                "Exception occurred",
                exc_info=True,
                extra={"error_type": type(e).__name__}
            )

        with open(log_file) as f:
            log_content = f.read()

        assert "Test exception for logging" in log_content
        assert "ValueError" in log_content
        # Stack trace should be included
        assert "Traceback" in log_content or "traceback" in log_content
