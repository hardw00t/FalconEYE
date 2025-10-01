"""
Tests for ChromaIndexRegistryAdapter.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

from falconeye.infrastructure.registry.chroma_registry_adapter import (
    ChromaIndexRegistryAdapter,
)
from falconeye.domain.value_objects.project_metadata import (
    ProjectType,
    ProjectMetadata,
    FileStatus,
    FileMetadata,
)


class TestChromaIndexRegistryAdapter:
    """Tests for ChromaIndexRegistryAdapter."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create temporary directory for test database
        self.temp_dir = tempfile.mkdtemp()
        self.registry = ChromaIndexRegistryAdapter(
            persist_directory=self.temp_dir,
            collection_name="test_registry",
        )

    def teardown_method(self):
        """Clean up test fixtures."""
        # Remove temporary directory
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    # ===== Project Management Tests =====

    def test_save_and_get_project(self):
        """Test saving and retrieving project metadata."""
        project = ProjectMetadata(
            project_id="test_project",
            project_name="Test Project",
            project_root=Path("/test/project"),
            project_type=ProjectType.GIT,
            git_remote_url="github.com/test/project",
            last_indexed_commit="abc123",
            total_files=100,
            total_chunks=500,
            languages=["python", "javascript"],
        )

        # Save project
        self.registry.save_project(project)

        # Retrieve project
        retrieved = self.registry.get_project("test_project")

        assert retrieved is not None
        assert retrieved.project_id == "test_project"
        assert retrieved.project_name == "Test Project"
        assert retrieved.project_root == Path("/test/project")
        assert retrieved.project_type == ProjectType.GIT
        assert retrieved.git_remote_url == "github.com/test/project"
        assert retrieved.last_indexed_commit == "abc123"
        assert retrieved.total_files == 100
        assert retrieved.total_chunks == 500
        assert retrieved.languages == ["python", "javascript"]

    def test_get_project_nonexistent(self):
        """Test retrieving non-existent project."""
        result = self.registry.get_project("nonexistent")
        assert result is None

    def test_update_project(self):
        """Test updating existing project."""
        project = ProjectMetadata(
            project_id="test_project",
            project_name="Test",
            project_root=Path("/test"),
            project_type=ProjectType.GIT,
            total_files=10,
        )

        # Save initial
        self.registry.save_project(project)

        # Update
        updated_project = ProjectMetadata(
            project_id="test_project",
            project_name="Test",
            project_root=Path("/test"),
            project_type=ProjectType.GIT,
            total_files=20,  # Changed
            total_chunks=100,  # Changed
        )

        self.registry.save_project(updated_project)

        # Retrieve
        retrieved = self.registry.get_project("test_project")
        assert retrieved.total_files == 20
        assert retrieved.total_chunks == 100

    def test_get_all_projects(self):
        """Test retrieving all projects."""
        # Save multiple projects
        for i in range(3):
            project = ProjectMetadata(
                project_id=f"project{i}",
                project_name=f"Project {i}",
                project_root=Path(f"/project{i}"),
                project_type=ProjectType.NON_GIT,
            )
            self.registry.save_project(project)

        # Retrieve all
        projects = self.registry.get_all_projects()

        assert len(projects) == 3
        project_ids = {p.project_id for p in projects}
        assert project_ids == {"project0", "project1", "project2"}

    def test_delete_project(self):
        """Test deleting a project."""
        project = ProjectMetadata(
            project_id="test_project",
            project_name="Test",
            project_root=Path("/test"),
            project_type=ProjectType.GIT,
        )

        self.registry.save_project(project)
        assert self.registry.project_exists("test_project")

        # Delete
        result = self.registry.delete_project("test_project")
        assert result is True

        # Verify deleted
        assert not self.registry.project_exists("test_project")
        assert self.registry.get_project("test_project") is None

    def test_delete_project_with_files(self):
        """Test that deleting project also deletes associated files."""
        # Create project
        project = ProjectMetadata(
            project_id="test_project",
            project_name="Test",
            project_root=Path("/test"),
            project_type=ProjectType.GIT,
        )
        self.registry.save_project(project)

        # Add files
        for i in range(3):
            file_meta = FileMetadata(
                project_id="test_project",
                file_path=Path(f"/test/file{i}.py"),
                relative_path=Path(f"file{i}.py"),
                language="python",
                file_checksum=f"sha256:abc{i}",
                file_size=1000,
                file_mtime=1000.0,
            )
            self.registry.save_file(file_meta)

        # Delete project
        self.registry.delete_project("test_project")

        # Verify files are also deleted
        files = self.registry.get_all_files("test_project")
        assert len(files) == 0

    def test_project_exists(self):
        """Test checking if project exists."""
        assert not self.registry.project_exists("test_project")

        project = ProjectMetadata(
            project_id="test_project",
            project_name="Test",
            project_root=Path("/test"),
            project_type=ProjectType.GIT,
        )
        self.registry.save_project(project)

        assert self.registry.project_exists("test_project")

    # ===== File Management Tests =====

    def test_save_and_get_file(self):
        """Test saving and retrieving file metadata."""
        file_meta = FileMetadata(
            project_id="test_project",
            file_path=Path("/test/file.py"),
            relative_path=Path("file.py"),
            language="python",
            file_checksum="sha256:abc123",
            file_size=1234,
            file_mtime=1234567890.0,
            git_commit_hash="def456",
            chunk_count=5,
            embedding_ids=["e1", "e2", "e3", "e4", "e5"],
        )

        # Save file
        self.registry.save_file(file_meta)

        # Retrieve file
        retrieved = self.registry.get_file("test_project", Path("/test/file.py"))

        assert retrieved is not None
        assert retrieved.project_id == "test_project"
        assert retrieved.file_path == Path("/test/file.py")
        assert retrieved.relative_path == Path("file.py")
        assert retrieved.language == "python"
        assert retrieved.file_checksum == "sha256:abc123"
        assert retrieved.file_size == 1234
        assert retrieved.file_mtime == 1234567890.0
        assert retrieved.git_commit_hash == "def456"
        assert retrieved.chunk_count == 5
        assert len(retrieved.embedding_ids) == 5
        assert retrieved.status == FileStatus.ACTIVE

    def test_get_file_nonexistent(self):
        """Test retrieving non-existent file."""
        result = self.registry.get_file("test_project", Path("/nonexistent.py"))
        assert result is None

    def test_save_files_batch(self):
        """Test batch saving of files."""
        files = []
        for i in range(10):
            file_meta = FileMetadata(
                project_id="test_project",
                file_path=Path(f"/test/file{i}.py"),
                relative_path=Path(f"file{i}.py"),
                language="python",
                file_checksum=f"sha256:abc{i}",
                file_size=1000 + i,
                file_mtime=1000.0 + i,
            )
            files.append(file_meta)

        # Batch save
        self.registry.save_files_batch(files)

        # Verify all saved
        all_files = self.registry.get_all_files("test_project")
        assert len(all_files) == 10

    def test_get_all_files(self):
        """Test retrieving all files for a project."""
        # Save files for project1
        for i in range(3):
            file_meta = FileMetadata(
                project_id="project1",
                file_path=Path(f"/p1/file{i}.py"),
                relative_path=Path(f"file{i}.py"),
                language="python",
                file_checksum=f"sha256:p1_{i}",
                file_size=1000,
                file_mtime=1000.0,
            )
            self.registry.save_file(file_meta)

        # Save files for project2
        for i in range(2):
            file_meta = FileMetadata(
                project_id="project2",
                file_path=Path(f"/p2/file{i}.py"),
                relative_path=Path(f"file{i}.py"),
                language="python",
                file_checksum=f"sha256:p2_{i}",
                file_size=1000,
                file_mtime=1000.0,
            )
            self.registry.save_file(file_meta)

        # Get files for project1 only
        files = self.registry.get_all_files("project1")
        assert len(files) == 3

        # Get files for project2 only
        files = self.registry.get_all_files("project2")
        assert len(files) == 2

    def test_get_files_by_status(self):
        """Test retrieving files by status."""
        # Save active files
        for i in range(3):
            file_meta = FileMetadata(
                project_id="test_project",
                file_path=Path(f"/test/active{i}.py"),
                relative_path=Path(f"active{i}.py"),
                language="python",
                file_checksum=f"sha256:active{i}",
                file_size=1000,
                file_mtime=1000.0,
                status=FileStatus.ACTIVE,
            )
            self.registry.save_file(file_meta)

        # Save deleted files
        for i in range(2):
            file_meta = FileMetadata(
                project_id="test_project",
                file_path=Path(f"/test/deleted{i}.py"),
                relative_path=Path(f"deleted{i}.py"),
                language="python",
                file_checksum=f"sha256:deleted{i}",
                file_size=1000,
                file_mtime=1000.0,
                status=FileStatus.DELETED,
            )
            self.registry.save_file(file_meta)

        # Get active files
        active_files = self.registry.get_files_by_status("test_project", "active")
        assert len(active_files) == 3

        # Get deleted files
        deleted_files = self.registry.get_files_by_status("test_project", "deleted")
        assert len(deleted_files) == 2

    def test_delete_file(self):
        """Test deleting a file."""
        file_meta = FileMetadata(
            project_id="test_project",
            file_path=Path("/test/file.py"),
            relative_path=Path("file.py"),
            language="python",
            file_checksum="sha256:abc",
            file_size=1000,
            file_mtime=1000.0,
        )

        self.registry.save_file(file_meta)
        assert self.registry.get_file("test_project", Path("/test/file.py")) is not None

        # Delete
        result = self.registry.delete_file("test_project", Path("/test/file.py"))
        assert result is True

        # Verify deleted
        assert self.registry.get_file("test_project", Path("/test/file.py")) is None

    def test_delete_files_batch(self):
        """Test batch deletion of files."""
        # Save files
        paths = []
        for i in range(5):
            path = Path(f"/test/file{i}.py")
            paths.append(path)

            file_meta = FileMetadata(
                project_id="test_project",
                file_path=path,
                relative_path=Path(f"file{i}.py"),
                language="python",
                file_checksum=f"sha256:abc{i}",
                file_size=1000,
                file_mtime=1000.0,
            )
            self.registry.save_file(file_meta)

        # Delete batch
        deleted_count = self.registry.delete_files_batch("test_project", paths[:3])
        assert deleted_count == 3

        # Verify
        all_files = self.registry.get_all_files("test_project")
        assert len(all_files) == 2  # 2 remaining

    def test_mark_file_deleted(self):
        """Test marking file as deleted without removing metadata."""
        file_meta = FileMetadata(
            project_id="test_project",
            file_path=Path("/test/file.py"),
            relative_path=Path("file.py"),
            language="python",
            file_checksum="sha256:abc",
            file_size=1000,
            file_mtime=1000.0,
            status=FileStatus.ACTIVE,
        )

        self.registry.save_file(file_meta)

        # Mark as deleted
        result = self.registry.mark_file_deleted("test_project", Path("/test/file.py"))
        assert result is True

        # Verify still exists but marked as deleted
        retrieved = self.registry.get_file("test_project", Path("/test/file.py"))
        assert retrieved is not None
        assert retrieved.status == FileStatus.DELETED

    # ===== Query Operations Tests =====

    def test_get_file_paths(self):
        """Test getting all file paths for a project."""
        paths = [Path("/test/a.py"), Path("/test/b.py"), Path("/test/c.py")]

        for path in paths:
            file_meta = FileMetadata(
                project_id="test_project",
                file_path=path,
                relative_path=Path(path.name),
                language="python",
                file_checksum="sha256:abc",
                file_size=1000,
                file_mtime=1000.0,
            )
            self.registry.save_file(file_meta)

        # Get paths
        result_paths = self.registry.get_file_paths("test_project")

        assert len(result_paths) == 3
        assert set(result_paths) == set(paths)

    def test_get_files_metadata_dict(self):
        """Test getting files as dictionary."""
        paths = [Path("/test/a.py"), Path("/test/b.py")]

        for path in paths:
            file_meta = FileMetadata(
                project_id="test_project",
                file_path=path,
                relative_path=Path(path.name),
                language="python",
                file_checksum="sha256:abc",
                file_size=1000,
                file_mtime=1000.0,
            )
            self.registry.save_file(file_meta)

        # Get as dict
        files_dict = self.registry.get_files_metadata_dict("test_project")

        assert len(files_dict) == 2
        assert Path("/test/a.py") in files_dict
        assert Path("/test/b.py") in files_dict
        assert files_dict[Path("/test/a.py")].relative_path == Path("a.py")

    def test_get_project_stats(self):
        """Test getting project statistics."""
        # Save active files
        for i in range(5):
            file_meta = FileMetadata(
                project_id="test_project",
                file_path=Path(f"/test/active{i}.py"),
                relative_path=Path(f"active{i}.py"),
                language="python",
                file_checksum=f"sha256:abc{i}",
                file_size=1000,
                file_mtime=1000.0,
                chunk_count=10,
                status=FileStatus.ACTIVE,
            )
            self.registry.save_file(file_meta)

        # Save deleted files
        for i in range(2):
            file_meta = FileMetadata(
                project_id="test_project",
                file_path=Path(f"/test/deleted{i}.py"),
                relative_path=Path(f"deleted{i}.py"),
                language="python",
                file_checksum=f"sha256:del{i}",
                file_size=1000,
                file_mtime=1000.0,
                chunk_count=5,
                status=FileStatus.DELETED,
            )
            self.registry.save_file(file_meta)

        # Get stats
        stats = self.registry.get_project_stats("test_project")

        assert stats["total_files"] == 7
        assert stats["active_files"] == 5
        assert stats["deleted_files"] == 2
        assert stats["total_chunks"] == (5 * 10) + (2 * 5)  # 60

    # ===== Bulk Operations Tests =====

    def test_clear_project_files(self):
        """Test clearing all files for a project."""
        # Save files
        for i in range(5):
            file_meta = FileMetadata(
                project_id="test_project",
                file_path=Path(f"/test/file{i}.py"),
                relative_path=Path(f"file{i}.py"),
                language="python",
                file_checksum=f"sha256:abc{i}",
                file_size=1000,
                file_mtime=1000.0,
            )
            self.registry.save_file(file_meta)

        # Clear
        cleared_count = self.registry.clear_project_files("test_project")
        assert cleared_count == 5

        # Verify all cleared
        files = self.registry.get_all_files("test_project")
        assert len(files) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
