"""Tests for environment detection functionality."""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from mcpydoc.env_detection import (
    find_venv_in_directory,
    get_active_python_environments,
    get_pwd_environment,
    get_search_paths_from_env,
    is_pipx_environment,
    load_mcpydoc_config,
    resolve_python_path_from_config,
    search_common_project_directories,
)


class TestIsPipxEnvironment:
    """Test pipx/uvx environment detection."""

    def test_detects_pipx_venvs(self):
        """Test detection of pipx venv paths."""
        assert is_pipx_environment("/home/user/.local/pipx/venvs/mcpydoc")
        assert is_pipx_environment("/Users/user/.local/pipx/venvs/tool")

    def test_detects_uvx(self):
        """Test detection of uvx paths."""
        assert is_pipx_environment("/home/user/.local/uvx/mcpydoc")

    def test_detects_pipx_share(self):
        """Test detection of pipx share paths."""
        assert is_pipx_environment("/home/user/.local/share/pipx/venvs/tool")

    def test_normal_paths_not_detected(self):
        """Test that normal paths are not detected as pipx."""
        assert not is_pipx_environment("/home/user/projects/myapp/.venv")
        assert not is_pipx_environment("/usr/local/lib/python3.12")
        assert not is_pipx_environment("/home/user/.pyenv/versions/3.12.0")


class TestLoadMcpydocConfig:
    """Test .mcpydoc.json configuration loading."""

    def test_load_valid_config(self):
        """Test loading a valid configuration file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / ".mcpydoc.json"
            config_data = {
                "python_path": ".venv",
                "fallback_paths": ["/usr/bin/python3"],
            }
            with open(config_path, "w") as f:
                json.dump(config_data, f)

            result = load_mcpydoc_config(Path(tmpdir))
            assert result == config_data

    def test_nonexistent_config(self):
        """Test handling of nonexistent configuration file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = load_mcpydoc_config(Path(tmpdir))
            assert result is None

    def test_invalid_json(self):
        """Test handling of invalid JSON in configuration file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / ".mcpydoc.json"
            with open(config_path, "w") as f:
                f.write("{ invalid json }")

            result = load_mcpydoc_config(Path(tmpdir))
            assert result is None


class TestResolvePythonPathFromConfig:
    """Test Python path resolution from configuration."""

    def test_relative_path(self):
        """Test resolution of relative Python path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            venv_dir = base_dir / ".venv"
            venv_dir.mkdir()

            config = {"python_path": ".venv"}
            result = resolve_python_path_from_config(config, base_dir)
            assert result == str(venv_dir.resolve())

    def test_absolute_path(self):
        """Test handling of absolute Python path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            venv_dir = Path(tmpdir) / "venv"
            venv_dir.mkdir()

            config = {"python_path": str(venv_dir)}
            result = resolve_python_path_from_config(config, Path("/some/base"))
            assert result == str(venv_dir)

    def test_nonexistent_path(self):
        """Test handling of nonexistent Python path."""
        config = {"python_path": "/nonexistent/path"}
        result = resolve_python_path_from_config(config, Path("/tmp"))
        assert result is None

    def test_no_python_path_in_config(self):
        """Test handling of configuration without python_path."""
        config = {"other_key": "value"}
        result = resolve_python_path_from_config(config, Path("/tmp"))
        assert result is None


class TestGetPwdEnvironment:
    """Test PWD environment variable handling."""

    @patch.dict(os.environ, {"PWD": "/tmp"}, clear=True)
    def test_pwd_with_venv(self):
        """Test detection of venv in PWD directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            venv_dir = Path(tmpdir) / ".venv"
            venv_dir.mkdir()
            (venv_dir / "bin").mkdir()
            (venv_dir / "bin" / "python").touch()

            with patch.dict(os.environ, {"PWD": tmpdir}):
                result = get_pwd_environment()
                assert result == str(venv_dir)

    @patch.dict(os.environ, {}, clear=True)
    def test_no_pwd_set(self):
        """Test handling when PWD is not set."""
        result = get_pwd_environment()
        assert result is None


