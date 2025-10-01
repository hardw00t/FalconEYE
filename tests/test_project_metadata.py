"""
Tests for project and file metadata value objects.
"""

import pytest
from datetime import datetime
from pathlib import Path

from falconeye.domain.value_objects.project_metadata import (
    ProjectType,
    ProjectMetadata,
    FileStatus,
    FileMetadata,
)


class TestProjectType:
    """Tests for ProjectType enum."""

    def test_project_type_values(self):
        """Test that ProjectType has correct values."""
        assert ProjectType.GIT == "git"
        assert ProjectType.NON_GIT == "non-git"


class TestProjectMetadata:
    """Tests for ProjectMetadata value object."""

    def test_create_git_project_metadata(self):
        """Test creating metadata for a git project."""
        project = ProjectMetadata(
            project_id="myrepo_a1b2c3d4",
            project_name="myrepo",
            project_root=Path("/path/to/myrepo"),
            project_type=ProjectType.GIT,
            git_remote_url="github.com/user/myrepo",
            last_indexed_commit="abc123def",
            total_files=100,
            total_chunks=500,
            languages=["python", "javascript"],
        )

        assert project.project_id == "myrepo_a1b2c3d4"
        assert project.project_name == "myrepo"
        assert project.project_root == Path("/path/to/myrepo")
        assert project.project_type == ProjectType.GIT
        assert project.git_remote_url == "github.com/user/myrepo"
        assert project.last_indexed_commit == "abc123def"
        assert project.total_files == 100
        assert project.total_chunks == 500
        assert project.languages == ["python", "javascript"]

    def test_create_non_git_project_metadata(self):
        """Test creating metadata for a non-git project."""
        project = ProjectMetadata(
            project_id="myproject_x9y8z7w6",
            project_name="myproject",
            project_root=Path("/path/to/myproject"),
            project_type=ProjectType.NON_GIT,
        )

        assert project.project_id == "myproject_x9y8z7w6"
        assert project.project_type == ProjectType.NON_GIT
        assert project.git_remote_url is None
        assert project.last_indexed_commit is None

    def test_to_dict(self):
        """Test converting ProjectMetadata to dictionary."""
        project = ProjectMetadata(
            project_id="test_project",
            project_name="test",
            project_root=Path("/test"),
            project_type=ProjectType.GIT,
            git_remote_url="github.com/test/test",
        )

        data = project.to_dict()

        assert data["project_id"] == "test_project"
        assert data["project_name"] == "test"
        assert data["project_root"] == "/test"
        assert data["project_type"] == "git"
        assert data["git_remote_url"] == "github.com/test/test"
        assert "created_at" in data
        assert "updated_at" in data

    def test_from_dict(self):
        """Test creating ProjectMetadata from dictionary."""
        data = {
            "project_id": "test_project",
            "project_name": "test",
            "project_root": "/test",
            "project_type": "git",
            "git_remote_url": "github.com/test/test",
            "last_indexed_commit": "abc123",
            "last_full_scan": "2025-10-01T10:00:00",
            "total_files": 50,
            "total_chunks": 250,
            "languages": ["python"],
            "created_at": "2025-10-01T09:00:00",
            "updated_at": "2025-10-01T10:00:00",
        }

        project = ProjectMetadata.from_dict(data)

        assert project.project_id == "test_project"
        assert project.project_name == "test"
        assert project.project_root == Path("/test")
        assert project.project_type == ProjectType.GIT
        assert project.total_files == 50
        assert project.total_chunks == 250
        assert project.languages == ["python"]

    def test_round_trip_serialization(self):
        """Test that to_dict/from_dict round trip works."""
        original = ProjectMetadata(
            project_id="test",
            project_name="test",
            project_root=Path("/test"),
            project_type=ProjectType.NON_GIT,
            total_files=10,
        )

        data = original.to_dict()
        restored = ProjectMetadata.from_dict(data)

        assert restored.project_id == original.project_id
        assert restored.project_name == original.project_name
        assert restored.project_root == original.project_root
        assert restored.project_type == original.project_type
        assert restored.total_files == original.total_files


class TestFileStatus:
    """Tests for FileStatus enum."""

    def test_file_status_values(self):
        """Test that FileStatus has correct values."""
        assert FileStatus.ACTIVE == "active"
        assert FileStatus.DELETED == "deleted"
        assert FileStatus.MODIFIED == "modified"


