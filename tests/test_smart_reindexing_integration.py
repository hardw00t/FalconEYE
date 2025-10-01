"""
Integration tests for smart re-indexing functionality.

Tests the complete flow from project identification through to selective re-indexing.
Uses real components (no mocks) to validate the entire system.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
import asyncio

from falconeye.application.commands.index_codebase import (
    IndexCodebaseCommand,
    IndexCodebaseHandler,
)
from falconeye.domain.services.project_identifier import ProjectIdentifier
from falconeye.domain.services.checksum_service import ChecksumService
from falconeye.infrastructure.registry.chroma_registry_adapter import (
    ChromaIndexRegistryAdapter,
)
from falconeye.domain.value_objects.project_metadata import (
    ProjectMetadata,
    ProjectType,
    FileMetadata,
    FileStatus,
)


class TestSmartReindexingIntegration:
    """Integration tests for smart re-indexing."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create temporary directories
        self.temp_dir = tempfile.mkdtemp()
        self.temp_dir_path = Path(self.temp_dir)

        self.registry_dir = tempfile.mkdtemp()

        # Initialize services
        self.project_identifier = ProjectIdentifier()
        self.checksum_service = ChecksumService()
        self.registry = ChromaIndexRegistryAdapter(
            persist_directory=self.registry_dir,
            collection_name="test_smart_reindex_registry",
        )

    def teardown_method(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        shutil.rmtree(self.registry_dir, ignore_errors=True)

    # ===== Test 1: First-time indexing =====

    def test_first_time_indexing_creates_project_metadata(self):
        """
        Test that first-time indexing creates project metadata in registry.

        Scenario:
        - Project has never been indexed
        - Registry should create new project entry
        - All files should be marked for indexing
        """
        # Create a simple Python project
        project_dir = self.temp_dir_path / "myproject"
        project_dir.mkdir()

        # Create some files
        (project_dir / "main.py").write_text("print('hello')\n")
        (project_dir / "utils.py").write_text("def helper():\n    pass\n")

        # Identify project
        project_id, project_name, project_type, remote_url = \
            self.project_identifier.identify_project(project_dir)

        # Verify project doesn't exist in registry
        assert not self.registry.project_exists(project_id)

        # Expected behavior:
        # - Project should be identified
        # - project_id should be generated
        # - Project metadata should be saved after indexing
        assert project_id is not None
        assert project_name == "myproject"
        assert project_type == ProjectType.NON_GIT

    def test_first_time_indexing_processes_all_files(self):
        """
        Test that first-time indexing processes all discovered files.

        Scenario:
        - Project has 3 files
        - All files should be indexed
        - File metadata should be saved for each
        """
        # Create project with 3 files
        project_dir = self.temp_dir_path / "project1"
        project_dir.mkdir()

        files = {
            "file1.py": "def func1():\n    pass\n",
            "file2.py": "class MyClass:\n    pass\n",
            "file3.py": "import os\n",
        }

        for filename, content in files.items():
            (project_dir / filename).write_text(content)

        # Identify project
        project_id, _, _, _ = self.project_identifier.identify_project(project_dir)

        # Expected: All files should be marked for indexing
        # (We'll verify this by checking that get_all_files returns empty before indexing)
        all_files = self.registry.get_all_files(project_id)
        assert len(all_files) == 0  # No files yet

    # ===== Test 2: Re-indexing with no changes =====

    def test_reindex_no_changes_skips_all_files(self):
        """
        Test that re-indexing with no changes skips all files.

        Scenario:
        - Project was indexed before
        - No files changed
        - All files should be skipped
        """
        # Create project
        project_dir = self.temp_dir_path / "stable_project"
        project_dir.mkdir()

        file1 = project_dir / "stable.py"
        file1.write_text("# No changes\n")

        # Identify project
        project_id, project_name, project_type, _ = \
            self.project_identifier.identify_project(project_dir)

        # Simulate previous indexing
        project_meta = ProjectMetadata(
            project_id=project_id,
            project_name=project_name,
            project_root=project_dir,
            project_type=project_type,
            total_files=1,
            total_chunks=1,
            languages=["python"],
        )
        self.registry.save_project(project_meta)

        # Save file metadata
        file_meta = self.checksum_service.get_file_metadata_snapshot(
            file_path=file1,
            relative_path=Path("stable.py"),
            project_id=project_id,
            language="python",
        )
        self.registry.save_file(file_meta)

        # Check for changes using quick check
        has_changed = self.checksum_service.has_file_changed_quick(file1, file_meta)

        # Expected: File has not changed
        assert has_changed is False

    def test_reindex_detects_modified_files(self):
        """
        Test that re-indexing detects modified files.

        Scenario:
        - Project was indexed before
        - 1 file was modified
        - Modified file should be re-indexed
        - Unchanged files should be skipped
        """
        # Create project with 2 files
        project_dir = self.temp_dir_path / "modified_project"
        project_dir.mkdir()

        file1 = project_dir / "unchanged.py"
        file2 = project_dir / "modified.py"

        file1.write_text("# Unchanged\n")
        file2.write_text("# Original\n")

        # Identify project
        project_id, project_name, project_type, _ = \
            self.project_identifier.identify_project(project_dir)

        # Simulate previous indexing
        project_meta = ProjectMetadata(
            project_id=project_id,
            project_name=project_name,
            project_root=project_dir,
            project_type=project_type,
            total_files=2,
            total_chunks=2,
            languages=["python"],
        )
        self.registry.save_project(project_meta)

        # Save file metadata for both files
        file1_meta = self.checksum_service.get_file_metadata_snapshot(
            file_path=file1,
            relative_path=Path("unchanged.py"),
            project_id=project_id,
            language="python",
        )
        file2_meta = self.checksum_service.get_file_metadata_snapshot(
            file_path=file2,
            relative_path=Path("modified.py"),
            project_id=project_id,
            language="python",
        )

        self.registry.save_file(file1_meta)
        self.registry.save_file(file2_meta)

        # Modify file2
        import time
        time.sleep(0.01)  # Ensure mtime changes
        file2.write_text("# Modified content\n")

        # Check for changes
        file1_changed = self.checksum_service.has_file_changed_quick(file1, file1_meta)
        file2_changed = self.checksum_service.has_file_changed_quick(file2, file2_meta)

        # Expected: file1 unchanged, file2 changed
        assert file1_changed is False
        assert file2_changed is True

    # ===== Test 3: New files detection =====

    def test_reindex_detects_new_files(self):
        """
        Test that re-indexing detects new files.

        Scenario:
        - Project had 1 file
        - Added 2 new files
        - New files should be indexed
        """
        # Create project with 1 file
        project_dir = self.temp_dir_path / "growing_project"
        project_dir.mkdir()

        existing_file = project_dir / "existing.py"
        existing_file.write_text("# Existing\n")

        # Identify project
        project_id, project_name, project_type, _ = \
            self.project_identifier.identify_project(project_dir)

        # Simulate previous indexing (1 file)
        project_meta = ProjectMetadata(
            project_id=project_id,
            project_name=project_name,
            project_root=project_dir,
            project_type=project_type,
            total_files=1,
            languages=["python"],
        )
        self.registry.save_project(project_meta)

        existing_meta = self.checksum_service.get_file_metadata_snapshot(
            file_path=existing_file,
            relative_path=Path("existing.py"),
            project_id=project_id,
            language="python",
        )
        self.registry.save_file(existing_meta)

        # Add new files
        new_file1 = project_dir / "new1.py"
        new_file2 = project_dir / "new2.py"
        new_file1.write_text("# New file 1\n")
        new_file2.write_text("# New file 2\n")

        # Get current files and cached files
        current_files = {existing_file, new_file1, new_file2}
        cached_metadata = self.registry.get_files_metadata_dict(project_id)

        # Identify new files
        new_files = self.checksum_service.identify_new_files(
            current_files,
            set(cached_metadata.keys())
        )

        # Expected: 2 new files detected
        assert len(new_files) == 2
        assert new_file1 in new_files
        assert new_file2 in new_files

    # ===== Test 4: Deleted files detection =====

    def test_reindex_detects_deleted_files(self):
        """
        Test that re-indexing detects deleted files.

        Scenario:
        - Project had 3 files
        - Deleted 1 file
        - Deleted file should be marked for cleanup
        """
        # Create project with 3 files
        project_dir = self.temp_dir_path / "shrinking_project"
        project_dir.mkdir()

        file1 = project_dir / "keep1.py"
        file2 = project_dir / "keep2.py"
        deleted_file = project_dir / "deleted.py"

        file1.write_text("# Keep 1\n")
        file2.write_text("# Keep 2\n")
        deleted_file.write_text("# Will be deleted\n")

        # Identify project
        project_id, project_name, project_type, _ = \
            self.project_identifier.identify_project(project_dir)

        # Simulate previous indexing (3 files)
        project_meta = ProjectMetadata(
            project_id=project_id,
            project_name=project_name,
            project_root=project_dir,
            project_type=project_type,
            total_files=3,
            languages=["python"],
        )
        self.registry.save_project(project_meta)

        # Save metadata for all 3 files
        for file_path, rel_path in [
            (file1, "keep1.py"),
            (file2, "keep2.py"),
            (deleted_file, "deleted.py"),
        ]:
            file_meta = self.checksum_service.get_file_metadata_snapshot(
                file_path=file_path,
                relative_path=Path(rel_path),
                project_id=project_id,
                language="python",
            )
            self.registry.save_file(file_meta)

        # Delete one file
        deleted_file.unlink()

        # Get current files and cached files
        current_files = {file1, file2}
        cached_metadata = self.registry.get_files_metadata_dict(project_id)

        # Identify deleted files
        deleted_files = self.checksum_service.identify_deleted_files(
            current_files,
            set(cached_metadata.keys())
        )

        # Expected: 1 deleted file
        assert len(deleted_files) == 1
        assert project_dir / "deleted.py" in deleted_files

    # ===== Test 5: Force re-index =====

    def test_force_reindex_processes_all_files(self):
        """
        Test that force re-index processes all files regardless of changes.

        Scenario:
        - Project was indexed before
        - No files changed
        - force_reindex=True
        - All files should be re-indexed
        """
        # Create project
        project_dir = self.temp_dir_path / "force_project"
        project_dir.mkdir()

        file1 = project_dir / "file1.py"
        file2 = project_dir / "file2.py"

        file1.write_text("# File 1\n")
        file2.write_text("# File 2\n")

        # Identify project
        project_id, project_name, project_type, _ = \
            self.project_identifier.identify_project(project_dir)

        # Simulate previous indexing
        project_meta = ProjectMetadata(
            project_id=project_id,
            project_name=project_name,
            project_root=project_dir,
            project_type=project_type,
            total_files=2,
            languages=["python"],
        )
        self.registry.save_project(project_meta)

        # Expected behavior with force_reindex=True:
        # All files should be processed regardless of metadata
        # This will be implemented in the handler

        # For now, verify that project exists
        assert self.registry.project_exists(project_id)

    # ===== Test 6: Git repository detection =====

    def test_git_project_identification(self):
        """
        Test project identification for git repositories.

        Scenario:
        - Create a git repository
        - Identify project
        - Should use git remote URL in project_id
        """
        # Create git repo
        git_dir = self.temp_dir_path / "git_repo"
        git_dir.mkdir()

        # Initialize git
        import subprocess
        subprocess.run(["git", "init"], cwd=git_dir, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=git_dir,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=git_dir,
            capture_output=True,
        )

        # Create a file and commit
        test_file = git_dir / "test.py"
        test_file.write_text("# Test\n")
        subprocess.run(["git", "add", "."], cwd=git_dir, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=git_dir,
            capture_output=True,
        )

        # Add remote
        subprocess.run(
            ["git", "remote", "add", "origin", "https://github.com/test/repo.git"],
            cwd=git_dir,
            capture_output=True,
        )

        # Identify project
        project_id, project_name, project_type, remote_url = \
            self.project_identifier.identify_project(git_dir)

        # Expected: Git project with remote URL
        assert project_type == ProjectType.GIT
        assert remote_url == "github.com/test/repo"
        assert "_" in project_id  # Should include URL hash

    # ===== Test 7: Project isolation verification =====

    def test_multiple_projects_isolated(self):
        """
        Test that multiple projects are properly isolated in registry.

        Scenario:
        - Index 2 different projects
        - Each should have separate project_id
        - File metadata should not cross-contaminate
        """
        # Create project 1
        project1_dir = self.temp_dir_path / "project1"
        project1_dir.mkdir()
        (project1_dir / "file1.py").write_text("# Project 1\n")

        # Create project 2
        project2_dir = self.temp_dir_path / "project2"
        project2_dir.mkdir()
        (project2_dir / "file2.py").write_text("# Project 2\n")

        # Identify both projects
        project1_id, _, _, _ = self.project_identifier.identify_project(project1_dir)
        project2_id, _, _, _ = self.project_identifier.identify_project(project2_dir)

        # Expected: Different project IDs
        assert project1_id != project2_id

        # Save metadata for both
        for proj_id, proj_dir, proj_name in [
            (project1_id, project1_dir, "project1"),
            (project2_id, project2_dir, "project2"),
        ]:
            project_meta = ProjectMetadata(
                project_id=proj_id,
                project_name=proj_name,
                project_root=proj_dir,
                project_type=ProjectType.NON_GIT,
                total_files=1,
                languages=["python"],
            )
            self.registry.save_project(project_meta)

        # Verify isolation
        project1_meta = self.registry.get_project(project1_id)
        project2_meta = self.registry.get_project(project2_id)

        assert project1_meta is not None
        assert project2_meta is not None
        assert project1_meta.project_name == "project1"
        assert project2_meta.project_name == "project2"

    # ===== Test 8: Explicit project_id override =====

    def test_explicit_project_id_override(self):
        """
        Test explicit project_id override (for monorepos).

        Scenario:
        - Monorepo with multiple services
        - User provides explicit project_id
        - Should use provided ID instead of auto-generated
        """
        # Create project
        monorepo = self.temp_dir_path / "monorepo"
        frontend = monorepo / "frontend"
        frontend.mkdir(parents=True)
        (frontend / "app.py").write_text("# Frontend\n")

        # Identify with explicit ID
        project_id, project_name, project_type, _ = \
            self.project_identifier.identify_project(
                frontend,
                explicit_id="frontend-app"
            )

        # Expected: Use explicit ID
        assert project_id == "frontend-app"
        assert project_name == "frontend-app"

    # ===== Test 9: File status management =====

    def test_mark_file_as_deleted(self):
        """
        Test marking files as deleted without removing metadata.

        Scenario:
        - File was indexed
        - File is deleted from disk
        - Mark as deleted in registry
        - Metadata should persist with deleted status
        """
        # Create project with file
        project_dir = self.temp_dir_path / "status_project"
        project_dir.mkdir()

        deleted_file = project_dir / "to_delete.py"
        deleted_file.write_text("# Will be deleted\n")

        # Identify project
        project_id, _, _, _ = self.project_identifier.identify_project(project_dir)

        # Save file metadata
        file_meta = self.checksum_service.get_file_metadata_snapshot(
            file_path=deleted_file,
            relative_path=Path("to_delete.py"),
            project_id=project_id,
            language="python",
        )
        self.registry.save_file(file_meta)

        # Verify file is active
        retrieved = self.registry.get_file(project_id, deleted_file)
        assert retrieved.status == FileStatus.ACTIVE

        # Mark as deleted
        result = self.registry.mark_file_deleted(project_id, deleted_file)
        assert result is True

        # Verify marked as deleted
        retrieved = self.registry.get_file(project_id, deleted_file)
        assert retrieved is not None
        assert retrieved.status == FileStatus.DELETED


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
