"""
Tests for ProjectIdentifier service.
"""

import pytest
import tempfile
import subprocess
from pathlib import Path

from falconeye.domain.services.project_identifier import ProjectIdentifier
from falconeye.domain.value_objects.project_metadata import ProjectType


class TestProjectIdentifier:
    """Tests for ProjectIdentifier service."""

    def setup_method(self):
        """Set up test fixtures."""
        self.identifier = ProjectIdentifier()

    def test_sanitize_project_id_basic(self):
        """Test basic project ID sanitization."""
        result = self.identifier._sanitize_project_id("My Project")
        assert result == "my_project"

    def test_sanitize_project_id_special_chars(self):
        """Test sanitization with special characters."""
        result = self.identifier._sanitize_project_id("my-project@2024!")
        # Hyphens are allowed, @ and ! are replaced with _
        assert result == "my-project_2024"

    def test_sanitize_project_id_consecutive_underscores(self):
        """Test removal of consecutive underscores."""
        result = self.identifier._sanitize_project_id("my___project")
        assert result == "my_project"

    def test_sanitize_project_id_starts_with_number(self):
        """Test ID starting with number."""
        result = self.identifier._sanitize_project_id("123project")
        assert result == "p123project"

    def test_sanitize_project_id_empty(self):
        """Test sanitization of empty string."""
        result = self.identifier._sanitize_project_id("")
        assert result == "project"

    def test_normalize_git_url_https(self):
        """Test normalizing HTTPS git URL."""
        url = "https://github.com/user/repo.git"
        result = self.identifier._normalize_git_url(url)
        assert result == "github.com/user/repo"

    def test_normalize_git_url_ssh(self):
        """Test normalizing SSH git URL."""
        url = "git@github.com:user/repo.git"
        result = self.identifier._normalize_git_url(url)
        assert result == "github.com/user/repo"

    def test_normalize_git_url_no_git_suffix(self):
        """Test normalizing URL without .git suffix."""
        url = "https://github.com/user/repo"
        result = self.identifier._normalize_git_url(url)
        assert result == "github.com/user/repo"

    def test_hash_string(self):
        """Test string hashing."""
        result = self.identifier._hash_string("test")
        assert len(result) == 64  # SHA256 produces 64 hex chars
        assert result == self.identifier._hash_string("test")  # Deterministic

    def test_identify_project_with_explicit_id(self):
        """Test project identification with explicit ID override."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir)

            project_id, name, proj_type, remote = self.identifier.identify_project(
                path, explicit_id="custom-project"
            )

            # Hyphens are allowed in sanitized IDs
            assert project_id == "custom-project"
            assert name == "custom-project"
            assert proj_type == ProjectType.NON_GIT
            assert remote is None

    def test_identify_project_non_git(self):
        """Test project identification for non-git directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir)

            project_id, name, proj_type, remote = self.identifier.identify_project(path)

            # Should use directory name + path hash
            assert proj_type == ProjectType.NON_GIT
            assert remote is None
            assert "_" in project_id  # Should have hash suffix
            assert len(project_id.split("_")[-1]) == 8  # Hash is 8 chars

    def test_find_git_root_no_git(self):
        """Test finding git root in non-git directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir)
            result = self.identifier._find_git_root(path)
            assert result is None

    def test_find_git_root_with_git(self):
        """Test finding git root in git repository."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir).resolve()  # Resolve to handle /private on macOS

            # Initialize git repo
            subprocess.run(["git", "init"], cwd=path, capture_output=True)

            result = self.identifier._find_git_root(path)
            assert result == path

    def test_find_git_root_subdirectory(self):
        """Test finding git root from subdirectory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir).resolve()  # Resolve to handle /private on macOS

            # Initialize git repo
            subprocess.run(["git", "init"], cwd=path, capture_output=True)

            # Create subdirectory
            subdir = path / "src" / "deep"
            subdir.mkdir(parents=True)

            result = self.identifier._find_git_root(subdir)
            assert result == path

    def test_identify_project_git_no_remote(self):
        """Test project identification for git repo without remote."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir)

            # Initialize git repo (no remote)
            subprocess.run(["git", "init"], cwd=path, capture_output=True)

            project_id, name, proj_type, remote = self.identifier.identify_project(path)

            assert proj_type == ProjectType.GIT
            assert remote is None
            # Should use just the directory name (sanitized - trailing underscores removed)
            expected = self.identifier._sanitize_project_id(path.name)
            assert project_id == expected

    def test_identify_project_git_with_remote(self):
        """Test project identification for git repo with remote."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir)

            # Initialize git repo
            subprocess.run(["git", "init"], cwd=path, capture_output=True)

            # Add remote
            subprocess.run(
                ["git", "remote", "add", "origin", "https://github.com/test/repo.git"],
                cwd=path,
                capture_output=True,
            )

            project_id, name, proj_type, remote = self.identifier.identify_project(path)

            assert proj_type == ProjectType.GIT
            assert remote == "github.com/test/repo"
            assert "_" in project_id  # Should have hash suffix
            # Project ID should be: {sanitized_dirname}_{8char_hash}
            # The last part should be 8 chars (the hash)
            parts = project_id.split("_")
            assert len(parts[-1]) == 8  # Last part is hash
            # Directory name should be in the project_id
            sanitized_dirname = self.identifier._sanitize_project_id(path.name)
            assert project_id.startswith(sanitized_dirname)

    def test_get_current_git_commit(self):
        """Test getting current git commit hash."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir)

            # Initialize git repo
            subprocess.run(["git", "init"], cwd=path, capture_output=True)
            subprocess.run(
                ["git", "config", "user.email", "test@test.com"],
                cwd=path,
                capture_output=True,
            )
            subprocess.run(
                ["git", "config", "user.name", "Test User"],
                cwd=path,
                capture_output=True,
            )

            # Create a commit
            (path / "test.txt").write_text("test")
            subprocess.run(["git", "add", "."], cwd=path, capture_output=True)
            subprocess.run(
                ["git", "commit", "-m", "test"], cwd=path, capture_output=True
            )

            commit = self.identifier.get_current_git_commit(path)
            assert commit is not None
            assert len(commit) == 40  # Git SHA1 is 40 chars

    def test_get_current_git_commit_no_commits(self):
        """Test getting commit hash when no commits exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir)

            # Initialize git repo but don't commit
            subprocess.run(["git", "init"], cwd=path, capture_output=True)

            commit = self.identifier.get_current_git_commit(path)
            assert commit is None  # No commits yet

    def test_has_uncommitted_changes_clean(self):
        """Test detecting uncommitted changes in clean repo."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir)

            # Initialize git repo with commit
            subprocess.run(["git", "init"], cwd=path, capture_output=True)
            subprocess.run(
                ["git", "config", "user.email", "test@test.com"],
                cwd=path,
                capture_output=True,
            )
            subprocess.run(
                ["git", "config", "user.name", "Test User"],
                cwd=path,
                capture_output=True,
            )
            (path / "test.txt").write_text("test")
            subprocess.run(["git", "add", "."], cwd=path, capture_output=True)
            subprocess.run(
                ["git", "commit", "-m", "test"], cwd=path, capture_output=True
            )

            has_changes = self.identifier.has_uncommitted_changes(path)
            assert has_changes is False

    def test_has_uncommitted_changes_with_changes(self):
        """Test detecting uncommitted changes when changes exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir)

            # Initialize git repo with commit
            subprocess.run(["git", "init"], cwd=path, capture_output=True)
            subprocess.run(
                ["git", "config", "user.email", "test@test.com"],
                cwd=path,
                capture_output=True,
            )
            subprocess.run(
                ["git", "config", "user.name", "Test User"],
                cwd=path,
                capture_output=True,
            )
            (path / "test.txt").write_text("test")
            subprocess.run(["git", "add", "."], cwd=path, capture_output=True)
            subprocess.run(
                ["git", "commit", "-m", "test"], cwd=path, capture_output=True
            )

            # Make changes
            (path / "test2.txt").write_text("new file")

            has_changes = self.identifier.has_uncommitted_changes(path)
            assert has_changes is True

    def test_get_git_untracked_files(self):
        """Test getting untracked files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir)

            # Initialize git repo
            subprocess.run(["git", "init"], cwd=path, capture_output=True)

            # Create untracked files
            (path / "untracked1.txt").write_text("test1")
            (path / "untracked2.txt").write_text("test2")

            untracked = self.identifier.get_git_untracked_files(path)

            assert len(untracked) == 2
            assert path / "untracked1.txt" in untracked
            assert path / "untracked2.txt" in untracked


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
