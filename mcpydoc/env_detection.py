"""Environment detection utilities for MCPyDoc.

This module provides intelligent detection of Python environments,
prioritizing the working directory's environment over isolated pipx/uvx environments.

Note: For package manager-aware introspection (uv, poetry, pipenv) that solves
Python version mismatch issues, see subprocess_introspection.py which uses
package managers to run introspection in the project's own Python environment.
"""

import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Cache for discovered environments
_environment_cache: Optional[List[str]] = None
_searched_directories: List[str] = []


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


def load_mcpydoc_config(directory: Path) -> Optional[Dict]:
    """Load .mcpydoc.json configuration from a directory.

    Args:
        directory: Directory to search for configuration file

    Returns:
        Configuration dictionary or None if not found
    """
    config_file = directory / ".mcpydoc.json"
    if config_file.exists():
        try:
            with open(config_file, "r") as f:
                config = json.load(f)
                logger.info(f"Loaded MCPyDoc configuration from {config_file}")
                return config
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Failed to load config from {config_file}: {e}")
    return None


def resolve_python_path_from_config(config: Dict, base_dir: Path) -> Optional[str]:
    """Resolve Python path from configuration.

    Args:
        config: Configuration dictionary
        base_dir: Base directory for resolving relative paths

    Returns:
        Resolved Python environment path or None
    """
    if "python_path" in config:
        python_path = config["python_path"]
        path_obj = Path(python_path)

        # Handle relative paths
        if not path_obj.is_absolute():
            path_obj = (base_dir / path_obj).resolve()

        if path_obj.exists():
            logger.info(f"Using Python path from config: {path_obj}")
            return str(path_obj)
        else:
            logger.warning(f"Config python_path does not exist: {path_obj}")

    return None


def get_client_roots_environment() -> Optional[str]:
    """Get Python environment from MCP client roots (automatic workspace detection).

    This checks if the MCP client has provided workspace roots via the roots
    capability, which allows zero-config workspace detection.

    Returns:
        Path to Python environment or None
    """
    try:
        # Import the module (not the variable) to get the current value
        from . import subprocess_introspection

        client_working_dir = subprocess_introspection._client_working_directory

        if client_working_dir is not None:
            logger.debug(f"Checking client root for venv: {client_working_dir}")
            # Check for venv in client root directory
            venv = find_venv_in_directory(client_working_dir)
            if venv:
                logger.info(f"Found venv in client root: {venv}")
                return venv

            # Check for .mcpydoc.json config
            config = load_mcpydoc_config(client_working_dir)
            if config:
                python_path = resolve_python_path_from_config(
                    config, client_working_dir
                )
                if python_path:
                    return python_path
    except ImportError as e:
        logger.debug(f"Could not import subprocess_introspection: {e}")

    return None


def get_pwd_environment() -> Optional[str]:
    """Get Python environment from PWD environment variable.

    The PWD environment variable often preserves the original working directory
    when processes are spawned, making it useful for detecting project environments.

    Returns:
        Path to Python environment or None
    """
    pwd = os.environ.get("PWD")
    if pwd:
        pwd_path = Path(pwd)
        if pwd_path.exists() and pwd_path.is_dir():
            # Check for venv in PWD directory
            venv = find_venv_in_directory(pwd_path)
            if venv:
                logger.info(f"Found venv in PWD: {venv}")
                return venv

            # Check for .mcpydoc.json config
            config = load_mcpydoc_config(pwd_path)
            if config:
                python_path = resolve_python_path_from_config(config, pwd_path)
                if python_path:
                    return python_path

    return None


def search_common_project_directories() -> List[str]:
    """Search common development directories for Python virtual environments.

    Returns:
        List of discovered Python environment paths
    """
    discovered = []
    home = Path.home()

    # Common project directory names
    common_dirs = ["projects", "dev", "code", "workspace", "work", "src", "repos"]

    for dir_name in common_dirs:
        project_dir = home / dir_name
        if not project_dir.exists() or not project_dir.is_dir():
            continue

        _searched_directories.append(str(project_dir))

        try:
            # Search immediate subdirectories (one level deep)
            for subdir in project_dir.iterdir():
                if not subdir.is_dir():
                    continue

                # Check for .mcpydoc.json first
                config = load_mcpydoc_config(subdir)
                if config:
                    python_path = resolve_python_path_from_config(config, subdir)
                    if python_path and python_path not in discovered:
                        discovered.append(python_path)
                        continue

                # Check for venv
                venv = find_venv_in_directory(subdir)
                if venv and venv not in discovered:
                    discovered.append(venv)
        except (PermissionError, OSError) as e:
            logger.debug(f"Could not search {project_dir}: {e}")
            continue

    if discovered:
        logger.info(
            f"Found {len(discovered)} environments in common project directories"
        )

    return discovered


def get_search_paths_from_env() -> List[str]:
    """Get additional search paths from MCPYDOC_SEARCH_PATHS environment variable.

    Returns:
        List of Python environment paths from custom search directories
    """
    discovered = []
    search_paths = os.environ.get("MCPYDOC_SEARCH_PATHS", "")

    if not search_paths:
        return discovered

    # Split by comma and search each path
    paths = [p.strip() for p in search_paths.split(",") if p.strip()]

    for path_str in paths:
        # Expand user home directory
        path_str = os.path.expanduser(path_str)
        path = Path(path_str)

        if not path.exists() or not path.is_dir():
            logger.warning(f"Search path does not exist: {path}")
            continue

        _searched_directories.append(str(path))

        # Check for .mcpydoc.json first
        config = load_mcpydoc_config(path)
        if config:
            python_path = resolve_python_path_from_config(config, path)
            if python_path and python_path not in discovered:
                discovered.append(python_path)
                continue

        # Check for venv
        venv = find_venv_in_directory(path)
        if venv and venv not in discovered:
            discovered.append(venv)

        # Search subdirectories
        try:
            for subdir in path.iterdir():
                if not subdir.is_dir():
                    continue

                config = load_mcpydoc_config(subdir)
                if config:
                    python_path = resolve_python_path_from_config(config, subdir)
                    if python_path and python_path not in discovered:
                        discovered.append(python_path)
                        continue

                venv = find_venv_in_directory(subdir)
                if venv and venv not in discovered:
                    discovered.append(venv)
        except (PermissionError, OSError) as e:
            logger.debug(f"Could not search subdirectories of {path}: {e}")

    if discovered:
        logger.info(f"Found {len(discovered)} environments from MCPYDOC_SEARCH_PATHS")

    return discovered


