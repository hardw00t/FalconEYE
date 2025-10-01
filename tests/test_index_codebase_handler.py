"""
End-to-end tests for IndexCodebaseHandler with smart re-indexing.

Uses real implementations (no mocks) to validate the complete flow.
"""

import pytest
import tempfile
import shutil
import asyncio
from pathlib import Path
from typing import List, Optional

from falconeye.application.commands.index_codebase import (
    IndexCodebaseCommand,
    IndexCodebaseHandler,
)
from falconeye.domain.services.project_identifier import ProjectIdentifier
from falconeye.domain.services.checksum_service import ChecksumService
from falconeye.domain.services.language_detector import LanguageDetector
from falconeye.infrastructure.registry.chroma_registry_adapter import (
    ChromaIndexRegistryAdapter,
)
from falconeye.domain.repositories.vector_store_repository import VectorStoreRepository
from falconeye.domain.repositories.metadata_repository import MetadataRepository
from falconeye.domain.services.llm_service import LLMService
from falconeye.domain.models.code_chunk import CodeChunk
from falconeye.domain.models.document import DocumentChunk
from falconeye.infrastructure.ast.ast_analyzer import EnhancedASTAnalyzer


# ===== Test Implementations (Real, not mocks) =====

class InMemoryVectorStore(VectorStoreRepository):
    """Simple in-memory vector store for testing."""

    def __init__(self):
        self.code_chunks = []
        self.document_chunks = []

    async def store_chunks(self, chunks: List[CodeChunk], collection: str = "code") -> None:
        self.code_chunks.extend(chunks)

    async def search_similar(self, query: str, top_k: int = 5, collection: str = "code", filters: Optional[dict] = None) -> List[CodeChunk]:
        return self.code_chunks[:top_k]

    async def search_by_embedding(self, embedding: List[float], top_k: int = 5, collection: str = "code") -> List[CodeChunk]:
        return self.code_chunks[:top_k]

    async def delete_collection(self, collection: str) -> None:
        if collection == "code":
            self.code_chunks = []
        else:
            self.document_chunks = []

    async def collection_exists(self, collection: str) -> bool:
        return True

    async def get_chunk_count(self, collection: str) -> int:
        return len(self.code_chunks) if collection == "code" else len(self.document_chunks)

    async def store_document_chunks(self, chunks: List[DocumentChunk], collection: str = "documents") -> None:
        self.document_chunks.extend(chunks)

    async def search_similar_documents(self, query: str, top_k: int = 5, collection: str = "documents", query_embedding: Optional[List[float]] = None) -> List[DocumentChunk]:
        return self.document_chunks[:top_k]


class InMemoryMetadataRepository(MetadataRepository):
    """Simple in-memory metadata repository for testing."""

    def __init__(self):
        self.metadata = {}

    async def store_metadata(self, metadata) -> None:
        file_path = metadata.file_path if hasattr(metadata, 'file_path') else "unknown"
        self.metadata[file_path] = metadata

    async def get_metadata(self, file_path: str) -> Optional[dict]:
        return self.metadata.get(file_path)

    async def get_function_calls_graph(self, target_function: Optional[str] = None):
        return {}

    async def get_dependency_graph(self):
        return {}

    async def get_statistics(self):
        return {"total_functions": 0, "total_files": 0}

    async def search_functions(self, function_name: str):
        return []


class SimpleLLMService(LLMService):
    """Simple deterministic LLM service for testing."""

    def count_tokens(self, text: str) -> int:
        # Simple word count approximation
        return len(text.split())

    async def generate_embedding(self, text: str) -> List[float]:
        # Deterministic fake embedding based on text length
        text_hash = hash(text) % 1000
        return [float(text_hash / 1000.0)] * 384  # 384-dim embedding

    async def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        return [await self.generate_embedding(text) for text in texts]

    async def generate_completion(self, prompt: str, **kwargs) -> str:
        return "Test completion"

    async def generate_completion_stream(self, prompt: str, **kwargs):
        yield "Test"
        yield " completion"

    async def analyze_code_security(self, code: str, **kwargs) -> dict:
        return {"findings": []}

    async def summarize_findings(self, findings: List[dict], **kwargs) -> str:
        return "No findings"

    async def validate_findings(self, findings: List[dict], **kwargs) -> List[dict]:
        return findings

    async def health_check(self) -> bool:
        return True


