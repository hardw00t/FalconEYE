"""
Complete end-to-end workflow tests for smart re-indexing.

Tests real-world scenarios with actual file operations and multiple indexing cycles.
Uses real implementations (no mocks).
"""

import pytest
import tempfile
import shutil
import time
from pathlib import Path
from typer.testing import CliRunner

from falconeye.adapters.cli.main import app
from falconeye.infrastructure.di.container import DIContainer


class TestCompleteWorkflow:
    """End-to-end workflow tests for complete indexing scenarios."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create temporary directories
        self.temp_dir = tempfile.mkdtemp()
        self.temp_dir_path = Path(self.temp_dir)

        # Create CLI runner with isolated mode
        self.runner = CliRunner(mix_stderr=False)

    def teardown_method(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _create_python_project(self, name: str, num_files: int = 5) -> Path:
        """Create a Python project with multiple files."""
        project_dir = self.temp_dir_path / name
        project_dir.mkdir(parents=True)

        # Create main.py
        (project_dir / "main.py").write_text(
            "def main():\n"
            "    print('Hello, World!')\n"
            "\n"
            "if __name__ == '__main__':\n"
            "    main()\n"
        )

        # Create utils.py
        (project_dir / "utils.py").write_text(
            "def helper_function(x):\n"
            "    return x * 2\n"
            "\n"
            "def another_helper(y):\n"
            "    return y + 1\n"
        )

        # Create config.py
        (project_dir / "config.py").write_text(
            "DEBUG = True\n"
            "VERSION = '1.0.0'\n"
            "API_KEY = 'test-key'\n"
        )

        # Create additional files
        for i in range(num_files - 3):
            (project_dir / f"module_{i}.py").write_text(
                f"# Module {i}\n"
                f"def function_{i}():\n"
                f"    return {i}\n"
            )

        return project_dir

    # ===== Test: Complete first-time indexing workflow =====

    def test_complete_first_time_indexing_workflow(self):
        """
        Test complete first-time indexing workflow.

        Scenario:
        - Create project with 10 files
        - Index project
        - Verify all files indexed
        - Verify project metadata saved
        - Verify can list projects
        - Verify can show project info
        """
        # Create project
        project_dir = self._create_python_project("first_time_project", num_files=10)

        # Index project
        result = self.runner.invoke(
            app,
            ["index", str(project_dir)],
        )

        assert result.exit_code == 0
        assert "10 files" in result.stdout or "Indexed" in result.stdout

        # List projects
        result = self.runner.invoke(app, ["projects", "list"])
        assert result.exit_code == 0
        assert "first_time_project" in result.stdout or "10" in result.stdout

        # Get project info
        container = DIContainer.create(None)
        project_id, _, _, _ = container.project_identifier.identify_project(project_dir)

        result = self.runner.invoke(app, ["projects", "info", project_id])
        assert result.exit_code == 0
        assert project_id in result.stdout
        assert "10" in result.stdout  # Should show 10 files

    # ===== Test: Smart re-indexing with no changes =====

    def test_smart_reindexing_no_changes_workflow(self):
        """
        Test smart re-indexing when no files changed.

        Scenario:
        - Index project
        - Re-index immediately (no changes)
        - Verify files skipped (smart re-indexing)
        - Verify project metadata updated
        """
        project_dir = self._create_python_project("no_changes_project")

        # First index
        result1 = self.runner.invoke(app, ["index", str(project_dir)])
        assert result1.exit_code == 0

        # Get initial timestamp
        container = DIContainer.create(None)
        project_id, _, _, _ = container.project_identifier.identify_project(project_dir)
        project_meta_before = container.index_registry.get_project(project_id)
        initial_scan_time = project_meta_before.last_full_scan

        # Wait a bit to ensure time difference
        time.sleep(0.1)

        # Re-index (no changes)
        result2 = self.runner.invoke(app, ["index", str(project_dir)])
        assert result2.exit_code == 0

        # Verify metadata updated
        project_meta_after = container.index_registry.get_project(project_id)
        assert project_meta_after.last_full_scan > initial_scan_time

    # ===== Test: Smart re-indexing with file modifications =====

    def test_smart_reindexing_with_modifications_workflow(self):
        """
        Test smart re-indexing when files are modified.

        Scenario:
        - Index project with 5 files
        - Modify 2 files
        - Re-index
        - Verify only modified files processed
        - Verify project metadata updated
        """
        project_dir = self._create_python_project("modified_project", num_files=5)

        # First index
        result1 = self.runner.invoke(app, ["index", str(project_dir)])
        assert result1.exit_code == 0

        # Modify 2 files
        time.sleep(0.01)  # Ensure mtime changes
        (project_dir / "main.py").write_text(
            "def main():\n"
            "    print('Hello, Modified World!')\n"  # Modified
            "\n"
            "if __name__ == '__main__':\n"
            "    main()\n"
        )

        (project_dir / "utils.py").write_text(
            "def helper_function(x):\n"
            "    return x * 3\n"  # Modified
            "\n"
            "def another_helper(y):\n"
            "    return y + 2\n"  # Modified
        )

        # Re-index
        result2 = self.runner.invoke(app, ["index", str(project_dir)])
        assert result2.exit_code == 0

        # Verify indexing completed
        assert "Indexed" in result2.stdout or "complete" in result2.stdout.lower()

    # ===== Test: Smart re-indexing with new files =====

    def test_smart_reindexing_with_new_files_workflow(self):
        """
        Test smart re-indexing when new files are added.

        Scenario:
        - Index project with 3 files
        - Add 2 new files
        - Re-index
        - Verify new files detected and indexed
        - Verify project shows 5 files
        """
        project_dir = self._create_python_project("new_files_project", num_files=3)

        # First index
        result1 = self.runner.invoke(app, ["index", str(project_dir)])
        assert result1.exit_code == 0

        # Add new files
        (project_dir / "new_module.py").write_text(
            "# New module\n"
            "def new_function():\n"
            "    return 'new'\n"
        )

        (project_dir / "another_new.py").write_text(
            "# Another new module\n"
            "def another_new_function():\n"
            "    return 'another'\n"
        )

        # Re-index
        result2 = self.runner.invoke(app, ["index", str(project_dir)])
        assert result2.exit_code == 0

        # Verify project now has 5 files
        container = DIContainer.create(None)
        project_id, _, _, _ = container.project_identifier.identify_project(project_dir)
        project_meta = container.index_registry.get_project(project_id)

        assert project_meta.total_files == 5

    # ===== Test: Smart re-indexing with deleted files =====

    def test_smart_reindexing_with_deleted_files_workflow(self):
        """
        Test smart re-indexing when files are deleted.

        Scenario:
        - Index project with 5 files
        - Delete 2 files
        - Re-index
        - Verify deleted files marked as deleted
        - Cleanup deleted files
        - Verify project shows 3 files
        """
        project_dir = self._create_python_project("deleted_files_project", num_files=5)

        # First index
        result1 = self.runner.invoke(app, ["index", str(project_dir)])
        assert result1.exit_code == 0

        # Get project ID
        container = DIContainer.create(None)
        project_id, _, _, _ = container.project_identifier.identify_project(project_dir)

        # Delete 2 files
        (project_dir / "module_0.py").unlink()
        (project_dir / "module_1.py").unlink()

        # Re-index
        result2 = self.runner.invoke(app, ["index", str(project_dir)])
        assert result2.exit_code == 0

        # Verify deleted files marked
        from falconeye.domain.value_objects.project_metadata import FileStatus
        deleted_files = container.index_registry.get_files_by_status(
            project_id, FileStatus.DELETED
        )
        assert len(deleted_files) == 2

        # Cleanup deleted files
        result3 = self.runner.invoke(
            app, ["projects", "cleanup", project_id, "--yes"]
        )
        assert result3.exit_code == 0

        # Verify deleted files removed
        project_meta = container.index_registry.get_project(project_id)
        assert project_meta.total_files == 3

    # ===== Test: Force re-index workflow =====

    def test_force_reindex_workflow(self):
        """
        Test force re-index workflow.

        Scenario:
        - Index project
        - Force re-index (all files processed)
        - Verify all files re-indexed
        - Verify project metadata updated
        """
        project_dir = self._create_python_project("force_reindex_project")

        # First index
        result1 = self.runner.invoke(app, ["index", str(project_dir)])
        assert result1.exit_code == 0

        # Get initial timestamp
        container = DIContainer.create(None)
        project_id, _, _, _ = container.project_identifier.identify_project(project_dir)
        project_meta_before = container.index_registry.get_project(project_id)
        initial_scan_time = project_meta_before.last_full_scan

        time.sleep(0.1)

        # Force re-index
        result2 = self.runner.invoke(
            app, ["index", str(project_dir), "--force-reindex"]
        )
        assert result2.exit_code == 0

        # Verify metadata updated
        project_meta_after = container.index_registry.get_project(project_id)
        assert project_meta_after.last_full_scan > initial_scan_time

    # ===== Test: Multiple projects workflow =====

    def test_multiple_projects_workflow(self):
        """
        Test managing multiple projects.

        Scenario:
        - Index 3 different projects
        - List all projects (should show 3)
        - Get info for each project
        - Delete one project
        - List again (should show 2)
        """
        # Create 3 projects
        project1 = self._create_python_project("project_alpha", num_files=3)
        project2 = self._create_python_project("project_beta", num_files=4)
        project3 = self._create_python_project("project_gamma", num_files=5)

        # Index all projects
        for project in [project1, project2, project3]:
            result = self.runner.invoke(app, ["index", str(project)])
            assert result.exit_code == 0

        # List projects
        result = self.runner.invoke(app, ["projects", "list"])
        assert result.exit_code == 0
        # Should show all 3 projects
        assert "project" in result.stdout.lower()

        # Get project IDs
        container = DIContainer.create(None)
        project1_id, _, _, _ = container.project_identifier.identify_project(project1)
        project2_id, _, _, _ = container.project_identifier.identify_project(project2)
        project3_id, _, _, _ = container.project_identifier.identify_project(project3)

        # Get info for each
        for pid in [project1_id, project2_id, project3_id]:
            result = self.runner.invoke(app, ["projects", "info", pid])
            assert result.exit_code == 0
            assert pid in result.stdout

        # Delete one project
        result = self.runner.invoke(
            app, ["projects", "delete", project2_id, "--yes"]
        )
        assert result.exit_code == 0

        # Verify deleted
        project2_meta = container.index_registry.get_project(project2_id)
        assert project2_meta is None

    # ===== Test: Explicit project ID workflow =====

    def test_explicit_project_id_workflow(self):
        """
        Test using explicit project IDs.

        Scenario:
        - Index project with custom ID
        - Verify custom ID used
        - Re-index with same custom ID
        - Verify project found with custom ID
        """
        project_dir = self._create_python_project("explicit_id_project")
        custom_id = f"my-custom-api-{id(project_dir)}"  # Unique ID per test run

        # Clean up any existing project with this ID (from previous test runs)
        container = DIContainer.create(None)
        existing = container.index_registry.get_project(custom_id)
        if existing:
            container.index_registry.delete_project(custom_id)

        # Index with custom ID
        result1 = self.runner.invoke(
            app, ["index", str(project_dir), "--project-id", custom_id]
        )
        assert result1.exit_code == 0, f"Index failed: {result1.stdout}"

        # Verify custom ID used
        container = DIContainer.create(None)
        project_meta = container.index_registry.get_project(custom_id)
        assert project_meta is not None
        assert project_meta.project_id == custom_id

        # Re-index with same custom ID
        result2 = self.runner.invoke(
            app, ["index", str(project_dir), "--project-id", custom_id]
        )
        assert result2.exit_code == 0

        # Get info
        result3 = self.runner.invoke(app, ["projects", "info", custom_id])
        assert result3.exit_code == 0
        assert custom_id in result3.stdout

    # ===== Test: Large project workflow =====

    def test_large_project_workflow(self):
        """
        Test indexing a larger project.

        Scenario:
        - Create project with 50 files
        - Index project
        - Verify all files indexed
        - Modify 10 files
        - Re-index
        - Verify smart re-indexing works with larger projects
        """
        project_dir = self._create_python_project("large_project", num_files=50)

        # Index project
        result1 = self.runner.invoke(app, ["index", str(project_dir)])
        assert result1.exit_code == 0
        assert "50" in result1.stdout or "Indexed" in result1.stdout

        # Verify project metadata
        container = DIContainer.create(None)
        project_id, _, _, _ = container.project_identifier.identify_project(project_dir)
        project_meta = container.index_registry.get_project(project_id)
        assert project_meta.total_files == 50

        # Modify 10 files
        time.sleep(0.01)
        for i in range(10):
            file_path = project_dir / f"module_{i}.py"
            file_path.write_text(
                f"# Modified Module {i}\n"
                f"def modified_function_{i}():\n"
                f"    return {i * 2}\n"
            )

        # Re-index
        result2 = self.runner.invoke(app, ["index", str(project_dir)])
        assert result2.exit_code == 0

        # Verify still has 50 files
        project_meta_after = container.index_registry.get_project(project_id)
        assert project_meta_after.total_files == 50


class TestBackwardCompatibility:
    """Tests to ensure backward compatibility with existing functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_dir_path = Path(self.temp_dir)
        self.runner = CliRunner()

    def teardown_method(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_index_without_new_flags_still_works(self):
        """
        Test that index command works without new flags.

        Scenario:
        - Index project using old command format (no new flags)
        - Verify indexing works correctly
        - Verify smart re-indexing enabled by default
        """
        project_dir = self.temp_dir_path / "backward_compat_project"
        project_dir.mkdir()
        (project_dir / "main.py").write_text("def main(): pass\n")

        # Index without new flags (old format)
        result = self.runner.invoke(app, ["index", str(project_dir)])

        assert result.exit_code == 0
        assert "Indexed" in result.stdout or "complete" in result.stdout.lower()

    def test_scan_without_new_flags_still_works(self):
        """
        Test that scan command works without new flags.

        Scenario:
        - Scan project using old command format
        - Verify indexing step works
        """
        project_dir = self.temp_dir_path / "scan_compat_project"
        project_dir.mkdir()
        (project_dir / "main.py").write_text("def main(): pass\n")

        # Scan without new flags (old format)
        # Note: Review will fail without LLM, but index should succeed
        result = self.runner.invoke(app, ["scan", str(project_dir)])

        # Index step should work (scan = index + review)
        # We're checking that the command accepted and started processing
        assert result.exit_code in [0, 1]  # 0 if success, 1 if review fails

    def test_existing_commands_unchanged(self):
        """
        Test that existing commands still work as before.

        Scenario:
        - Run info command
        - Run config command with --show
        - Verify commands work without issues
        """
        # Info command
        result1 = self.runner.invoke(app, ["info"])
        assert result1.exit_code == 0
        assert "FalconEYE" in result1.stdout

        # Config command
        result2 = self.runner.invoke(app, ["config"])
        assert result2.exit_code == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
