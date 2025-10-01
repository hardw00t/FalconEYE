"""Review single file command and handler."""

from dataclasses import dataclass
from pathlib import Path

from ...domain.models.security import SecurityReview
from ...domain.models.prompt import PromptContext
from ...domain.services.security_analyzer import SecurityAnalyzer
from ...domain.services.context_assembler import ContextAssembler


@dataclass
class ReviewFileCommand:
    """
    Command to review a single file.

    Uses AI to analyze the file for security vulnerabilities.
    NO pattern matching - pure AI reasoning.
    """
    file_path: Path
    language: str
    system_prompt: str
    validate_findings: bool = False
    top_k_context: int = 5


class ReviewFileHandler:
    """
    Handler for review file command.

    Orchestrates:
    1. Read file content
    2. Assemble context with RAG
    3. AI analysis
    4. Optional validation
    """

    def __init__(
        self,
        security_analyzer: SecurityAnalyzer,
        context_assembler: ContextAssembler,
    ):
        """
        Initialize handler.

        Args:
            security_analyzer: AI-powered security analyzer
            context_assembler: Context assembly for RAG
        """
        self.security_analyzer = security_analyzer
        self.context_assembler = context_assembler

    async def handle(self, command: ReviewFileCommand) -> SecurityReview:
        """
        Execute review file command.

        Args:
            command: Review command

        Returns:
            SecurityReview with AI-identified findings
        """
        print(f"Reviewing file: {command.file_path}")

        # Read file
        content = command.file_path.read_text(encoding="utf-8")

        # Create review session
        review = SecurityReview.create(
            codebase_path=str(command.file_path),
            language=command.language,
        )

        # Assemble context with RAG
        context = await self.context_assembler.assemble_context(
            file_path=str(command.file_path),
            code_snippet=content,
            language=command.language,
            top_k_similar=command.top_k_context,
            analysis_type="review",
        )

        # AI analysis
        findings = await self.security_analyzer.analyze_code(
            context=context,
            system_prompt=command.system_prompt,
        )

        # Add findings to review
        for finding in findings:
            review.add_finding(finding)

        # Optional validation
        if command.validate_findings and findings:
            print("  Validating findings with AI...")
            validated_findings = await self.security_analyzer.validate_findings(
                findings=findings,
                context=context,
            )

            # Replace with validated
            review.findings = validated_findings

        review.files_analyzed = 1
        review.complete()

        print(f"  Found {len(review.findings)} issues")

        return review