# ===== Tests =====

class TestIndexCodebaseHandler:
    """End-to-end tests for IndexCodebaseHandler."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create temporary directories
        self.temp_dir = tempfile.mkdtemp()
        self.temp_dir_path = Path(self.temp_dir)
        self.registry_dir = tempfile.mkdtemp()

        # Initialize real services
        self.project_identifier = ProjectIdentifier()
        self.checksum_service = ChecksumService()
        self.language_detector = LanguageDetector()
        self.registry = ChromaIndexRegistryAdapter(
            persist_directory=self.registry_dir,
            collection_name="test_handler_registry",
        )

        # Initialize test implementations
        self.vector_store = InMemoryVectorStore()
        self.metadata_repo = InMemoryMetadataRepository()
        self.llm_service = SimpleLLMService()
        self.ast_analyzer = EnhancedASTAnalyzer()

        # Create handler
        self.handler = IndexCodebaseHandler(
            vector_store=self.vector_store,
            metadata_repo=self.metadata_repo,
            llm_service=self.llm_service,
            language_detector=self.language_detector,
            ast_analyzer=self.ast_analyzer,
            project_identifier=self.project_identifier,
            checksum_service=self.checksum_service,
            index_registry=self.registry,
        )

    def teardown_method(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        shutil.rmtree(self.registry_dir, ignore_errors=True)

    # ===== Test: First-time indexing =====

    @pytest.mark.asyncio
    async def test_first_time_indexing_full_flow(self):
        """
        Test complete first-time indexing flow.

        Scenario:
        - Create Python project with 3 files
        - Index for first time
        - Verify project metadata saved
        - Verify file metadata saved
        - Verify chunks stored
        """
        # Create project
        project_dir = self.temp_dir_path / "test_project"
        project_dir.mkdir()

        files = {
            "main.py": "def main():\n    print('Hello')\n\nif __name__ == '__main__':\n    main()\n",
            "utils.py": "def helper():\n    return 42\n",
            "config.py": "DEBUG = True\nVERSION = '1.0.0'\n",
        }

        for filename, content in files.items():
            (project_dir / filename).write_text(content)

        # Create command
        command = IndexCodebaseCommand(
            codebase_path=project_dir,
            language="python",
            chunk_size=10,
            chunk_overlap=2,
            include_documents=False,
        )

        # Execute
        codebase = await self.handler.handle(command)

        # Verify codebase
        assert codebase is not None
        assert codebase.total_files == 3

        # Verify project metadata in registry
        project_id, _, _, _ = self.project_identifier.identify_project(project_dir)
        project_meta = self.registry.get_project(project_id)

        assert project_meta is not None
        assert project_meta.project_id == project_id
        assert project_meta.total_files == 3
        assert "python" in project_meta.languages

        # Verify file metadata in registry
        all_files = self.registry.get_all_files(project_id)
        assert len(all_files) == 3

        # Verify chunks stored
        assert len(self.vector_store.code_chunks) > 0

    # ===== Test: Re-indexing with no changes =====

    @pytest.mark.asyncio
    async def test_reindex_no_changes_skips_files(self):
        """
        Test that re-indexing with no changes skips all files.

        Scenario:
        - Index project
        - Re-index without any changes
        - Verify files are skipped
        """
        # Create project
        project_dir = self.temp_dir_path / "stable_project"
        project_dir.mkdir()

        (project_dir / "stable.py").write_text("# Stable code\n")

        # First index
        command = IndexCodebaseCommand(
            codebase_path=project_dir,
            language="python",
            include_documents=False,
        )

        await self.handler.handle(command)

        initial_chunk_count = len(self.vector_store.code_chunks)

        # Re-index (no changes)
        codebase = await self.handler.handle(command)

        # Verify: No new chunks added (files skipped)
        assert len(self.vector_store.code_chunks) == initial_chunk_count

    # ===== Test: Re-indexing with modified file =====

    @pytest.mark.asyncio
    async def test_reindex_modified_file_processed(self):
        """
        Test that modified files are re-indexed.

        Scenario:
        - Index project with 2 files
        - Modify 1 file
        - Re-index
        - Verify modified file is processed
        """
        # Create project
        project_dir = self.temp_dir_path / "modified_project"
        project_dir.mkdir()

        file1 = project_dir / "unchanged.py"
        file2 = project_dir / "modified.py"

        file1.write_text("# Unchanged\n")
        file2.write_text("# Original\n")

        # First index
        command = IndexCodebaseCommand(
            codebase_path=project_dir,
            language="python",
            include_documents=False,
        )

        await self.handler.handle(command)

        initial_chunk_count = len(self.vector_store.code_chunks)

        # Modify file2
        import time
        time.sleep(0.01)  # Ensure mtime changes
        file2.write_text("# Modified content\ndef new_function():\n    pass\n")

        # Re-index
        await self.handler.handle(command)

        # Verify: New chunks added (modified file processed)
        assert len(self.vector_store.code_chunks) > initial_chunk_count

    # ===== Test: Force re-index =====

    @pytest.mark.asyncio
    async def test_force_reindex_processes_all(self):
        """
        Test that force_reindex=True processes all files.

        Scenario:
        - Index project
        - Re-index with force_reindex=True
        - Verify all files processed
        """
        # Create project
        project_dir = self.temp_dir_path / "force_project"
        project_dir.mkdir()

        (project_dir / "file.py").write_text("# Test\n")

        # First index
        command = IndexCodebaseCommand(
            codebase_path=project_dir,
            language="python",
            include_documents=False,
        )

        await self.handler.handle(command)

        initial_chunk_count = len(self.vector_store.code_chunks)

        # Force re-index
        force_command = IndexCodebaseCommand(
            codebase_path=project_dir,
            language="python",
            force_reindex=True,
            include_documents=False,
        )

        await self.handler.handle(force_command)

        # Verify: New chunks added (all files processed)
        assert len(self.vector_store.code_chunks) > initial_chunk_count

    # ===== Test: Explicit project_id =====

    @pytest.mark.asyncio
    async def test_explicit_project_id(self):
        """
        Test explicit project_id override.

        Scenario:
        - Index with explicit project_id
        - Verify metadata uses explicit ID
        """
        # Create project
        project_dir = self.temp_dir_path / "explicit_project"
        project_dir.mkdir()

        (project_dir / "app.py").write_text("# App\n")

        # Index with explicit ID
        command = IndexCodebaseCommand(
            codebase_path=project_dir,
            language="python",
            project_id="my-custom-id",
            include_documents=False,
        )

        await self.handler.handle(command)

        # Verify project metadata uses explicit ID
        project_meta = self.registry.get_project("my-custom-id")
        assert project_meta is not None
        assert project_meta.project_id == "my-custom-id"

    # ===== Test: Multiple projects isolated =====

    @pytest.mark.asyncio
    async def test_multiple_projects_isolated(self):
        """
        Test that multiple projects are properly isolated.

        Scenario:
        - Index project A
        - Index project B
        - Verify separate metadata
        """
        # Create project A
        project_a = self.temp_dir_path / "project_a"
        project_a.mkdir()
        (project_a / "a.py").write_text("# Project A\n")

        # Create project B
        project_b = self.temp_dir_path / "project_b"
        project_b.mkdir()
        (project_b / "b.py").write_text("# Project B\n")

        # Index both
        await self.handler.handle(IndexCodebaseCommand(
            codebase_path=project_a,
            language="python",
            include_documents=False,
        ))

        await self.handler.handle(IndexCodebaseCommand(
            codebase_path=project_b,
            language="python",
            include_documents=False,
        ))

        # Verify separate project IDs
        proj_a_id, _, _, _ = self.project_identifier.identify_project(project_a)
        proj_b_id, _, _, _ = self.project_identifier.identify_project(project_b)

        assert proj_a_id != proj_b_id

        # Verify separate metadata
        proj_a_meta = self.registry.get_project(proj_a_id)
        proj_b_meta = self.registry.get_project(proj_b_id)

        assert proj_a_meta is not None
        assert proj_b_meta is not None
        assert proj_a_meta.project_name != proj_b_meta.project_name


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
