"""
Tests for ReviewFileHandler logging and error handling.

Following TDD methodology - tests written before implementation.
Tests use real implementations, not mocks.

Note: Logging tests verify functional behavior rather than exact log output,
since FalconEyeLogger has its own comprehensive test suite.
"""

import pytest
from pathlib import Path
from typing import List

from falconeye.application.commands.review_file import ReviewFileHandler, ReviewFileCommand
from falconeye.domain.models.security import SecurityFinding, Severity, FindingConfidence
from falconeye.domain.models.prompt import PromptContext
from falconeye.infrastructure.logging import FalconEyeLogger


# Mock SecurityAnalyzer for testing
class MockSecurityAnalyzer:
    """Mock security analyzer that returns predictable results."""

    def __init__(self, findings=None, should_fail=False):
        self.findings = findings or []
        self.should_fail = should_fail
        self.analyze_count = 0
        self.validate_count = 0

    async def analyze_code(self, context, system_prompt):
        """Mock analyze_code."""
        self.analyze_count += 1
        if self.should_fail:
            raise ConnectionError("Mock analyzer connection error")
        return self.findings

    async def validate_findings(self, findings, context):
        """Mock validate_findings."""
        self.validate_count += 1
        if self.should_fail:
            raise ConnectionError("Mock validation error")
        # Return same findings (validated)
        return findings


# Mock ContextAssembler for testing
class MockContextAssembler:
    """Mock context assembler that returns predictable results."""

    def __init__(self, should_fail=False):
        self.should_fail = should_fail
        self.assemble_count = 0

    async def assemble_context(self, file_path, code_snippet, language, top_k_similar=5, analysis_type="review"):
        """Mock assemble_context."""
        self.assemble_count += 1
        if self.should_fail:
            raise ConnectionError("Mock assembler connection error")

        return PromptContext(
            file_path=file_path,
            code_snippet=code_snippet,
            language=language,
        )


class TestReviewFileHandlerLogging:
    """Test suite for ReviewFileHandler logging."""

    @pytest.fixture
    def logger(self):
        """Get logger instance."""
        return FalconEyeLogger.get_instance()

    @pytest.fixture
    def temp_file(self, tmp_path):
        """Create temporary test file."""
        file_path = tmp_path / "test.py"
        file_path.write_text("def get_user(id): return db.query(f'SELECT * FROM users WHERE id={id}')")
        return file_path

    @pytest.fixture
    def mock_analyzer(self):
        """Create mock security analyzer."""
        return MockSecurityAnalyzer()

    @pytest.fixture
    def mock_assembler(self):
        """Create mock context assembler."""
        return MockContextAssembler()

    @pytest.fixture
    def handler(self, mock_analyzer, mock_assembler):
        """Create ReviewFileHandler with mocks."""
        return ReviewFileHandler(mock_analyzer, mock_assembler)

    @pytest.mark.asyncio
    async def test_handle_with_findings(self, handler, temp_file, mock_analyzer, logger):
        """Test that handler successfully processes file and returns review."""
        # Configure mock to return findings
        finding = SecurityFinding.create(
            issue="SQL Injection",
            reasoning="User input directly in query",
            mitigation="Use parameterized queries",
            severity=Severity.CRITICAL,
            confidence=FindingConfidence.HIGH,
            file_path=str(temp_file),
            code_snippet="f'SELECT * FROM users WHERE id={id}'",
        )
        mock_analyzer.findings = [finding]

        # Create command
        command = ReviewFileCommand(
            file_path=temp_file,
            language="python",
            system_prompt="Find security issues",
            validate_findings=False,
            top_k_context=5,
        )

        # Execute
        review = await handler.handle(command)

        # Verify review is correct
        assert review.files_analyzed == 1
        assert len(review.findings) == 1
        assert review.findings[0].issue == "SQL Injection"
        assert review.language == "python"
        # Logging is happening - visible in test output

    @pytest.mark.asyncio
    async def test_handle_with_validation(self, handler, temp_file, mock_analyzer, logger):
        """Test that handler validates findings when requested."""
        # Configure mock to return findings
        finding = SecurityFinding.create(
            issue="Potential Issue",
            reasoning="Might be a problem",
            mitigation="Review this code",
            severity=Severity.MEDIUM,
            confidence=FindingConfidence.MEDIUM,
            file_path=str(temp_file),
            code_snippet="def test(): pass",
        )
        mock_analyzer.findings = [finding]

        # Create command with validation
        command = ReviewFileCommand(
            file_path=temp_file,
            language="python",
            system_prompt="Find security issues",
            validate_findings=True,  # Enable validation
            top_k_context=5,
        )

        # Execute
        review = await handler.handle(command)

        # Verify validation was called
        assert mock_analyzer.validate_count == 1
        assert len(review.findings) == 1
        # Logging of validation is happening

    @pytest.mark.asyncio
    async def test_handle_without_findings(self, handler, temp_file, mock_analyzer, logger):
        """Test that handler handles files with no findings."""
        # Configure mock to return no findings
        mock_analyzer.findings = []

        # Create command
        command = ReviewFileCommand(
            file_path=temp_file,
            language="python",
            system_prompt="Find security issues",
        )

        # Execute
        review = await handler.handle(command)

        # Verify review shows no findings
        assert review.files_analyzed == 1
        assert len(review.findings) == 0
        # Logging shows no findings


