"""Environment detection utilities for MCPyDoc.

This module provides intelligent detection of Python environments,
prioritizing the working directory's environment over isolated pipx/uvx environments.
"""

import logging
import os
import sys
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)


def is_pipx_environment(path: str) -> bool:
    """Detect if a path belongs to a pipx or uvx isolated environment.

    Args:
        path: Path to check

    Returns:
        True if the path is in a pipx/uvx isolated environment
    """
    path_str = str(path).lower()

    # Common pipx/uvx paths
    pipx_indicators = [
        ".local/pipx/venvs",
        ".local/share/pipx",
        "pipx/venvs",
        ".local/uvx",
        "uvx/venvs",
    ]

    return any(indicator in path_str for indicator in pipx_indicators)


def find_venv_in_directory(directory: Path) -> Optional[str]:
    """Find a virtual environment in the given directory.

    Args:
        directory: Directory to search for virtual environments

    Returns:
        Path to the Python executable in the venv, or None if not found
    """
    if not directory.exists() or not directory.is_dir():
        return None

    # Common venv folder names
    venv_names = [".venv", "venv", "env", ".env"]

    for venv_name in venv_names:
        venv_path = directory / venv_name
        if not venv_path.exists():
            continue

        # Check for Python executable
        if sys.platform == "win32":
            python_exe = venv_path / "Scripts" / "python.exe"
        else:
            python_exe = venv_path / "bin" / "python"

        if python_exe.exists():
            logger.info(f"Found virtual environment at {venv_path}")
            return str(venv_path)

    # Check for Poetry environment
    poetry_toml = directory / "poetry.toml"
    pyproject_toml = directory / "pyproject.toml"

    if poetry_toml.exists() or pyproject_toml.exists():
        # Poetry typically uses .venv in the project directory
        # or a global cache location
        poetry_venv = directory / ".venv"
        if poetry_venv.exists():
            if sys.platform == "win32":
                python_exe = poetry_venv / "Scripts" / "python.exe"
            else:
                python_exe = poetry_venv / "bin" / "python"

            if python_exe.exists():
                logger.info(f"Found Poetry virtual environment at {poetry_venv}")
                return str(poetry_venv)

    return None


def get_site_packages_paths(python_paths: List[str]) -> List[str]:
    """Convert Python environment paths to site-packages paths.

    Args:
        python_paths: List of Python environment root paths

    Returns:
        List of site-packages directory paths
    """
    site_packages = []

    for path in python_paths:
        path_obj = Path(path)

        # Try common site-packages locations
        if sys.platform == "win32":
            # Windows: <venv>/Lib/site-packages
            sp_path = path_obj / "Lib" / "site-packages"
        else:
            # Unix: <venv>/lib/pythonX.Y/site-packages
            lib_path = path_obj / "lib"
            if lib_path.exists():
                # Find pythonX.Y directory
                for item in lib_path.iterdir():
                    if item.is_dir() and item.name.startswith("python"):
                        sp_path = item / "site-packages"
                        if sp_path.exists():
                            site_packages.append(str(sp_path))
                            break
                continue
            else:
                sp_path = path_obj / "site-packages"

        if sp_path.exists():
            site_packages.append(str(sp_path))

    return site_packages


def get_active_python_environments() -> List[str]:
    """Get ordered list of Python environment paths to search for packages.

    This function implements intelligent environment detection with the following priority:
    1. MCPYDOC_PYTHON_PATH environment variable (manual override)
    2. VIRTUAL_ENV environment variable (activated virtual environment)
    3. Virtual environment in current working directory
    4. sys.executable's environment (if not in pipx/uvx)
    5. sys.prefix (fallback)

    Returns:
        Ordered list of Python environment paths to search
    """
    python_paths = []

    # 1. Check MCPYDOC_PYTHON_PATH for manual override
    manual_path = os.environ.get("MCPYDOC_PYTHON_PATH")
    if manual_path:
        manual_path_obj = Path(manual_path)
        if manual_path_obj.exists():
            logger.info(
                f"Using manual Python path from MCPYDOC_PYTHON_PATH: {manual_path}"
            )
            python_paths.append(manual_path)
        else:
            logger.warning(
                f"MCPYDOC_PYTHON_PATH set but path does not exist: {manual_path}"
            )

    # 2. Check VIRTUAL_ENV environment variable
    virtual_env = os.environ.get("VIRTUAL_ENV")
    if virtual_env:
        virtual_env_path = Path(virtual_env)
        if virtual_env_path.exists():
            logger.info(f"Found active virtual environment: {virtual_env}")
            python_paths.append(virtual_env)
        else:
            logger.warning(f"VIRTUAL_ENV set but path does not exist: {virtual_env}")

    # 3. Search current working directory for venv
    cwd = Path.cwd()
    venv_in_cwd = find_venv_in_directory(cwd)
    if venv_in_cwd and venv_in_cwd not in python_paths:
        python_paths.append(venv_in_cwd)

    # 4. Check sys.executable's environment (if not in pipx/uvx)
    sys_exec_prefix = Path(sys.executable).parent.parent
    if not is_pipx_environment(str(sys_exec_prefix)):
        if str(sys_exec_prefix) not in python_paths:
            logger.info(f"Using sys.executable environment: {sys_exec_prefix}")
            python_paths.append(str(sys_exec_prefix))
    else:
        logger.info(
            f"Detected pipx/uvx environment, skipping sys.executable: {sys_exec_prefix}"
        )

    # 5. Fallback to sys.prefix (but log if it's pipx/uvx)
    if str(sys.prefix) not in python_paths:
        if is_pipx_environment(sys.prefix):
            logger.warning(
                f"Using pipx/uvx isolated environment as fallback: {sys.prefix}. "
                "Consider activating a virtual environment or setting MCPYDOC_PYTHON_PATH."
            )
        python_paths.append(sys.prefix)

    # Remove duplicates while preserving order
    seen = set()
    unique_paths = []
    for path in python_paths:
        path_normalized = str(Path(path).resolve())
        if path_normalized not in seen:
            seen.add(path_normalized)
            unique_paths.append(path_normalized)

    logger.info(f"Python environment search order: {unique_paths}")
    return unique_paths
