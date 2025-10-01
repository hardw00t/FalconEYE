"""Security analyzer domain service."""

from typing import List
import json
from ..models.security import SecurityFinding, SecurityReview, Severity, FindingConfidence
from ..models.prompt import PromptContext
from .llm_service import LLMService
from ..exceptions import AnalysisError, InvalidSecurityFindingError


class SecurityAnalyzer:
    """
    Domain service for security analysis.

    This service orchestrates AI-powered security analysis.
    CRITICAL: ALL analysis is done by AI, NO pattern matching.
    """

    def __init__(self, llm_service: LLMService):
        """
        Initialize security analyzer.

        Args:
            llm_service: LLM service for AI analysis
        """
        self.llm_service = llm_service

    async def analyze_code(
        self,
        context: PromptContext,
        system_prompt: str,
    ) -> List[SecurityFinding]:
        """
        Analyze code for security vulnerabilities using AI.

        This method sends code to the LLM and parses security findings.
        NO pattern matching - pure AI reasoning.

        Args:
            context: Code context with metadata
            system_prompt: Instructions for the AI

        Returns:
            List of security findings identified by AI

        Raises:
            AnalysisError: If AI analysis fails
        """
        try:
            # Get AI analysis
            raw_response = await self.llm_service.analyze_code_security(
                context=context,
                system_prompt=system_prompt,
            )

            # Parse AI response into findings
            findings = self._parse_findings(raw_response, context.file_path)
            return findings

        except Exception as e:
            raise AnalysisError(f"AI analysis failed: {str(e)}") from e

    async def validate_findings(
        self,
        findings: List[SecurityFinding],
        context: PromptContext,
    ) -> List[SecurityFinding]:
        """
        Use AI to validate findings and filter false positives.

        The AI re-evaluates each finding to ensure it's a genuine issue.
        NO pattern-based filtering - AI makes all decisions.

        Args:
            findings: Initial findings to validate
            context: Original code context

        Returns:
            Validated findings (false positives removed by AI)
        """
        if not findings:
            return []

        # Prepare findings for AI validation
        findings_json = json.dumps([
            {
                "issue": f.issue,
                "reasoning": f.reasoning,
                "code_snippet": f.code_snippet,
                "severity": f.severity.value,
            }
            for f in findings
        ])

        # Ask AI to validate
        validated_response = await self.llm_service.validate_findings(
            code_snippet=context.code_snippet,
            findings=findings_json,
            context=context.format_for_ai(),
        )

        # Parse validated findings
        validated = self._parse_findings(validated_response, context.file_path)
        return validated

    def _parse_findings(
        self,
        ai_response: str,
        file_path: str,
    ) -> List[SecurityFinding]:
        """
        Parse AI response into SecurityFinding objects.

        The AI returns findings in JSON format. This method just parses them.
        NO analysis or pattern matching happens here.

        Args:
            ai_response: Raw AI response (JSON)
            file_path: File being analyzed

        Returns:
            List of SecurityFinding objects

        Raises:
            InvalidSecurityFindingError: If AI response is malformed
        """
        try:
            # Try to extract JSON from response
            data = self._extract_json(ai_response)

            if not data:
                # AI found no issues
                return []

            # Handle different response formats
            reviews = data.get("reviews", [])
            if not reviews:
                # Check if data itself is a list
                if isinstance(data, list):
                    reviews = data

            findings = []
            for review in reviews:
                try:
                    finding = SecurityFinding.create(
                        issue=review.get("issue", "Unknown issue"),
                        reasoning=review.get("reasoning", ""),
                        mitigation=review.get("mitigation", ""),
                        severity=self._parse_severity(review.get("severity", "medium")),
                        confidence=self._parse_confidence(review.get("confidence", 0.7)),
                        file_path=file_path,
                        code_snippet=review.get("code_snippet", ""),
                        line_start=review.get("line_start"),
                        line_end=review.get("line_end"),
                        cwe_id=review.get("cwe_id"),
                        tags=review.get("tags", []),
                    )
                    findings.append(finding)
                except Exception as e:
                    # Log but don't fail on single malformed finding
                    print(f"Warning: Skipping malformed finding: {e}")
                    continue

            return findings

        except json.JSONDecodeError as e:
            raise InvalidSecurityFindingError(
                f"AI response is not valid JSON: {str(e)}"
            ) from e
        except Exception as e:
            raise InvalidSecurityFindingError(
                f"Failed to parse AI findings: {str(e)}"
            ) from e

    def _extract_json(self, text: str) -> dict:
        """
        Extract JSON from AI response.

        AI might wrap JSON in markdown code blocks or include explanatory text.
        """
        # Try to find JSON in markdown code block
        if "```json" in text:
            start = text.find("```json") + 7
            end = text.find("```", start)
            json_text = text[start:end].strip()
            return json.loads(json_text)

        # Try to find JSON in plain code block
        if "```" in text:
            start = text.find("```") + 3
            end = text.find("```", start)
            json_text = text[start:end].strip()
            return json.loads(json_text)

        # Try parsing the whole response
        return json.loads(text)

    def _parse_severity(self, severity: str) -> Severity:
        """Parse severity string to Severity enum."""
        severity_map = {
            "critical": Severity.CRITICAL,
            "high": Severity.HIGH,
            "medium": Severity.MEDIUM,
            "low": Severity.LOW,
            "info": Severity.INFO,
        }
        return severity_map.get(severity.lower(), Severity.MEDIUM)

    def _parse_confidence(self, confidence: float) -> FindingConfidence:
        """Parse confidence float to FindingConfidence enum."""
        if confidence >= 0.8:
            return FindingConfidence.HIGH
        elif confidence >= 0.5:
            return FindingConfidence.MEDIUM
        else:
            return FindingConfidence.LOW