def get_searched_directories() -> List[str]:
    """Get list of directories that were searched for environments.

    Returns:
        List of searched directory paths
    """
    return _searched_directories.copy()


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


def get_active_python_environments(use_cache: bool = True) -> List[str]:
    """Get ordered list of Python environment paths to search for packages.

    This function implements intelligent environment detection with the following priority:
    1. MCP Client Roots (automatic workspace detection - zero config!)
    2. MCPYDOC_PYTHON_PATH environment variable (manual override)
    3. VIRTUAL_ENV environment variable (activated virtual environment)
    4. PWD environment variable + venv search
    5. Common project directories search (~/projects, ~/dev, etc.)
    6. MCPYDOC_SEARCH_PATHS custom directories
    7. Current working directory venv
    8. sys.executable's environment (if not in pipx/uvx)
    9. sys.prefix (fallback)

    Args:
        use_cache: If True, return cached results from previous calls
                   NOTE: Cache is bypassed when client roots are available
                   to ensure we always use the latest workspace.

    Returns:
        Ordered list of Python environment paths to search
    """
    global _environment_cache, _searched_directories

    # Check if client roots are available - if so, bypass cache
    # since we want to always use the latest workspace
    client_roots_env = get_client_roots_environment()

    # Return cached results if available AND no client roots
    if use_cache and _environment_cache is not None and client_roots_env is None:
        return _environment_cache.copy()

    # Reset searched directories tracking
    _searched_directories = []

    python_paths = []

    # 1. Check MCP Client Roots (automatic workspace detection - zero config!)
    if client_roots_env:
        logger.info(
            f"Using Python environment from MCP client roots: {client_roots_env}"
        )
        python_paths.append(client_roots_env)
        # Also track the client root directory as searched
        try:
            from . import subprocess_introspection

            if subprocess_introspection._client_working_directory is not None:
                _searched_directories.append(
                    str(subprocess_introspection._client_working_directory)
                )
        except ImportError:
            pass

    # 2. Check MCPYDOC_PYTHON_PATH for manual override
    manual_path = os.environ.get("MCPYDOC_PYTHON_PATH")
    if manual_path:
        manual_path = os.path.expanduser(manual_path)
        manual_path_obj = Path(manual_path)
        if manual_path_obj.exists():
            logger.info(
                f"Using manual Python path from MCPYDOC_PYTHON_PATH: {manual_path}"
            )
            if manual_path not in python_paths:
                python_paths.append(manual_path)
        else:
            logger.warning(
                f"MCPYDOC_PYTHON_PATH set but path does not exist: {manual_path}"
            )

    # 3. Check VIRTUAL_ENV environment variable
    virtual_env = os.environ.get("VIRTUAL_ENV")
    if virtual_env:
        virtual_env_path = Path(virtual_env)
        if virtual_env_path.exists():
            logger.info(f"Found active virtual environment: {virtual_env}")
            if virtual_env not in python_paths:
                python_paths.append(virtual_env)
        else:
            logger.warning(f"VIRTUAL_ENV set but path does not exist: {virtual_env}")

    # 4. Check PWD environment variable
    pwd_env = get_pwd_environment()
    if pwd_env and pwd_env not in python_paths:
        python_paths.append(pwd_env)

    # 5. Search common project directories
    common_envs = search_common_project_directories()
    for env in common_envs:
        if env not in python_paths:
            python_paths.append(env)

    # 6. Check MCPYDOC_SEARCH_PATHS for custom directories
    search_path_envs = get_search_paths_from_env()
    for env in search_path_envs:
        if env not in python_paths:
            python_paths.append(env)

    # 7. Search current working directory for venv
    cwd = Path.cwd()
    _searched_directories.append(str(cwd))

    # Check for .mcpydoc.json in cwd first
    config = load_mcpydoc_config(cwd)
    if config:
        python_path = resolve_python_path_from_config(config, cwd)
        if python_path and python_path not in python_paths:
            python_paths.append(python_path)

    # Check for venv in cwd
    venv_in_cwd = find_venv_in_directory(cwd)
    if venv_in_cwd and venv_in_cwd not in python_paths:
        python_paths.append(venv_in_cwd)

    # 8. Check sys.executable's environment (if not in pipx/uvx)
    sys_exec_prefix = Path(sys.executable).parent.parent
    if not is_pipx_environment(str(sys_exec_prefix)):
        if str(sys_exec_prefix) not in python_paths:
            logger.info(f"Using sys.executable environment: {sys_exec_prefix}")
            python_paths.append(str(sys_exec_prefix))
    else:
        logger.info(
            f"Detected pipx/uvx environment, skipping sys.executable: {sys_exec_prefix}"
        )

    # 9. Fallback to sys.prefix (but log if it's pipx/uvx)
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

    # Cache the results
    _environment_cache = unique_paths

    return unique_paths
