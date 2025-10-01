"""
Integration tests for CLI error handling with ErrorPresenter.

Tests the --verbose flag and error message formatting.
"""

import pytest
from typer.testing import CliRunner
from pathlib import Path

from falconeye.adapters.cli.main import app


class TestCLIErrorHandling:
    """Test suite for CLI error handling integration."""

    @pytest.fixture
    def runner(self):
        """Create CLI runner."""
        return CliRunner()

    def test_index_nonexistent_path_non_verbose(self, runner):
        """Test index with nonexistent path shows user-friendly error."""
        result = runner.invoke(app, ["index", "/nonexistent/path/to/code"])

        # Should exit with error
        assert result.exit_code != 0
        # Should contain friendly error message
        assert "not found" in result.stdout.lower() or "does not exist" in result.stdout.lower()
        # Should NOT contain stack trace
        assert "Traceback" not in result.stdout

    def test_index_nonexistent_path_verbose(self, runner):
        """Test index with nonexistent path and --verbose shows technical details."""
        # Note: Typer validates path exists before our code runs, so this tests Typer's error handling
        result = runner.invoke(app, ["index", "/nonexistent/path/to/code", "--verbose"])

        # Should exit with error
        assert result.exit_code != 0
        # Typer shows its own error message for invalid paths
        assert "does not exist" in result.stdout.lower()

    def test_review_nonexistent_file_non_verbose(self, runner):
        """Test review with nonexistent file shows error."""
        # Note: Typer validates path exists before our code runs
        result = runner.invoke(app, ["review", "/nonexistent/file.py"])

        # Should exit with error
        assert result.exit_code != 0
        # Typer shows its own error message
        assert "does not exist" in result.stdout.lower()

    def test_review_nonexistent_file_verbose(self, runner):
        """Test review with nonexistent file and --verbose."""
        # Note: Typer validates path exists before our code runs
        result = runner.invoke(app, ["review", "/nonexistent/file.py", "--verbose"])

        # Should exit with error
        assert result.exit_code != 0
        # Typer shows its own error message
        assert "does not exist" in result.stdout.lower()

    def test_help_shows_verbose_flag(self, runner):
        """Test that --verbose flag is documented in help."""
        result = runner.invoke(app, ["index", "--help"])

        assert "--verbose" in result.stdout or "-v" in result.stdout
        assert "verbose" in result.stdout.lower()

    def test_review_help_shows_verbose_flag(self, runner):
        """Test that --verbose flag is documented in review help."""
        result = runner.invoke(app, ["review", "--help"])

        assert "--verbose" in result.stdout or "-v" in result.stdout
        assert "verbose" in result.stdout.lower()
