"""End-to-end integration tests."""

import pytest
import sys
from pathlib import Path
import tempfile
import shutil

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from falconeye.infrastructure.llm_providers.ollama_adapter import OllamaLLMAdapter
from falconeye.infrastructure.vector_stores.chroma_adapter import ChromaVectorStoreAdapter
from falconeye.infrastructure.persistence.chroma_metadata_repository import ChromaMetadataRepository
from falconeye.infrastructure.registry.chroma_registry_adapter import ChromaIndexRegistryAdapter
from falconeye.infrastructure.ast.ast_analyzer import EnhancedASTAnalyzer
from falconeye.domain.services.security_analyzer import SecurityAnalyzer
from falconeye.domain.services.context_assembler import ContextAssembler
from falconeye.domain.services.language_detector import LanguageDetector
from falconeye.domain.services.project_identifier import ProjectIdentifier
from falconeye.domain.services.checksum_service import ChecksumService
from falconeye.application.commands.index_codebase import IndexCodebaseCommand, IndexCodebaseHandler
from falconeye.application.commands.review_file import ReviewFileCommand, ReviewFileHandler


@pytest.mark.integration
class TestEndToEnd:
    """End-to-end integration tests with real components."""

    @pytest.fixture
    def temp_codebase(self):
        """Create temporary codebase for testing."""
        temp_dir = tempfile.mkdtemp()
        temp_path = Path(temp_dir)

        # Create test files with vulnerabilities
        vulnerable_file = temp_path / "vulnerable.py"
        vulnerable_file.write_text("""
import os

def execute_command(user_input):
    # Command injection vulnerability
    os.system(user_input)

def sql_query(user_input):
    # SQL injection vulnerability
    query = f"SELECT * FROM users WHERE id = {user_input}"
    return query
""")

        safe_file = temp_path / "safe.py"
        safe_file.write_text("""
def add_numbers(a: int, b: int) -> int:
    \"\"\"Safely add two numbers.\"\"\"
    return a + b

def greet(name: str) -> str:
    \"\"\"Greet a user.\"\"\"
    return f"Hello, {name}!"
""")

        yield temp_path

        # Cleanup
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def test_chromadb_dir(self):
        """Create temporary ChromaDB directory."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def components(self, test_chromadb_dir):
        """Create all components."""
        # Infrastructure
        llm_service = OllamaLLMAdapter()
        vector_store = ChromaVectorStoreAdapter(
            persist_directory=test_chromadb_dir,
            collection_prefix="test_e2e"
        )
        metadata_repo = ChromaMetadataRepository(
            persist_directory=test_chromadb_dir,
            collection_name="test_e2e_metadata"
        )
        ast_analyzer = EnhancedASTAnalyzer()
        language_detector = LanguageDetector()

        # Domain services
        security_analyzer = SecurityAnalyzer(llm_service)
        context_assembler = ContextAssembler(vector_store, metadata_repo)
        project_identifier = ProjectIdentifier()
        checksum_service = ChecksumService()

        # Registry
        registry_dir = tempfile.mkdtemp()
        index_registry = ChromaIndexRegistryAdapter(
            persist_directory=registry_dir,
            collection_name="test_registry",
        )

        # Application handlers
        index_handler = IndexCodebaseHandler(
            vector_store=vector_store,
            metadata_repo=metadata_repo,
            llm_service=llm_service,
            language_detector=language_detector,
            ast_analyzer=ast_analyzer,
            project_identifier=project_identifier,
            checksum_service=checksum_service,
            index_registry=index_registry,
        )

        review_handler = ReviewFileHandler(
            security_analyzer=security_analyzer,
            context_assembler=context_assembler,
        )

        return {
            "index_handler": index_handler,
            "review_handler": review_handler,
            "vector_store": vector_store,
            "metadata_repo": metadata_repo,
        }

    @pytest.mark.asyncio
    async def test_full_workflow_index_and_review(self, temp_codebase, components):
        """
        Test complete workflow: index codebase then review a file.

        This validates the entire FalconEYE architecture with real components.
        """
        print(f"\n=== Testing Full Workflow ===")
        print(f"Codebase: {temp_codebase}")

        # Step 1: Index the codebase
        print("\n[Step 1] Indexing codebase...")
        index_command = IndexCodebaseCommand(
            codebase_path=temp_codebase,
            language="python",
            chunk_size=20,
            chunk_overlap=5,
        )

        codebase = await components["index_handler"].handle(index_command)

        assert codebase.total_files == 2
        print(f"  Indexed {codebase.total_files} files")

        # Verify chunks were stored
        chunk_count = await components["vector_store"].get_chunk_count("code")
        assert chunk_count > 0
        print(f"  Stored {chunk_count} code chunks")

        # Verify metadata was stored
        metadata = await components["metadata_repo"].get_metadata("vulnerable.py")
        assert metadata is not None
        assert len(metadata.functions) > 0
        print(f"  Extracted metadata: {len(metadata.functions)} functions")

        # Step 2: Review vulnerable file
        print("\n[Step 2] Reviewing vulnerable file...")

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
Focus on command injection, SQL injection, and OWASP Top 10 vulnerabilities."""

        review_command = ReviewFileCommand(
            file_path=temp_codebase / "vulnerable.py",
            language="python",
            system_prompt=system_prompt,
            validate_findings=False,
            top_k_context=3,
        )

        review = await components["review_handler"].handle(review_command)

        print(f"  Found {len(review.findings)} security issues")

        # Verify AI found vulnerabilities
        assert len(review.findings) > 0, "AI should find vulnerabilities in vulnerable.py"

        # Check that findings contain expected vulnerability types
        finding_texts = " ".join([f.issue.lower() for f in review.findings])
        assert any(term in finding_texts for term in ["command", "injection", "sql", "exec", "system"]), \
            "AI should identify command or SQL injection"

        # Display findings
        for i, finding in enumerate(review.findings, 1):
            print(f"\n  Finding {i}:")
            print(f"    Issue: {finding.issue}")
            print(f"    Severity: {finding.severity.value}")
            print(f"    Confidence: {finding.confidence.value}")

        print("\n=== Full Workflow Test Complete ===")

    @pytest.mark.asyncio
    async def test_ast_analyzer_integration(self, temp_codebase, components):
        """Test AST analyzer extracts metadata correctly."""
        print(f"\n=== Testing AST Analyzer ===")

        # Read vulnerable file
        vulnerable_file = temp_codebase / "vulnerable.py"
        content = vulnerable_file.read_text()

        # Analyze with AST
        ast_analyzer = EnhancedASTAnalyzer()
        metadata = ast_analyzer.analyze_file("vulnerable.py", content)

        # Verify extraction
        assert metadata.language == "python"
        assert len(metadata.functions) == 2  # execute_command, sql_query
        assert len(metadata.imports) >= 1  # import os

        print(f"  Functions found: {[f.name for f in metadata.functions]}")
        print(f"  Imports found: {[i.module for i in metadata.imports]}")

        # Check specific functions
        func_names = [f.name for f in metadata.functions]
        assert "execute_command" in func_names
        assert "sql_query" in func_names

        print("\n=== AST Analyzer Test Complete ===")

    @pytest.mark.asyncio
    async def test_semantic_search(self, temp_codebase, components):
        """Test semantic search retrieves relevant code."""
        print(f"\n=== Testing Semantic Search ===")

        # Index codebase first
        index_command = IndexCodebaseCommand(
            codebase_path=temp_codebase,
            language="python",
        )
        await components["index_handler"].handle(index_command)

        # Generate embedding for search query using Ollama
        from falconeye.infrastructure.llm_providers.ollama_adapter import OllamaLLMAdapter
        llm = OllamaLLMAdapter()
        query_text = "command injection os.system vulnerability"
        query_embedding = await llm.generate_embedding(query_text)

        # Search for vulnerable patterns with consistent embeddings
        results = await components["vector_store"].search_similar(
            query=query_text,
            top_k=3,
            collection="code",
            query_embedding=query_embedding
        )

        assert len(results) > 0
        print(f"  Found {len(results)} relevant chunks")

        # Check that vulnerable code is in results
        result_contents = " ".join([r.content for r in results])
        assert "os.system" in result_contents or "execute_command" in result_contents

        print("\n=== Semantic Search Test Complete ===")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])