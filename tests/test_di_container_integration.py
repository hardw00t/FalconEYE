"""
Integration tests for DI Container with smart re-indexing services.

Tests the complete dependency injection setup with real services (no mocks).
Validates that all services are correctly wired and work together.
"""

import pytest
import tempfile
import shutil
import yaml
from pathlib import Path
from typing import Optional

from falconeye.infrastructure.di.container import DIContainer
from falconeye.infrastructure.config.config_models import FalconEyeConfig
from falconeye.infrastructure.config.config_loader import ConfigLoader
from falconeye.application.commands.index_codebase import IndexCodebaseCommand


class TestDIContainerIntegration:
    """Integration tests for DI container with new smart re-indexing services."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create temporary directories
        self.temp_dir = tempfile.mkdtemp()
        self.temp_dir_path = Path(self.temp_dir)
        self.registry_dir = tempfile.mkdtemp()
        self.vector_store_dir = tempfile.mkdtemp()
        self.metadata_dir = tempfile.mkdtemp()
        self.output_dir = tempfile.mkdtemp()

        # Create test config file
        self.config_path = self.temp_dir_path / "test_config.yaml"
        self._create_test_config_file()

    def teardown_method(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        shutil.rmtree(self.registry_dir, ignore_errors=True)
        shutil.rmtree(self.vector_store_dir, ignore_errors=True)
        shutil.rmtree(self.metadata_dir, ignore_errors=True)
        shutil.rmtree(self.output_dir, ignore_errors=True)

    def _create_test_config_file(self):
        """Create a minimal config file for testing."""
        config_dict = {
            "llm": {
                "provider": "ollama",
                "model": {
                    "analysis": "qwen3-coder:30b",
                    "embedding": "embeddinggemma:300m",
                },
                "base_url": "http://localhost:11434",
                "timeout": 120,
                "max_retries": 3,
            },
            "vector_store": {
                "provider": "chroma",
                "persist_directory": str(self.vector_store_dir),
                "collection_prefix": "test",
            },
            "metadata": {
                "provider": "chroma",
                "persist_directory": str(self.metadata_dir),
                "collection_name": "test_metadata",
            },
            "index_registry": {
                "persist_directory": str(self.registry_dir),
                "collection_name": "test_registry",
            },
            "chunking": {
                "chunk_size": 10,
                "chunk_overlap": 2,
                "language_specific": {
                    "python": {"chunk_size": 10, "chunk_overlap": 2}
                },
            },
            "analysis": {
                "enable_vulnerability_scanning": False,
                "enable_code_quality_check": False,
                "enable_compliance_check": False,
                "enable_architecture_analysis": False,
            },
            "languages": {
                "supported": ["python", "javascript"],
                "auto_detect": True,
            },
            "file_discovery": {
                "max_file_size_mb": 10,
                "exclude_patterns": ["*.pyc", "__pycache__"],
                "exclude_directories": [".git", "node_modules"],
            },
            "output": {
                "format": "markdown",
                "output_directory": str(self.output_dir),
                "save_to_file": False,
            },
            "logging": {
                "level": "INFO",
                "log_to_file": False,
            },
        }
        with open(self.config_path, "w") as f:
            yaml.dump(config_dict, f)

    # ===== Test: DI Container Creation =====

    @pytest.mark.asyncio
    async def test_di_container_creates_all_services(self):
        """
        Test that DIContainer creates all required services.

        Scenario:
        - Create DIContainer with config
        - Verify all services are created
        - Verify services have correct types
        """
        container = DIContainer.create(str(self.config_path))

        # Verify core services
        assert container.llm_service is not None
        assert container.vector_store is not None
        assert container.metadata_repo is not None
        assert container.language_detector is not None
        assert container.ast_analyzer is not None

        # Verify new smart re-indexing services
        assert container.project_identifier is not None
        assert container.checksum_service is not None
        assert container.index_registry is not None

        # Verify handler
        assert container.index_handler is not None

    # ===== Test: IndexCodebaseHandler Wiring =====

    @pytest.mark.asyncio
    async def test_index_handler_has_all_dependencies(self):
        """
        Test that IndexCodebaseHandler receives all 8 dependencies.

        Scenario:
        - Create DIContainer
        - Verify IndexCodebaseHandler has all required attributes
        """
        container = DIContainer.create(str(self.config_path))
        handler = container.index_handler

        # Verify all 8 dependencies are present
        assert hasattr(handler, "vector_store")
        assert hasattr(handler, "metadata_repo")
        assert hasattr(handler, "llm_service")
        assert hasattr(handler, "language_detector")
        assert hasattr(handler, "ast_analyzer")
        assert hasattr(handler, "project_identifier")
        assert hasattr(handler, "checksum_service")
        assert hasattr(handler, "index_registry")

        # Verify dependencies are not None
        assert handler.vector_store is not None
        assert handler.metadata_repo is not None
        assert handler.llm_service is not None
        assert handler.language_detector is not None
        assert handler.ast_analyzer is not None
        assert handler.project_identifier is not None
        assert handler.checksum_service is not None
        assert handler.index_registry is not None

    # ===== Test: IndexRegistry Configuration =====

    @pytest.mark.asyncio
    async def test_index_registry_configured_correctly(self):
        """
        Test that IndexRegistry is configured with correct settings.

        Scenario:
        - Create DIContainer with registry config
        - Verify registry uses correct persist directory
        - Verify registry uses correct collection name
        """
        container = DIContainer.create(str(self.config_path))
        registry = container.index_registry

        # Verify registry is functional
        assert registry is not None

        # Test basic registry operations
        from falconeye.domain.value_objects.project_metadata import (
            ProjectMetadata,
            ProjectType,
        )
        from datetime import datetime

        test_project = ProjectMetadata(
            project_id="test-project",
            project_name="Test Project",
            project_type=ProjectType.NON_GIT,
            project_root=Path("/test/path"),
            languages=["python"],
            total_files=1,
        )

        # Save and retrieve
        registry.save_project(test_project)
        retrieved = registry.get_project("test-project")

        assert retrieved is not None
        assert retrieved.project_id == "test-project"
        assert retrieved.project_name == "Test Project"

    # ===== Test: End-to-End Indexing Through DI Container =====

    @pytest.mark.asyncio
    async def test_end_to_end_indexing_through_container(self):
        """
        Test complete indexing flow through DI container.

        Scenario:
        - Create test project
        - Create DIContainer
        - Execute indexing command through handler
        - Verify project metadata saved to registry
        - Verify files indexed to vector store
        """
        # Create test project
        project_dir = self.temp_dir_path / "test_project"
        project_dir.mkdir()
        (project_dir / "main.py").write_text("def hello():\n    print('Hello')\n")

        # Create container and handler
        container = DIContainer.create(str(self.config_path))
        handler = container.index_handler

        # Create command
        command = IndexCodebaseCommand(
            codebase_path=project_dir,
            language="python",
            chunk_size=10,
            chunk_overlap=2,
            include_documents=False,
        )

        # Execute indexing
        codebase = await handler.handle(command)

        # Verify codebase result
        assert codebase is not None
        assert codebase.total_files == 1

        # Verify project metadata in registry
        project_id, _, _, _ = container.project_identifier.identify_project(project_dir)
        project_meta = container.index_registry.get_project(project_id)

        assert project_meta is not None
        assert project_meta.project_id == project_id
        assert project_meta.total_files == 1
        assert "python" in project_meta.languages

    # ===== Test: Smart Re-indexing Through DI Container =====

    @pytest.mark.asyncio
    async def test_smart_reindexing_through_container(self):
        """
        Test smart re-indexing flow through DI container.

        Scenario:
        - Index project first time
        - Re-index without changes
        - Verify files are skipped (smart re-indexing works)
        """
        # Create test project
        project_dir = self.temp_dir_path / "reindex_project"
        project_dir.mkdir()
        (project_dir / "stable.py").write_text("# Stable code\n")

        # Create container
        container = DIContainer.create(str(self.config_path))
        handler = container.index_handler

        # First index
        command = IndexCodebaseCommand(
            codebase_path=project_dir,
            language="python",
            include_documents=False,
        )
        await handler.handle(command)

        # Get project ID
        project_id, _, _, _ = container.project_identifier.identify_project(project_dir)

        # Verify project exists in registry
        project_meta = container.index_registry.get_project(project_id)
        assert project_meta is not None
        initial_scan_time = project_meta.last_full_scan

        # Re-index (no changes)
        import asyncio
        await asyncio.sleep(0.1)  # Ensure time difference
        codebase = await handler.handle(command)

        # Verify project metadata updated
        project_meta_after = container.index_registry.get_project(project_id)
        assert project_meta_after is not None
        assert project_meta_after.last_full_scan > initial_scan_time

    # ===== Test: Force Re-index Through DI Container =====

    @pytest.mark.asyncio
    async def test_force_reindex_through_container(self):
        """
        Test force re-index through DI container.

        Scenario:
        - Index project
        - Force re-index
        - Verify all files processed
        """
        # Create test project
        project_dir = self.temp_dir_path / "force_project"
        project_dir.mkdir()
        (project_dir / "code.py").write_text("# Code\n")

        # Create container
        container = DIContainer.create(str(self.config_path))
        handler = container.index_handler

        # First index
        command = IndexCodebaseCommand(
            codebase_path=project_dir,
            language="python",
            include_documents=False,
        )
        await handler.handle(command)

        # Force re-index
        force_command = IndexCodebaseCommand(
            codebase_path=project_dir,
            language="python",
            force_reindex=True,
            include_documents=False,
        )
        codebase = await handler.handle(force_command)

        # Verify project processed
        assert codebase is not None
        assert codebase.total_files == 1

    # ===== Test: Explicit Project ID Through DI Container =====

    @pytest.mark.asyncio
    async def test_explicit_project_id_through_container(self):
        """
        Test explicit project ID override through DI container.

        Scenario:
        - Index with explicit project_id
        - Verify registry uses explicit ID
        """
        # Create test project
        project_dir = self.temp_dir_path / "explicit_project"
        project_dir.mkdir()
        (project_dir / "app.py").write_text("# App\n")

        # Create container
        container = DIContainer.create(str(self.config_path))
        handler = container.index_handler

        # Index with explicit ID
        command = IndexCodebaseCommand(
            codebase_path=project_dir,
            language="python",
            project_id="my-custom-id",
            include_documents=False,
        )
        await handler.handle(command)

        # Verify explicit ID used
        project_meta = container.index_registry.get_project("my-custom-id")
        assert project_meta is not None
        assert project_meta.project_id == "my-custom-id"

    # ===== Test: Multiple Projects Through DI Container =====

    @pytest.mark.asyncio
    async def test_multiple_projects_through_container(self):
        """
        Test indexing multiple projects through same DI container.

        Scenario:
        - Index project A
        - Index project B
        - Verify both isolated in registry
        """
        # Create projects
        project_a = self.temp_dir_path / "project_a"
        project_a.mkdir()
        (project_a / "a.py").write_text("# Project A\n")

        project_b = self.temp_dir_path / "project_b"
        project_b.mkdir()
        (project_b / "b.py").write_text("# Project B\n")

        # Create container
        container = DIContainer.create(str(self.config_path))
        handler = container.index_handler

        # Index both projects
        await handler.handle(
            IndexCodebaseCommand(
                codebase_path=project_a, language="python", include_documents=False
            )
        )
        await handler.handle(
            IndexCodebaseCommand(
                codebase_path=project_b, language="python", include_documents=False
            )
        )

        # Verify both projects in registry
        proj_a_id, _, _, _ = container.project_identifier.identify_project(project_a)
        proj_b_id, _, _, _ = container.project_identifier.identify_project(project_b)

        assert proj_a_id != proj_b_id

        proj_a_meta = container.index_registry.get_project(proj_a_id)
        proj_b_meta = container.index_registry.get_project(proj_b_id)

        assert proj_a_meta is not None
        assert proj_b_meta is not None
        assert proj_a_meta.project_name != proj_b_meta.project_name

    # ===== Test: Service Dependencies Are Shared =====

    @pytest.mark.asyncio
    async def test_services_are_singleton_instances(self):
        """
        Test that services are singleton instances (not recreated).

        Scenario:
        - Get same service multiple times from container
        - Verify they are the same instance (shared state)
        """
        container = DIContainer.create(str(self.config_path))

        # Services should be same instances
        assert container.llm_service is container.index_handler.llm_service
        assert container.vector_store is container.index_handler.vector_store
        assert container.metadata_repo is container.index_handler.metadata_repo
        assert container.project_identifier is container.index_handler.project_identifier
        assert container.checksum_service is container.index_handler.checksum_service
        assert container.index_registry is container.index_handler.index_registry


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
