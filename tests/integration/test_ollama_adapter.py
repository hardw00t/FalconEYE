"""Integration tests for Ollama LLM adapter with real Ollama."""

import pytest
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from falconeye.infrastructure.llm_providers.ollama_adapter import OllamaLLMAdapter
from falconeye.domain.models.prompt import PromptContext


@pytest.mark.integration
class TestOllamaAdapter:
    """Test Ollama adapter with real Ollama instance."""

    @pytest.fixture
    async def adapter(self):
        """Create Ollama adapter."""
        return OllamaLLMAdapter(
            host="http://localhost:11434",
            chat_model="qwen3-coder:30b",
            embedding_model="embeddinggemma:300m",
        )

    @pytest.mark.asyncio
    async def test_health_check(self, adapter):
        """Test Ollama connectivity."""
        is_healthy = await adapter.health_check()
        assert is_healthy, "Ollama service should be available"

    @pytest.mark.asyncio
    async def test_generate_embedding(self, adapter):
        """Test embedding generation."""
        text = "def vulnerable_function(user_input): exec(user_input)"
        embedding = await adapter.generate_embedding(text)

        assert embedding is not None
        assert isinstance(embedding, list)
        assert len(embedding) > 0
        assert all(isinstance(x, float) for x in embedding)

    @pytest.mark.asyncio
    async def test_analyze_simple_vulnerability(self, adapter):
        """
        Test AI-powered security analysis with a clear vulnerability.

        This tests the CORE functionality - AI finding vulnerabilities
        with NO pattern matching.
        """
        # Code with obvious security issue
        vulnerable_code = '''def execute_command(user_input):
    import os
    os.system(user_input)  # Command injection vulnerability
'''

        context = PromptContext(
            file_path="test.py",
            code_snippet=vulnerable_code,
            language="python",
            analysis_type="review",
        )

        system_prompt = """You are a security expert analyzing Python code.
Identify security vulnerabilities and return findings in JSON format:
{
  "reviews": [
    {
      "issue": "Brief description",
      "reasoning": "Why this is a security issue",
      "mitigation": "How to fix it",
      "severity": "critical|high|medium|low",
      "confidence": 0.9,
      "code_snippet": "Vulnerable code"
    }
  ]
}

If no issues found, return: {"reviews": []}
Analyze for command injection, SQL injection, XSS, and other OWASP Top 10 issues."""

        response = await adapter.analyze_code_security(context, system_prompt)

        # Verify we got a response
        assert response is not None
        assert len(response) > 0

        # Response should mention command injection or related terms
        response_lower = response.lower()
        assert any(term in response_lower for term in [
            "command", "injection", "os.system", "vulnerability", "exec"
        ]), "AI should identify the command injection vulnerability"

        print(f"\nAI Response:\n{response}")

    @pytest.mark.asyncio
    async def test_analyze_safe_code(self, adapter):
        """Test AI analysis on safe code (should find no issues)."""
        safe_code = '''def add_numbers(a: int, b: int) -> int:
    """Safely add two numbers."""
    return a + b
'''

        context = PromptContext(
            file_path="test.py",
            code_snippet=safe_code,
            language="python",
            analysis_type="review",
        )

        system_prompt = """You are a security expert analyzing Python code.
Identify security vulnerabilities and return findings in JSON format.
If no issues found, return: {"reviews": []}"""

        response = await adapter.analyze_code_security(context, system_prompt)

        assert response is not None
        print(f"\nAI Response for safe code:\n{response}")

    @pytest.mark.asyncio
    async def test_batch_embeddings(self, adapter):
        """Test batch embedding generation."""
        texts = [
            "def function1(): pass",
            "def function2(): pass",
            "def function3(): pass",
        ]

        embeddings = await adapter.generate_embeddings_batch(texts)

        assert len(embeddings) == 3
        assert all(isinstance(emb, list) for emb in embeddings)
        assert all(len(emb) > 0 for emb in embeddings)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])