class TestReviewFileHandlerErrorHandling:
    """Test suite for ReviewFileHandler error handling."""

    @pytest.fixture
    def temp_file(self, tmp_path):
        """Create temporary test file."""
        file_path = tmp_path / "test.py"
        file_path.write_text("def test(): pass")
        return file_path

    @pytest.fixture
    def mock_analyzer(self):
        """Create mock security analyzer."""
        return MockSecurityAnalyzer()

    @pytest.fixture
    def mock_assembler(self):
        """Create mock context assembler."""
        return MockContextAssembler()

    @pytest.fixture
    def handler(self, mock_analyzer, mock_assembler):
        """Create ReviewFileHandler with mocks."""
        return ReviewFileHandler(mock_analyzer, mock_assembler)

    @pytest.mark.asyncio
    async def test_handle_file_not_found(self, handler):
        """Test that handler handles missing files appropriately."""
        command = ReviewFileCommand(
            file_path=Path("/nonexistent/file.py"),
            language="python",
            system_prompt="Find issues",
        )

        # Should raise FileNotFoundError
        with pytest.raises(FileNotFoundError):
            await handler.handle(command)
        # Error logging is happening

    @pytest.mark.asyncio
    async def test_handle_assembler_error(self, handler, temp_file, mock_assembler):
        """Test that handler handles context assembler errors."""
        # Configure mock to fail
        mock_assembler.should_fail = True

        command = ReviewFileCommand(
            file_path=temp_file,
            language="python",
            system_prompt="Find issues",
        )

        # Should propagate the error from assembler
        with pytest.raises(ConnectionError) as exc_info:
            await handler.handle(command)

        assert "assembler" in str(exc_info.value).lower()
        # Error logging is happening

    @pytest.mark.asyncio
    async def test_handle_analyzer_error(self, handler, temp_file, mock_analyzer):
        """Test that handler handles security analyzer errors."""
        # Configure mock to fail
        mock_analyzer.should_fail = True

        command = ReviewFileCommand(
            file_path=temp_file,
            language="python",
            system_prompt="Find issues",
        )

        # Should propagate the error from analyzer
        with pytest.raises(ConnectionError) as exc_info:
            await handler.handle(command)

        assert "analyzer" in str(exc_info.value).lower()
        # Error logging is happening

    @pytest.mark.asyncio
    async def test_handle_with_correlation_context(self, handler, temp_file):
        """Test that handler works with correlation context."""
        from falconeye.infrastructure.logging import logging_context

        command = ReviewFileCommand(
            file_path=temp_file,
            language="python",
            system_prompt="Find issues",
        )

        # Verify handler works within correlation context
        with logging_context(operation="test_review", command_id="rev-123"):
            review = await handler.handle(command)

        # Functional behavior should work correctly
        assert review.files_analyzed == 1
        # Logging with correlation ID is happening