class TestFileMetadata:
    """Tests for FileMetadata value object."""

    def test_create_file_metadata(self):
        """Test creating file metadata."""
        file_meta = FileMetadata(
            project_id="test_project",
            file_path=Path("/project/src/file.py"),
            relative_path=Path("src/file.py"),
            language="python",
            file_checksum="sha256:abc123",
            file_size=1234,
            file_mtime=1234567890.0,
            git_commit_hash="def456",
            chunk_count=5,
            embedding_ids=["emb1", "emb2", "emb3", "emb4", "emb5"],
        )

        assert file_meta.project_id == "test_project"
        assert file_meta.file_path == Path("/project/src/file.py")
        assert file_meta.relative_path == Path("src/file.py")
        assert file_meta.language == "python"
        assert file_meta.file_checksum == "sha256:abc123"
        assert file_meta.file_size == 1234
        assert file_meta.file_mtime == 1234567890.0
        assert file_meta.git_commit_hash == "def456"
        assert file_meta.chunk_count == 5
        assert len(file_meta.embedding_ids) == 5
        assert file_meta.status == FileStatus.ACTIVE

    def test_has_changed_mtime_differs(self):
        """Test has_changed when modification time differs."""
        file_meta = FileMetadata(
            project_id="test",
            file_path=Path("/test/file.py"),
            relative_path=Path("file.py"),
            language="python",
            file_checksum="sha256:abc",
            file_size=1000,
            file_mtime=1000.0,
        )

        # Different mtime, same size
        assert file_meta.has_changed(2000.0, 1000) is True

    def test_has_changed_size_differs(self):
        """Test has_changed when file size differs."""
        file_meta = FileMetadata(
            project_id="test",
            file_path=Path("/test/file.py"),
            relative_path=Path("file.py"),
            language="python",
            file_checksum="sha256:abc",
            file_size=1000,
            file_mtime=1000.0,
        )

        # Same mtime, different size
        assert file_meta.has_changed(1000.0, 2000) is True

    def test_has_changed_both_same(self):
        """Test has_changed when both mtime and size are same."""
        file_meta = FileMetadata(
            project_id="test",
            file_path=Path("/test/file.py"),
            relative_path=Path("file.py"),
            language="python",
            file_checksum="sha256:abc",
            file_size=1000,
            file_mtime=1000.0,
        )

        # Same mtime and size
        assert file_meta.has_changed(1000.0, 1000) is False

    def test_to_dict(self):
        """Test converting FileMetadata to dictionary."""
        file_meta = FileMetadata(
            project_id="test",
            file_path=Path("/test/file.py"),
            relative_path=Path("file.py"),
            language="python",
            file_checksum="sha256:abc",
            file_size=1000,
            file_mtime=1000.0,
        )

        data = file_meta.to_dict()

        assert data["project_id"] == "test"
        assert data["file_path"] == "/test/file.py"
        assert data["relative_path"] == "file.py"
        assert data["language"] == "python"
        assert data["file_checksum"] == "sha256:abc"
        assert data["file_size"] == 1000
        assert data["file_mtime"] == 1000.0
        assert data["status"] == "active"

    def test_from_dict(self):
        """Test creating FileMetadata from dictionary."""
        data = {
            "project_id": "test",
            "file_path": "/test/file.py",
            "relative_path": "file.py",
            "language": "python",
            "file_checksum": "sha256:abc",
            "file_size": 1000,
            "file_mtime": 1000.0,
            "indexed_at": "2025-10-01T10:00:00",
            "chunk_count": 3,
            "embedding_ids": ["e1", "e2", "e3"],
            "status": "active",
            "last_scanned": "2025-10-01T10:00:00",
        }

        file_meta = FileMetadata.from_dict(data)

        assert file_meta.project_id == "test"
        assert file_meta.file_path == Path("/test/file.py")
        assert file_meta.relative_path == Path("file.py")
        assert file_meta.chunk_count == 3
        assert file_meta.status == FileStatus.ACTIVE

    def test_round_trip_serialization(self):
        """Test that to_dict/from_dict round trip works."""
        original = FileMetadata(
            project_id="test",
            file_path=Path("/test/file.py"),
            relative_path=Path("file.py"),
            language="python",
            file_checksum="sha256:abc",
            file_size=1000,
            file_mtime=1000.0,
            chunk_count=5,
        )

        data = original.to_dict()
        restored = FileMetadata.from_dict(data)

        assert restored.project_id == original.project_id
        assert restored.file_path == original.file_path
        assert restored.relative_path == original.relative_path
        assert restored.language == original.language
        assert restored.file_checksum == original.file_checksum
        assert restored.chunk_count == original.chunk_count
        assert restored.status == original.status


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
