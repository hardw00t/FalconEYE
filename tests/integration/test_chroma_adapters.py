"""Integration tests for ChromaDB adapters."""

import pytest
import sys
from pathlib import Path
import asyncio

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from falconeye.infrastructure.vector_stores.chroma_adapter import ChromaVectorStoreAdapter
from falconeye.infrastructure.persistence.chroma_metadata_repository import ChromaMetadataRepository
from falconeye.infrastructure.llm_providers.ollama_adapter import OllamaLLMAdapter
from falconeye.domain.models.code_chunk import CodeChunk, ChunkMetadata
from falconeye.domain.models.structural import StructuralMetadata, FunctionInfo, ImportInfo


@pytest.mark.integration
class TestChromaVectorStoreAdapter:
    """Test ChromaDB vector store adapter."""

    @pytest.fixture
    async def vector_store(self):
        """Create vector store adapter."""
        store = ChromaVectorStoreAdapter(
            persist_directory="./test_chromadb",
            collection_prefix="test"
        )
        # Clean up before test
        await store.delete_collection("code")
        yield store
        # Clean up after test
        await store.delete_collection("code")

    @pytest.fixture
    async def ollama_adapter(self):
        """Create Ollama adapter for embeddings."""
        return OllamaLLMAdapter()

    @pytest.mark.asyncio
    async def test_store_and_search_chunks(self, vector_store, ollama_adapter):
        """Test storing and searching code chunks."""
        # Create test chunks with embeddings
        code_samples = [
            "def vulnerable_function(user_input): exec(user_input)",
            "def safe_function(a, b): return a + b",
            "import os; os.system(user_input)",
        ]

        chunks = []
        for i, code in enumerate(code_samples):
            # Generate embedding
            embedding = await ollama_adapter.generate_embedding(code)

            metadata = ChunkMetadata(
                file_path=f"test{i}.py",
                language="python",
                start_line=1,
                end_line=1,
                chunk_index=i,
                total_chunks=len(code_samples),
            )

            chunk = CodeChunk.create(
                content=code,
                metadata=metadata,
                token_count=len(code) // 4,
                embedding=embedding,
            )
            chunks.append(chunk)

        # Store chunks
        await vector_store.store_chunks(chunks, collection="code")

        # Verify count
        count = await vector_store.get_chunk_count("code")
        assert count == 3

        # Generate embedding for search query
        query_text = "vulnerable code with exec"
        query_embedding = await ollama_adapter.generate_embedding(query_text)

        # Search for vulnerable code with consistent embeddings
        results = await vector_store.search_similar(
            query=query_text,
            top_k=2,
            collection="code",
            query_embedding=query_embedding
        )

        assert len(results) > 0
        assert any("exec" in r.content for r in results)

    @pytest.mark.asyncio
    async def test_collection_management(self, vector_store):
        """Test collection existence and deletion."""
        # Initially should not exist
        exists = await vector_store.collection_exists("test_collection")
        assert not exists

        # Create by storing chunks
        metadata = ChunkMetadata(
            file_path="test.py",
            language="python",
            start_line=1,
            end_line=1,
            chunk_index=0,
            total_chunks=1,
        )

        chunk = CodeChunk.create(
            content="test code",
            metadata=metadata,
            token_count=2,
            embedding=[0.1] * 768,  # Dummy embedding
        )

        await vector_store.store_chunks([chunk], collection="test_collection")

        # Now should exist
        exists = await vector_store.collection_exists("test_collection")
        assert exists

        # Delete
        await vector_store.delete_collection("test_collection")

        # Should not exist
        exists = await vector_store.collection_exists("test_collection")
        assert not exists


@pytest.mark.integration
class TestChromaMetadataRepository:
    """Test ChromaDB metadata repository."""

    @pytest.fixture
    async def metadata_repo(self):
        """Create metadata repository."""
        repo = ChromaMetadataRepository(
            persist_directory="./test_chromadb",
            collection_name="test_metadata"
        )
        yield repo

    @pytest.mark.asyncio
    async def test_store_and_retrieve_metadata(self, metadata_repo):
        """Test storing and retrieving structural metadata."""
        # Create test metadata
        metadata = StructuralMetadata(
            file_path="test.py",
            language="python"
        )

        metadata.functions.append(FunctionInfo(
            name="test_function",
            line=10,
            parameters=["a", "b"],
        ))

        metadata.imports.append(ImportInfo(
            statement="import os",
            line=1,
            module="os",
        ))

        # Store metadata
        await metadata_repo.store_metadata(metadata)

        # Retrieve metadata
        retrieved = await metadata_repo.get_metadata("test.py")

        assert retrieved is not None
        assert retrieved.file_path == "test.py"
        assert retrieved.language == "python"
        assert len(retrieved.functions) == 1
        assert retrieved.functions[0].name == "test_function"
        assert len(retrieved.imports) == 1
        assert retrieved.imports[0].module == "os"

    @pytest.mark.asyncio
    async def test_get_statistics(self, metadata_repo):
        """Test getting codebase statistics."""
        # Create and store multiple metadata entries
        for i in range(3):
            metadata = StructuralMetadata(
                file_path=f"file{i}.py",
                language="python"
            )
            metadata.functions.append(FunctionInfo(
                name=f"func{i}",
                line=i * 10,
            ))
            await metadata_repo.store_metadata(metadata)

        # Get statistics
        stats = await metadata_repo.get_statistics()

        assert stats["total_files"] >= 3
        assert stats["total_functions"] >= 3
        assert "python" in stats["language_breakdown"]

    @pytest.mark.asyncio
    async def test_search_functions(self, metadata_repo):
        """Test searching for functions."""
        # Create metadata with functions
        metadata = StructuralMetadata(
            file_path="search_test.py",
            language="python"
        )
        metadata.functions.append(FunctionInfo(
            name="vulnerable_exec",
            line=20,
        ))
        await metadata_repo.store_metadata(metadata)

        # Search for function
        results = await metadata_repo.search_functions("vulnerable")

        assert len(results) > 0
        assert any("vulnerable" in r["function_name"] for r in results)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])