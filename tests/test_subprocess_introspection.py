"""Tests for subprocess-based package introspection."""

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from mcpydoc.subprocess_introspection import (
    _find_project_root,
    _is_command_available,
    clear_cache,
    detect_package_manager,
    get_working_directory,
    introspect_package_info,
    introspect_symbol,
    is_subprocess_available,
    search_symbols_subprocess,
)


@pytest.fixture
def mock_project_dir(tmp_path):
    """Create a mock project directory with package manager files."""
    return tmp_path


@pytest.fixture
def uv_project(tmp_path):
    """Create a mock uv project directory."""
    uv_lock = tmp_path / "uv.lock"
    uv_lock.write_text("")
    return tmp_path


@pytest.fixture
def poetry_project(tmp_path):
    """Create a mock poetry project directory."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("[tool.poetry]\nname = 'test'\n")
    return tmp_path


@pytest.fixture
def pipenv_project(tmp_path):
    """Create a mock pipenv project directory."""
    pipfile = tmp_path / "Pipfile"
    pipfile.write_text("")
    return tmp_path


def test_find_project_root(uv_project):
    """Test finding project root from subdirectory."""
    # Create a subdirectory
    subdir = uv_project / "src" / "package"
    subdir.mkdir(parents=True)

    # Should find project root from subdirectory
    result = _find_project_root(subdir)
    assert result == uv_project


def test_find_project_root_no_project(tmp_path):
    """Test when no project root is found."""
    result = _find_project_root(tmp_path)
    assert result is None


@patch("mcpydoc.subprocess_introspection._is_command_available")
def test_detect_package_manager_uv(mock_cmd_available, uv_project):
    """Test detection of uv package manager."""
    mock_cmd_available.return_value = True
    clear_cache()

    result = detect_package_manager(uv_project)

    assert result is not None
    runner, project_root = result
    assert runner == ["uv", "run", "python"]
    assert project_root == uv_project


@patch("mcpydoc.subprocess_introspection._is_command_available")
def test_detect_package_manager_poetry(mock_cmd_available, poetry_project):
    """Test detection of poetry package manager."""
    mock_cmd_available.return_value = True
    clear_cache()

    result = detect_package_manager(poetry_project)

    assert result is not None
    runner, project_root = result
    assert runner == ["poetry", "run", "python"]
    assert project_root == poetry_project


@patch("mcpydoc.subprocess_introspection._is_command_available")
def test_detect_package_manager_pipenv(mock_cmd_available, pipenv_project):
    """Test detection of pipenv package manager."""
    mock_cmd_available.return_value = True
    clear_cache()

    result = detect_package_manager(pipenv_project)

    assert result is not None
    runner, project_root = result
    assert runner == ["pipenv", "run", "python"]
    assert project_root == pipenv_project


def test_detect_package_manager_none(mock_project_dir):
    """Test when no package manager is detected."""
    clear_cache()
    result = detect_package_manager(mock_project_dir)
    assert result is None


@patch("mcpydoc.subprocess_introspection._is_command_available")
def test_detect_package_manager_command_not_available(mock_cmd_available, uv_project):
    """Test when package manager command is not available."""
    mock_cmd_available.return_value = False
    clear_cache()

    result = detect_package_manager(uv_project)

    # Should return None since 'uv' command is not available
    assert result is None


@patch("mcpydoc.subprocess_introspection._is_command_available")
def test_detect_package_manager_from_subdirectory(mock_cmd_available, uv_project):
    """Test package manager detection from subdirectory."""
    mock_cmd_available.return_value = True
    clear_cache()

    # Create a subdirectory
    subdir = uv_project / "src" / "mypackage"
    subdir.mkdir(parents=True)

    result = detect_package_manager(subdir)

    assert result is not None
    runner, project_root = result
    assert runner == ["uv", "run", "python"]
    assert project_root == uv_project  # Should find root, not subdir


@patch("mcpydoc.subprocess_introspection._is_command_available")
def test_detect_package_manager_caching(mock_cmd_available, uv_project):
    """Test that package manager detection is cached."""
    mock_cmd_available.return_value = True
    clear_cache()

    # First call
    result1 = detect_package_manager(uv_project)
    # Second call should use cache
    result2 = detect_package_manager(uv_project)

    assert result1 == result2
    assert result1 is not None
    assert result1[0] == ["uv", "run", "python"]


@patch("mcpydoc.subprocess_introspection._is_command_available")
def test_introspect_package_info_success(mock_cmd_available, uv_project):
    """Test successful package info introspection via subprocess."""
    mock_cmd_available.return_value = True
    clear_cache()

    mock_output = json.dumps(
        {
            "name": "pytest",
            "version": "7.4.0",
            "summary": "Testing framework",
            "author": "Test Author",
            "license": "MIT",
            "location": "/path/to/package",
            "is_builtin": False,
        }
    )

    with patch("mcpydoc.subprocess_introspection.subprocess.run") as mock_run:
        mock_run.return_value = Mock(returncode=0, stdout=mock_output)

        result = introspect_package_info("pytest", uv_project)

        assert result is not None
        assert result["name"] == "pytest"
        assert result["version"] == "7.4.0"
        assert result["summary"] == "Testing framework"

        # Verify subprocess was called with correct command
        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert call_args[0][0][:3] == ["uv", "run", "python"]


@patch("mcpydoc.subprocess_introspection._is_command_available")
def test_introspect_package_info_failure(mock_cmd_available, uv_project):
    """Test package info introspection when subprocess fails."""
    mock_cmd_available.return_value = True
    clear_cache()

    with patch("mcpydoc.subprocess_introspection.subprocess.run") as mock_run:
        mock_run.return_value = Mock(returncode=1, stderr="Error message")

        result = introspect_package_info("nonexistent", uv_project)

        assert result is None


@patch("mcpydoc.subprocess_introspection._is_command_available")
def test_introspect_package_info_timeout(mock_cmd_available, uv_project):
    """Test package info introspection when subprocess times out."""
    mock_cmd_available.return_value = True
    clear_cache()

    with patch("mcpydoc.subprocess_introspection.subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.TimeoutExpired("cmd", 15)

        result = introspect_package_info("pytest", uv_project)

        assert result is None


def test_introspect_package_info_no_package_manager(mock_project_dir):
    """Test package info introspection when no package manager is detected."""
    clear_cache()
    result = introspect_package_info("pytest", mock_project_dir)
    assert result is None


@patch("mcpydoc.subprocess_introspection._is_command_available")
def test_introspect_symbol_success(mock_cmd_available, uv_project):
    """Test successful symbol introspection via subprocess."""
    mock_cmd_available.return_value = True
    clear_cache()

    mock_output = json.dumps(
        {
            "name": "main",
            "qualname": "pytest.main",
            "kind": "function",
            "module": "pytest",
            "docstring": "Main entry point",
            "signature": "(args=None)",
            "source": "def main(args=None):\n    pass",
        }
    )

    with patch("mcpydoc.subprocess_introspection.subprocess.run") as mock_run:
        mock_run.return_value = Mock(returncode=0, stdout=mock_output)

        result = introspect_symbol("pytest", "main", uv_project)

        assert result is not None
        assert result["name"] == "main"
        assert result["kind"] == "function"
        assert result["signature"] == "(args=None)"


@patch("mcpydoc.subprocess_introspection._is_command_available")
def test_introspect_symbol_failure(mock_cmd_available, uv_project):
    """Test symbol introspection when subprocess fails."""
    mock_cmd_available.return_value = True
    clear_cache()

    with patch("mcpydoc.subprocess_introspection.subprocess.run") as mock_run:
        mock_run.return_value = Mock(returncode=1, stderr="Symbol not found")

        result = introspect_symbol("pytest", "nonexistent", uv_project)

        assert result is None


@patch("mcpydoc.subprocess_introspection._is_command_available")
def test_search_symbols_subprocess_success(mock_cmd_available, uv_project):
    """Test successful symbol search via subprocess."""
    mock_cmd_available.return_value = True
    clear_cache()

    mock_symbols = [
        {
            "name": "main",
            "qualname": "pytest.main",
            "kind": "function",
            "module": "pytest",
            "docstring": "Main function",
            "signature": "()",
        },
        {
            "name": "fixture",
            "qualname": "pytest.fixture",
            "kind": "function",
            "module": "pytest",
            "docstring": "Fixture decorator",
            "signature": "()",
        },
    ]
    mock_output = json.dumps({"symbols": mock_symbols, "count": 2})

    with patch("mcpydoc.subprocess_introspection.subprocess.run") as mock_run:
        mock_run.return_value = Mock(returncode=0, stdout=mock_output)

        result = search_symbols_subprocess("pytest", None, uv_project)

        assert result is not None
        assert len(result) == 2
        assert result[0]["name"] == "main"
        assert result[1]["name"] == "fixture"


@patch("mcpydoc.subprocess_introspection._is_command_available")
def test_search_symbols_subprocess_with_pattern(mock_cmd_available, uv_project):
    """Test symbol search with pattern via subprocess."""
    mock_cmd_available.return_value = True
    clear_cache()

    mock_symbols = [
        {
            "name": "fixture",
            "qualname": "pytest.fixture",
            "kind": "function",
            "module": "pytest",
            "docstring": "Fixture decorator",
            "signature": "()",
        }
    ]
    mock_output = json.dumps({"symbols": mock_symbols, "count": 1})

    with patch("mcpydoc.subprocess_introspection.subprocess.run") as mock_run:
        mock_run.return_value = Mock(returncode=0, stdout=mock_output)

        result = search_symbols_subprocess("pytest", "fixture", uv_project)

        assert result is not None
        assert len(result) == 1
        assert result[0]["name"] == "fixture"

        # Verify pattern was passed to subprocess
        call_args = mock_run.call_args
        assert "fixture" in call_args[0][0][-1]  # In the script


@patch("mcpydoc.subprocess_introspection._is_command_available")
def test_search_symbols_subprocess_failure(mock_cmd_available, uv_project):
    """Test symbol search when subprocess fails."""
    mock_cmd_available.return_value = True
    clear_cache()

    with patch("mcpydoc.subprocess_introspection.subprocess.run") as mock_run:
        mock_run.return_value = Mock(returncode=1, stderr="Package not found")

        result = search_symbols_subprocess("nonexistent", None, uv_project)

        assert result is None


@patch("mcpydoc.subprocess_introspection._is_command_available")
def test_caching_behavior(mock_cmd_available, uv_project):
    """Test that introspection results are cached."""
    mock_cmd_available.return_value = True
    clear_cache()

    mock_output = json.dumps(
        {
            "name": "pytest",
            "version": "7.4.0",
            "summary": "Testing framework",
            "author": "Test Author",
            "license": "MIT",
            "location": "/path/to/package",
            "is_builtin": False,
        }
    )

    with patch("mcpydoc.subprocess_introspection.subprocess.run") as mock_run:
        mock_run.return_value = Mock(returncode=0, stdout=mock_output)

        # First call - should execute subprocess
        result1 = introspect_package_info("pytest", uv_project)
        assert mock_run.call_count == 1

        # Second call - should use cache (no additional subprocess call)
        result2 = introspect_package_info("pytest", uv_project)
        assert mock_run.call_count == 1  # Not called again

        assert result1 == result2


def test_get_working_directory_from_pwd(tmp_path):
    """Test getting working directory from PWD environment variable."""
    import os

    # Create a temp directory and set PWD to it
    with patch.dict(os.environ, {"PWD": str(tmp_path)}):
        result = get_working_directory()
        assert result == tmp_path


def test_get_working_directory_fallback():
    """Test falling back to cwd when PWD is not set."""
    import os

    with patch.dict(os.environ, {"PWD": ""}, clear=False):
        result = get_working_directory()
        assert result == Path.cwd()


def test_clear_cache(uv_project):
    """Test that clear_cache removes all cached data."""
    # First populate the cache
    clear_cache()  # Start fresh

    # This should add to cache
    with patch(
        "mcpydoc.subprocess_introspection._is_command_available", return_value=True
    ):
        detect_package_manager(uv_project)

    # Now clear
    clear_cache()

    # Verify by checking that detection runs again (would use cache otherwise)
    with patch(
        "mcpydoc.subprocess_introspection._is_command_available", return_value=True
    ) as mock:
        detect_package_manager(uv_project)
        # If cache was used, _is_command_available wouldn't be called again
        mock.assert_called()


@patch("mcpydoc.subprocess_introspection._is_command_available")
def test_is_subprocess_available(mock_cmd_available, uv_project, mock_project_dir):
    """Test the is_subprocess_available helper."""
    mock_cmd_available.return_value = True
    clear_cache()

    # Should be available for uv project
    assert is_subprocess_available(uv_project) is True

    clear_cache()

    # Should not be available for empty directory (mock _find_project_root to prevent
    # searching up to parent directories which might find the test runner's project)
    with patch(
        "mcpydoc.subprocess_introspection._find_project_root", return_value=None
    ):
        # Clear cache again inside patch context to ensure fresh detection
        clear_cache()
        assert is_subprocess_available(mock_project_dir) is False


@pytest.mark.integration
def test_integration_with_analyzer():
    """Integration test: verify analyzer uses subprocess introspection."""
    from mcpydoc.analyzer import PackageAnalyzer

    # Create analyzer with subprocess enabled
    analyzer = PackageAnalyzer(enable_subprocess=True)

    # Verify subprocess is enabled
    assert analyzer._subprocess_enabled is True
    assert analyzer._working_directory is not None


@pytest.mark.integration
def test_integration_fallback_to_direct_import():
    """Integration test: verify fallback to direct import works."""
    from mcpydoc.analyzer import PackageAnalyzer

    # Create analyzer with subprocess disabled
    analyzer = PackageAnalyzer(enable_subprocess=False)

    # Verify subprocess is disabled
    assert analyzer._subprocess_enabled is False


@pytest.mark.integration
def test_integration_subprocess_with_real_package():
    """Integration test: test subprocess introspection with a real package (if available)."""
    from mcpydoc.subprocess_introspection import detect_package_manager

    # Check if we're in a project with a package manager
    working_dir = get_working_directory()
    pm_result = detect_package_manager(working_dir)

    if pm_result:
        runner, project_root = pm_result
        assert isinstance(runner, list)
        assert isinstance(project_root, Path)
        assert project_root.exists()
    else:
        pytest.skip("No package manager detected, skipping real subprocess test")
