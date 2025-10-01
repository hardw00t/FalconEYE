"""
Tests for ChecksumService.
"""

import pytest
import tempfile
from pathlib import Path
from datetime import datetime

from falconeye.domain.services.checksum_service import ChecksumService
from falconeye.domain.value_objects.project_metadata import FileMetadata, FileStatus


class TestChecksumService:
    """Tests for ChecksumService."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = ChecksumService()

    def test_calculate_file_checksum(self):
        """Test SHA256 checksum calculation."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("Hello, World!")
            temp_path = Path(f.name)

        try:
            checksum = self.service.calculate_file_checksum(temp_path)

            # Should have sha256: prefix
            assert checksum.startswith("sha256:")

            # Should be deterministic
            checksum2 = self.service.calculate_file_checksum(temp_path)
            assert checksum == checksum2

            # Should be correct SHA256
            expected = "sha256:dffd6021bb2bd5b0af676290809ec3a53191dd81c7f70a4b28688a362182986f"
            assert checksum == expected
        finally:
            temp_path.unlink()

    def test_calculate_file_checksum_large_file(self):
        """Test SHA256 calculation for large file (streaming)."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            # Write 1MB of data
            content = "A" * (1024 * 1024)
            f.write(content)
            temp_path = Path(f.name)

        try:
            checksum = self.service.calculate_file_checksum(temp_path)

            # Should work without loading entire file in memory
            assert checksum.startswith("sha256:")
            assert len(checksum) == 71  # "sha256:" + 64 hex chars
        finally:
            temp_path.unlink()

    def test_calculate_file_checksum_empty_file(self):
        """Test checksum of empty file."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            temp_path = Path(f.name)

        try:
            checksum = self.service.calculate_file_checksum(temp_path)

            # Empty file has specific SHA256
            expected = "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
            assert checksum == expected
        finally:
            temp_path.unlink()

    def test_calculate_file_checksum_nonexistent_file(self):
        """Test checksum calculation for non-existent file."""
        with pytest.raises(FileNotFoundError):
            self.service.calculate_file_checksum(Path("/nonexistent/file.txt"))

    def test_has_file_changed_quick_no_cache(self):
        """Test quick check with no cached metadata."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            temp_path = Path(f.name)

        try:
            # No cached metadata should return True (assume changed)
            result = self.service.has_file_changed_quick(temp_path, None)
            assert result is True
        finally:
            temp_path.unlink()

    def test_has_file_changed_quick_same_mtime_and_size(self):
        """Test quick check when mtime and size match."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("test content")
            temp_path = Path(f.name)

        try:
            stat = temp_path.stat()

            # Create cached metadata with same mtime and size
            cached = FileMetadata(
                project_id="test",
                file_path=temp_path,
                relative_path=Path("test.txt"),
                language="text",
                file_checksum="sha256:abc",
                file_size=stat.st_size,
                file_mtime=stat.st_mtime,
            )

            # Should return False (not changed)
            result = self.service.has_file_changed_quick(temp_path, cached)
            assert result is False
        finally:
            temp_path.unlink()

    def test_has_file_changed_quick_different_mtime(self):
        """Test quick check when mtime differs."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("test content")
            temp_path = Path(f.name)

        try:
            stat = temp_path.stat()

            # Create cached metadata with different mtime
            cached = FileMetadata(
                project_id="test",
                file_path=temp_path,
                relative_path=Path("test.txt"),
                language="text",
                file_checksum="sha256:abc",
                file_size=stat.st_size,
                file_mtime=stat.st_mtime - 1000,  # Different mtime
            )

            # Should return True (changed)
            result = self.service.has_file_changed_quick(temp_path, cached)
            assert result is True
        finally:
            temp_path.unlink()

    def test_has_file_changed_quick_different_size(self):
        """Test quick check when size differs."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("test content")
            temp_path = Path(f.name)

        try:
            stat = temp_path.stat()

            # Create cached metadata with different size
            cached = FileMetadata(
                project_id="test",
                file_path=temp_path,
                relative_path=Path("test.txt"),
                language="text",
                file_checksum="sha256:abc",
                file_size=stat.st_size + 100,  # Different size
                file_mtime=stat.st_mtime,
            )

            # Should return True (changed)
            result = self.service.has_file_changed_quick(temp_path, cached)
            assert result is True
        finally:
            temp_path.unlink()

    def test_has_file_changed_checksum_no_cache(self):
        """Test checksum verification with no cached metadata."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("test")
            temp_path = Path(f.name)

        try:
            # No cached metadata should return True
            result = self.service.has_file_changed_checksum(temp_path, None)
            assert result is True
        finally:
            temp_path.unlink()

    def test_has_file_changed_checksum_same_content(self):
        """Test checksum verification when content is same."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("test content")
            temp_path = Path(f.name)

        try:
            # Calculate actual checksum
            actual_checksum = self.service.calculate_file_checksum(temp_path)

            # Create cached metadata with same checksum
            cached = FileMetadata(
                project_id="test",
                file_path=temp_path,
                relative_path=Path("test.txt"),
                language="text",
                file_checksum=actual_checksum,
                file_size=100,
                file_mtime=1000.0,
            )

            # Should return False (not changed)
            result = self.service.has_file_changed_checksum(temp_path, cached)
            assert result is False
        finally:
            temp_path.unlink()

    def test_has_file_changed_checksum_different_content(self):
        """Test checksum verification when content differs."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("new content")
            temp_path = Path(f.name)

        try:
            # Create cached metadata with different checksum
            cached = FileMetadata(
                project_id="test",
                file_path=temp_path,
                relative_path=Path("test.txt"),
                language="text",
                file_checksum="sha256:old_checksum_here",
                file_size=100,
                file_mtime=1000.0,
            )

            # Should return True (changed)
            result = self.service.has_file_changed_checksum(temp_path, cached)
            assert result is True
        finally:
            temp_path.unlink()

    def test_get_file_metadata_snapshot(self):
        """Test creating file metadata snapshot."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("test content")
            temp_path = Path(f.name)

        try:
            snapshot = self.service.get_file_metadata_snapshot(
                file_path=temp_path,
                relative_path=Path("test.txt"),
                project_id="test_project",
                language="python",
                git_commit_hash="abc123",
            )

            assert snapshot.project_id == "test_project"
            assert snapshot.file_path == temp_path
            assert snapshot.relative_path == Path("test.txt")
            assert snapshot.language == "python"
            assert snapshot.git_commit_hash == "abc123"
            assert snapshot.file_checksum.startswith("sha256:")
            assert snapshot.file_size > 0
            assert snapshot.file_mtime > 0
        finally:
            temp_path.unlink()

    def test_filter_changed_files_efficient_no_cache(self):
        """Test filtering when no cached metadata."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            file1 = tmpdir / "file1.txt"
            file2 = tmpdir / "file2.txt"
            file1.write_text("content1")
            file2.write_text("content2")

            files = [file1, file2]
            cached = {}  # No cached metadata

            changed, unchanged = self.service.filter_changed_files_efficient(
                files, cached, use_checksum=False
            )

            # All files should be marked as changed (new files)
            assert len(changed) == 2
            assert len(unchanged) == 0

    def test_filter_changed_files_efficient_all_unchanged(self):
        """Test filtering when all files unchanged."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            file1 = tmpdir / "file1.txt"
            file1.write_text("content1")

            stat = file1.stat()

            # Create cached metadata matching current state
            cached = {
                file1: FileMetadata(
                    project_id="test",
                    file_path=file1,
                    relative_path=Path("file1.txt"),
                    language="text",
                    file_checksum=self.service.calculate_file_checksum(file1),
                    file_size=stat.st_size,
                    file_mtime=stat.st_mtime,
                )
            }

            changed, unchanged = self.service.filter_changed_files_efficient(
                [file1], cached, use_checksum=False
            )

            # File should be unchanged
            assert len(changed) == 0
            assert len(unchanged) == 1

    def test_filter_changed_files_efficient_with_checksum_verification(self):
        """Test filtering with checksum verification enabled."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            file1 = tmpdir / "file1.txt"
            file1.write_text("content1")

            stat = file1.stat()

            # Create cached with different mtime but same content
            # (file was touched but not modified)
            cached = {
                file1: FileMetadata(
                    project_id="test",
                    file_path=file1,
                    relative_path=Path("file1.txt"),
                    language="text",
                    file_checksum=self.service.calculate_file_checksum(file1),
                    file_size=stat.st_size,
                    file_mtime=stat.st_mtime - 1000,  # Different mtime
                )
            }

            # With checksum verification
            changed, unchanged = self.service.filter_changed_files_efficient(
                [file1], cached, use_checksum=True
            )

            # Should detect that content hasn't actually changed
            assert len(changed) == 0
            assert len(unchanged) == 1

    def test_batch_calculate_checksums(self):
        """Test parallel checksum calculation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Create multiple files
            files = []
            for i in range(5):
                file_path = tmpdir / f"file{i}.txt"
                file_path.write_text(f"content {i}")
                files.append(file_path)

            # Calculate checksums in parallel
            checksums = self.service.batch_calculate_checksums(files, max_workers=2)

            # Should have checksum for each file
            assert len(checksums) == 5

            # All should start with sha256:
            for checksum in checksums.values():
                assert checksum.startswith("sha256:")

            # Should be deterministic
            checksums2 = self.service.batch_calculate_checksums(files, max_workers=2)
            assert checksums == checksums2

    def test_identify_deleted_files(self):
        """Test identifying deleted files."""
        current = {Path("/a.txt"), Path("/b.txt")}
        cached = {Path("/a.txt"), Path("/b.txt"), Path("/c.txt"), Path("/d.txt")}

        deleted = self.service.identify_deleted_files(current, cached)

        assert len(deleted) == 2
        assert Path("/c.txt") in deleted
        assert Path("/d.txt") in deleted

    def test_identify_deleted_files_none_deleted(self):
        """Test when no files deleted."""
        current = {Path("/a.txt"), Path("/b.txt")}
        cached = {Path("/a.txt"), Path("/b.txt")}

        deleted = self.service.identify_deleted_files(current, cached)

        assert len(deleted) == 0

    def test_identify_new_files(self):
        """Test identifying new files."""
        current = {Path("/a.txt"), Path("/b.txt"), Path("/c.txt"), Path("/d.txt")}
        cached = {Path("/a.txt"), Path("/b.txt")}

        new_files = self.service.identify_new_files(current, cached)

        assert len(new_files) == 2
        assert Path("/c.txt") in new_files
        assert Path("/d.txt") in new_files

    def test_identify_new_files_none_new(self):
        """Test when no new files."""
        current = {Path("/a.txt"), Path("/b.txt")}
        cached = {Path("/a.txt"), Path("/b.txt")}

        new_files = self.service.identify_new_files(current, cached)

        assert len(new_files) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