class TestGetSearchPathsFromEnv:
    """Test MCPYDOC_SEARCH_PATHS environment variable handling."""

    @patch.dict(os.environ, {}, clear=True)
    def test_no_search_paths(self):
        """Test when MCPYDOC_SEARCH_PATHS is not set."""
        result = get_search_paths_from_env()
        assert result == []

    @patch.dict(os.environ, {"MCPYDOC_SEARCH_PATHS": "/tmp"}, clear=True)
    def test_single_search_path(self):
        """Test single search path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            venv_dir = Path(tmpdir) / ".venv"
            venv_dir.mkdir()
            (venv_dir / "bin").mkdir()
            (venv_dir / "bin" / "python").touch()

            with patch.dict(os.environ, {"MCPYDOC_SEARCH_PATHS": tmpdir}):
                result = get_search_paths_from_env()
                assert str(venv_dir) in result

    @patch.dict(os.environ, {"MCPYDOC_SEARCH_PATHS": "/tmp,/var"}, clear=True)
    def test_multiple_search_paths(self):
        """Test multiple comma-separated search paths."""
        result = get_search_paths_from_env()
        # Just verify it doesn't crash with multiple paths
        assert isinstance(result, list)


class TestGetActivePythonEnvironments:
    """Test main environment detection function."""

    @patch.dict(os.environ, {"MCPYDOC_PYTHON_PATH": "/tmp"}, clear=True)
    def test_manual_override_priority(self):
        """Test that MCPYDOC_PYTHON_PATH has highest priority."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.dict(os.environ, {"MCPYDOC_PYTHON_PATH": tmpdir}):
                result = get_active_python_environments(use_cache=False)
                # Manual path should be first
                assert tmpdir in result[0]

    @patch.dict(os.environ, {"VIRTUAL_ENV": "/tmp/venv"}, clear=True)
    def test_virtual_env_detection(self):
        """Test VIRTUAL_ENV environment variable detection."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.dict(os.environ, {"VIRTUAL_ENV": tmpdir}):
                result = get_active_python_environments(use_cache=False)
                # Resolve paths for comparison (macOS /var -> /private/var symlink)
                resolved_tmpdir = str(Path(tmpdir).resolve())
                resolved_results = [str(Path(r).resolve()) for r in result]
                assert resolved_tmpdir in resolved_results

    def test_returns_list(self):
        """Test that function returns a list."""
        result = get_active_python_environments(use_cache=False)
        assert isinstance(result, list)
        assert len(result) > 0

    def test_no_duplicates(self):
        """Test that returned paths have no duplicates."""
        result = get_active_python_environments(use_cache=False)
        # Normalize and check for duplicates
        normalized = [str(Path(p).resolve()) for p in result]
        assert len(normalized) == len(set(normalized))

    def test_caching_works(self):
        """Test that caching mechanism works."""
        # First call without cache
        result1 = get_active_python_environments(use_cache=False)

        # Second call with cache (default)
        result2 = get_active_python_environments(use_cache=True)

        # Should return same results
        assert result1 == result2


class TestSearchCommonProjectDirectories:
    """Test searching common project directories."""

    def test_returns_list(self):
        """Test that function returns a list."""
        result = search_common_project_directories()
        assert isinstance(result, list)

    def test_respects_nonexistent_directories(self):
        """Test that function handles nonexistent directories gracefully."""
        # Should not crash even if common directories don't exist
        result = search_common_project_directories()
        assert isinstance(result, list)


class TestFindVenvInDirectory:
    """Test virtual environment discovery in directories."""

    def test_finds_dot_venv(self):
        """Test finding .venv directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            venv_dir = Path(tmpdir) / ".venv"
            venv_dir.mkdir()
            (venv_dir / "bin").mkdir()
            (venv_dir / "bin" / "python").touch()

            result = find_venv_in_directory(Path(tmpdir))
            assert result == str(venv_dir)

    def test_finds_venv(self):
        """Test finding venv directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            venv_dir = Path(tmpdir) / "venv"
            venv_dir.mkdir()
            (venv_dir / "bin").mkdir()
            (venv_dir / "bin" / "python").touch()

            result = find_venv_in_directory(Path(tmpdir))
            assert result == str(venv_dir)

    def test_no_venv_found(self):
        """Test handling when no venv is found."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = find_venv_in_directory(Path(tmpdir))
            assert result is None

    def test_nonexistent_directory(self):
        """Test handling of nonexistent directory."""
        result = find_venv_in_directory(Path("/nonexistent/path"))
        assert result is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
