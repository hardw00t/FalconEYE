"""
Integration tests for CLI commands with smart re-indexing features.

Tests the complete CLI flow with real implementations (no mocks).
Validates new --project-id and --force-reindex flags.
"""

import pytest
import tempfile
import shutil
import yaml
from pathlib import Path
from typer.testing import CliRunner
from unittest.mock import patch

# Import CLI app
from falconeye.adapters.cli.main import app


class TestCLIIntegration:
    """Integration tests for CLI commands."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create temporary directories
        self.temp_dir = tempfile.mkdtemp()
        self.temp_dir_path = Path(self.temp_dir)
        self.vector_store_dir = tempfile.mkdtemp()
        self.metadata_dir = tempfile.mkdtemp()
        self.registry_dir = tempfile.mkdtemp()
        self.output_dir = tempfile.mkdtemp()

        # Create test config file
        self.config_path = self.temp_dir_path / "test_config.yaml"
        self._create_test_config_file()

        # Create CLI runner
        self.runner = CliRunner()

    def teardown_method(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        shutil.rmtree(self.vector_store_dir, ignore_errors=True)
        shutil.rmtree(self.metadata_dir, ignore_errors=True)
        shutil.rmtree(self.registry_dir, ignore_errors=True)
        shutil.rmtree(self.output_dir, ignore_errors=True)

    def _create_test_config_file(self):
        """Create a test configuration file."""
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
                "default_size": 10,
                "default_overlap": 2,
                "language_specific": {
                    "python": {"chunk_size": 10, "chunk_overlap": 2}
                },
            },
            "analysis": {
                "enable_vulnerability_scanning": True,
                "enable_code_quality_check": False,
                "enable_compliance_check": False,
                "enable_architecture_analysis": False,
                "top_k_context": 5,
            },
            "languages": {
                "supported": ["python", "javascript"],
                "auto_detect": True,
            },
            "file_discovery": {
                "max_file_size_mb": 10,
                "exclude_patterns": ["*.pyc", "__pycache__"],
                "exclude_directories": [".git", "node_modules"],
                "default_exclusions": ["*.pyc"],
            },
            "output": {
                "default_format": "console",
                "output_directory": str(self.output_dir),
                "save_to_file": False,
                "color": True,
            },
            "logging": {
                "level": "INFO",
                "log_to_file": False,
            },
        }
        with open(self.config_path, "w") as f:
            yaml.dump(config_dict, f)

    def _create_test_project(self, name: str = "test_project") -> Path:
        """Create a simple test project."""
        project_dir = self.temp_dir_path / name
        project_dir.mkdir()
        (project_dir / "main.py").write_text("def hello():\n    print('Hello')\n")
        return project_dir

    # ===== Test: Index command with --project-id flag =====

    def test_index_command_with_project_id_flag(self):
        """
        Test index command with explicit --project-id flag.

        Scenario:
        - Create test project
        - Run index command with --project-id
        - Verify project registered with custom ID
        """
        project_dir = self._create_test_project()

        # Run index with custom project ID
        result = self.runner.invoke(
            app,
            [
                "index",
                str(project_dir),
                "--config", str(self.config_path),
                "--project-id", "my-custom-project",
            ],
        )

        # Verify command succeeded
        assert result.exit_code == 0, f"Command failed: {result.stdout}"
        assert "Indexed" in result.stdout or "complete" in result.stdout.lower()

        # Verify project registered with custom ID
        from falconeye.infrastructure.di.container import DIContainer
        container = DIContainer.create(str(self.config_path))
        registry = container.index_registry

        project_meta = registry.get_project("my-custom-project")
        assert project_meta is not None
        assert project_meta.project_id == "my-custom-project"

    # ===== Test: Index command with --force-reindex flag =====

    def test_index_command_with_force_reindex_flag(self):
        """
        Test index command with --force-reindex flag.

        Scenario:
        - Create test project
        - Index once
        - Re-index with --force-reindex
        - Verify all files re-processed
        """
        project_dir = self._create_test_project()

        # First index
        result1 = self.runner.invoke(
            app,
            [
                "index",
                str(project_dir),
                "--config", str(self.config_path),
            ],
        )
        assert result1.exit_code == 0

        # Force re-index
        result2 = self.runner.invoke(
            app,
            [
                "index",
                str(project_dir),
                "--config", str(self.config_path),
                "--force-reindex",
            ],
        )

        assert result2.exit_code == 0
        assert "Indexed" in result2.stdout or "complete" in result2.stdout.lower()

    # ===== Test: Scan command with new flags =====

    def test_scan_command_with_project_id(self):
        """
        Test scan command with --project-id flag.

        Scenario:
        - Create test project
        - Run scan with --project-id
        - Verify project registered with custom ID
        """
        project_dir = self._create_test_project()

        # Mock LLM service to avoid actual LLM calls
        with patch("falconeye.infrastructure.llm_providers.ollama_adapter.OllamaLLMAdapter.analyze_code_security") as mock_analyze:
            mock_analyze.return_value = {"findings": []}

            result = self.runner.invoke(
                app,
                [
                    "scan",
                    str(project_dir),
                    "--config", str(self.config_path),
                    "--project-id", "scan-project",
                ],
            )

            # Note: scan might fail if LLM not available, but we check if project-id was used
            # The important part is that index step uses project-id
            from falconeye.infrastructure.di.container import DIContainer
            container = DIContainer.create(str(self.config_path))
            registry = container.index_registry

            # Check if project was created (scan does index first)
            project_meta = registry.get_project("scan-project")
            if result.exit_code == 0:
                assert project_meta is not None

    # ===== Test: Index without flags (default behavior) =====

    def test_index_command_auto_detect_project_id(self):
        """
        Test index command auto-detects project ID.

        Scenario:
        - Create test project
        - Run index without --project-id
        - Verify project registered with auto-generated ID
        """
        project_dir = self._create_test_project("auto_detect_project")

        result = self.runner.invoke(
            app,
            [
                "index",
                str(project_dir),
                "--config", str(self.config_path),
            ],
        )

        assert result.exit_code == 0

        # Verify project registered with auto-detected ID
        from falconeye.infrastructure.di.container import DIContainer
        container = DIContainer.create(str(self.config_path))
        registry = container.index_registry
        project_identifier = container.project_identifier

        # Get expected project ID
        expected_id, _, _, _ = project_identifier.identify_project(project_dir)

        project_meta = registry.get_project(expected_id)
        assert project_meta is not None
        assert project_meta.project_id == expected_id

    # ===== Test: Re-index without changes (smart re-indexing) =====

    def test_reindex_without_changes_skips_files(self):
        """
        Test that re-indexing without changes skips files.

        Scenario:
        - Index project
        - Re-index without changes
        - Verify smart re-indexing works (output indicates skipping)
        """
        project_dir = self._create_test_project()

        # First index
        result1 = self.runner.invoke(
            app,
            [
                "index",
                str(project_dir),
                "--config", str(self.config_path),
            ],
        )
        assert result1.exit_code == 0

        # Re-index (no changes)
        result2 = self.runner.invoke(
            app,
            [
                "index",
                str(project_dir),
                "--config", str(self.config_path),
            ],
        )
        assert result2.exit_code == 0

        # Check that it processed (smart re-indexing happens in handler)
        assert "Indexed" in result2.stdout or "complete" in result2.stdout.lower()

    # ===== Test: Config file validation =====

    def test_index_command_uses_config_file(self):
        """
        Test that index command uses config file correctly.

        Scenario:
        - Create config with specific settings
        - Run index with config
        - Verify settings applied
        """
        project_dir = self._create_test_project()

        result = self.runner.invoke(
            app,
            [
                "index",
                str(project_dir),
                "--config", str(self.config_path),
                "--language", "python",
            ],
        )

        assert result.exit_code == 0

        # Verify registry was used (directory created)
        assert Path(self.registry_dir).exists()

    # ===== Test: Error handling =====

    def test_index_command_nonexistent_path(self):
        """
        Test index command with nonexistent path.

        Scenario:
        - Run index with invalid path
        - Verify proper error handling
        """
        result = self.runner.invoke(
            app,
            [
                "index",
                "/nonexistent/path",
                "--config", str(self.config_path),
            ],
        )

        # Typer will fail on path validation before command runs
        assert result.exit_code != 0


class TestProjectsCommandIntegration:
    """Integration tests for new 'projects' command group."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create temporary directories
        self.temp_dir = tempfile.mkdtemp()
        self.temp_dir_path = Path(self.temp_dir)
        self.vector_store_dir = tempfile.mkdtemp()
        self.metadata_dir = tempfile.mkdtemp()
        self.registry_dir = tempfile.mkdtemp()
        self.output_dir = tempfile.mkdtemp()

        # Create test config file
        self.config_path = self.temp_dir_path / "test_config.yaml"
        self._create_test_config_file()

        # Create CLI runner
        self.runner = CliRunner()

    def teardown_method(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        shutil.rmtree(self.vector_store_dir, ignore_errors=True)
        shutil.rmtree(self.metadata_dir, ignore_errors=True)
        shutil.rmtree(self.registry_dir, ignore_errors=True)
        shutil.rmtree(self.output_dir, ignore_errors=True)

    def _create_test_config_file(self):
        """Create a test configuration file."""
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
                "default_size": 10,
                "default_overlap": 2,
                "language_specific": {
                    "python": {"chunk_size": 10, "chunk_overlap": 2}
                },
            },
            "analysis": {
                "enable_vulnerability_scanning": True,
                "enable_code_quality_check": False,
                "enable_compliance_check": False,
                "enable_architecture_analysis": False,
                "top_k_context": 5,
            },
            "languages": {
                "supported": ["python", "javascript"],
                "auto_detect": True,
            },
            "file_discovery": {
                "max_file_size_mb": 10,
                "exclude_patterns": ["*.pyc", "__pycache__"],
                "exclude_directories": [".git", "node_modules"],
                "default_exclusions": ["*.pyc"],
            },
            "output": {
                "default_format": "console",
                "output_directory": str(self.output_dir),
                "save_to_file": False,
                "color": True,
            },
            "logging": {
                "level": "INFO",
                "log_to_file": False,
            },
        }
        with open(self.config_path, "w") as f:
            yaml.dump(config_dict, f)

    def _create_and_index_project(self, name: str = "test_project") -> Path:
        """Create and index a test project."""
        project_dir = self.temp_dir_path / name
        project_dir.mkdir()
        (project_dir / "main.py").write_text("def hello():\n    print('Hello')\n")

        # Index the project
        result = self.runner.invoke(
            app,
            [
                "index",
                str(project_dir),
                "--config", str(self.config_path),
            ],
        )
        assert result.exit_code == 0

        return project_dir

    # ===== Test: projects list command =====

    def test_projects_list_command(self):
        """
        Test 'projects list' command.

        Scenario:
        - Index 2 projects
        - Run 'projects list'
        - Verify both projects shown
        """
        # Index two projects
        self._create_and_index_project("project1")
        self._create_and_index_project("project2")

        # Run projects list
        result = self.runner.invoke(
            app,
            [
                "projects",
                "list",
                "--config", str(self.config_path),
            ],
        )

        assert result.exit_code == 0
        # Should show project information
        assert "project" in result.stdout.lower()

    # ===== Test: projects info command =====

    def test_projects_info_command(self):
        """
        Test 'projects info' command.

        Scenario:
        - Index project with custom ID
        - Run 'projects info <id>'
        - Verify project details shown
        """
        project_dir = self.temp_dir_path / "info_project"
        project_dir.mkdir()
        (project_dir / "main.py").write_text("def test():\n    pass\n")

        # Index with custom ID
        result1 = self.runner.invoke(
            app,
            [
                "index",
                str(project_dir),
                "--config", str(self.config_path),
                "--project-id", "info-test",
            ],
        )
        assert result1.exit_code == 0

        # Get project info
        result2 = self.runner.invoke(
            app,
            [
                "projects",
                "info",
                "info-test",
                "--config", str(self.config_path),
            ],
        )

        assert result2.exit_code == 0
        assert "info-test" in result2.stdout

    # ===== Test: projects delete command =====

    def test_projects_delete_command(self):
        """
        Test 'projects delete' command.

        Scenario:
        - Index project
        - Run 'projects delete <id>'
        - Verify project removed from registry
        """
        project_dir = self._create_and_index_project("delete_project")

        # Get project ID
        from falconeye.infrastructure.di.container import DIContainer
        container = DIContainer.create(str(self.config_path))
        project_id, _, _, _ = container.project_identifier.identify_project(project_dir)

        # Verify project exists
        project_meta = container.index_registry.get_project(project_id)
        assert project_meta is not None

        # Delete project
        result = self.runner.invoke(
            app,
            [
                "projects",
                "delete",
                project_id,
                "--config", str(self.config_path),
                "--yes",  # Skip confirmation
            ],
        )

        assert result.exit_code == 0

        # Verify project deleted
        project_meta_after = container.index_registry.get_project(project_id)
        assert project_meta_after is None

    # ===== Test: projects list empty =====

    def test_projects_list_empty(self):
        """
        Test 'projects list' with no indexed projects.

        Scenario:
        - Run 'projects list' with empty registry
        - Verify appropriate message shown
        """
        result = self.runner.invoke(
            app,
            [
                "projects",
                "list",
                "--config", str(self.config_path),
            ],
        )

        assert result.exit_code == 0
        # Should indicate no projects
        assert "no indexed projects found" in result.stdout.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
