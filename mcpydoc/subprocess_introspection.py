"""Subprocess-based package introspection for MCPyDoc.

This module provides introspection capabilities by running Python code in the
project's own environment via package managers (uv, poetry, pipenv). This solves:
1. Python version mismatch issues (C extensions)
2. Workspace/monorepo package boundary handling
"""

import json
import logging
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Cache for package manager detection per directory
_package_manager_cache: Dict[str, Optional[Tuple[List[str], Path]]] = {}

# Cache for introspection results (with simple TTL via dictionary size limit)
_introspection_cache: Dict[str, Any] = {}
_CACHE_SIZE_LIMIT = 100


def _add_to_cache(key: str, value: Any) -> None:
    """Add item to cache with size limit."""
    if len(_introspection_cache) >= _CACHE_SIZE_LIMIT:
        # Simple FIFO eviction
        _introspection_cache.pop(next(iter(_introspection_cache)))
    _introspection_cache[key] = value


def _get_from_cache(key: str) -> Optional[Any]:
    """Get item from cache."""
    return _introspection_cache.get(key)


def _is_command_available(command: str) -> bool:
    """Check if a command is available on the system."""
    return shutil.which(command) is not None


def _find_project_root(start_dir: Path) -> Optional[Path]:
    """Find the project root by searching for package manager files in parent directories.

    Args:
        start_dir: Directory to start searching from

    Returns:
        Path to project root, or None if not found
    """
    current = start_dir.resolve()

    # Search up to 10 levels to avoid infinite loops
    for _ in range(10):
        # Check for any package manager files
        if (current / "uv.lock").exists():
            return current
        if (current / "poetry.lock").exists():
            return current
        if (current / "Pipfile").exists() or (current / "Pipfile.lock").exists():
            return current
        if (current / "pyproject.toml").exists():
            return current

        parent = current.parent
        if parent == current:
            # Reached filesystem root
            break
        current = parent

    return None


def detect_package_manager(directory: Path) -> Optional[Tuple[List[str], Path]]:
    """Detect which package manager to use for a directory.

    Searches the given directory and its parents for package manager files.
    Also verifies the package manager command is available on the system.

    Args:
        directory: Directory to start searching from

    Returns:
        Tuple of (command list, project root path), or None if not detected
    """
    cache_key = str(directory.resolve())

    # Check cache first
    if cache_key in _package_manager_cache:
        return _package_manager_cache[cache_key]

    # Find project root by searching parent directories
    project_root = _find_project_root(directory)
    if project_root is None:
        logger.debug(f"No project root found starting from {directory}")
        _package_manager_cache[cache_key] = None
        return None

    result = None

    # Check for uv (pyproject.toml with [tool.uv] or uv.lock)
    uv_lock = project_root / "uv.lock"
    pyproject = project_root / "pyproject.toml"

    if uv_lock.exists():
        if _is_command_available("uv"):
            logger.info(f"Detected uv project at {project_root} (uv.lock)")
            result = (["uv", "run", "python"], project_root)
        else:
            logger.warning(
                f"uv.lock found at {project_root} but 'uv' command not available"
            )

    if result is None and pyproject.exists():
        try:
            with open(pyproject, "r") as f:
                content = f.read()
                if "[tool.uv]" in content:
                    if _is_command_available("uv"):
                        logger.info(
                            f"Detected uv project at {project_root} ([tool.uv])"
                        )
                        result = (["uv", "run", "python"], project_root)
                    else:
                        logger.warning(
                            f"[tool.uv] found but 'uv' command not available"
                        )
                elif "[tool.poetry]" in content:
                    if _is_command_available("poetry"):
                        logger.info(
                            f"Detected poetry project at {project_root} ([tool.poetry])"
                        )
                        result = (["poetry", "run", "python"], project_root)
                    else:
                        logger.warning(
                            f"[tool.poetry] found but 'poetry' command not available"
                        )
        except (IOError, OSError) as e:
            logger.debug(f"Could not read {pyproject}: {e}")

    # Check for poetry.lock if not already detected
    if result is None:
        poetry_lock = project_root / "poetry.lock"
        if poetry_lock.exists():
            if _is_command_available("poetry"):
                logger.info(f"Detected poetry project at {project_root} (poetry.lock)")
                result = (["poetry", "run", "python"], project_root)
            else:
                logger.warning(f"poetry.lock found but 'poetry' command not available")

    # Check for pipenv (Pipfile or Pipfile.lock)
    if result is None:
        pipfile = project_root / "Pipfile"
        pipfile_lock = project_root / "Pipfile.lock"
        if pipfile.exists() or pipfile_lock.exists():
            if _is_command_available("pipenv"):
                logger.info(f"Detected pipenv project at {project_root}")
                result = (["pipenv", "run", "python"], project_root)
            else:
                logger.warning(f"Pipfile found but 'pipenv' command not available")

    # Cache the result
    _package_manager_cache[cache_key] = result

    if result:
        logger.info(f"Package manager detected: {' '.join(result[0])} at {result[1]}")
    else:
        logger.debug(f"No package manager detected at {directory}")

    return result


# Introspection script for package info
PACKAGE_INFO_SCRIPT = """
import json
import sys
from importlib import metadata
from pathlib import Path

package_name = {package_name!r}

try:
    # Check if it's a built-in module
    if package_name in sys.builtin_module_names:
        result = {{
            "name": package_name,
            "version": f"{{sys.version_info.major}}.{{sys.version_info.minor}}.{{sys.version_info.micro}}",
            "summary": "Built-in Python module",
            "author": "Python Software Foundation",
            "license": "Python Software Foundation License",
            "location": None,
            "is_builtin": True
        }}
    else:
        # Try to get package metadata
        dist = metadata.distribution(package_name)
        result = {{
            "name": dist.metadata["Name"],
            "version": dist.metadata["Version"],
            "summary": dist.metadata.get("Summary"),
            "author": dist.metadata.get("Author"),
            "license": dist.metadata.get("License"),
            "location": str(Path(dist.locate_file(""))),
            "is_builtin": False
        }}
    print(json.dumps(result))
except Exception as e:
    error = {{"error": str(e), "type": type(e).__name__}}
    print(json.dumps(error))
    sys.exit(1)
"""


# Introspection script for symbol info
SYMBOL_INFO_SCRIPT = """
import json
import sys
import inspect
from importlib import import_module

package_name = {package_name!r}
symbol_path = {symbol_path!r}

try:
    # Import the module
    if "." in symbol_path:
        parts = symbol_path.split(".")
        # Try treating first part as module
        try:
            module = import_module(f"{{package_name}}.{{parts[0]}}")
            obj = module
            for part in parts[1:]:
                obj = getattr(obj, part)
        except (ImportError, AttributeError):
            # Try as nested symbols in main package
            module = import_module(package_name)
            obj = module
            for part in parts:
                obj = getattr(obj, part)
    else:
        module = import_module(package_name)
        obj = getattr(module, symbol_path)
    
    # Determine kind
    if inspect.ismodule(obj):
        kind = "module"
    elif inspect.isclass(obj):
        kind = "class"
    elif inspect.isfunction(obj):
        kind = "function"
    elif inspect.ismethod(obj):
        kind = "method"
    elif inspect.isbuiltin(obj):
        kind = "builtin"
    else:
        kind = "other"
    
    # Get signature
    signature = None
    if callable(obj):
        try:
            signature = str(inspect.signature(obj))
        except (ValueError, TypeError):
            pass
    
    # Get source code
    source = None
    try:
        source = inspect.getsource(obj)
    except (TypeError, OSError, AttributeError):
        pass
    
    # Get docstring - try to resolve inherited docstrings for methods
    docstring = getattr(obj, "__doc__", None)
    if docstring is None and kind in ("method", "function") and hasattr(obj, "__func__"):
        # Try to get from wrapped function
        docstring = getattr(obj.__func__, "__doc__", None)
    if docstring is None and kind in ("method", "function"):
        # Try to resolve from parent class via MRO
        method_name = getattr(obj, "__name__", None)
        if method_name:
            for cls in inspect.getmro(type(obj)) if hasattr(type(obj), "__mro__") else []:
                parent_method = getattr(cls, method_name, None)
                if parent_method and getattr(parent_method, "__doc__", None):
                    docstring = parent_method.__doc__
                    break
    
    # For classes, include a summary of methods
    methods = None
    if kind == "class":
        methods = []
        for name, method in inspect.getmembers(obj, predicate=lambda x: inspect.isfunction(x) or inspect.ismethod(x)):
            if name.startswith("_") and not name.startswith("__"):
                continue  # Skip private methods but keep dunder
            if name.startswith("__") and name not in ("__init__", "__call__", "__enter__", "__exit__", "__aenter__", "__aexit__"):
                continue  # Only include common dunder methods
            
            method_sig = None
            try:
                method_sig = str(inspect.signature(method))
            except (ValueError, TypeError):
                pass
            
            method_doc = getattr(method, "__doc__", None)
            # Get first line of docstring as preview
            doc_preview = None
            if method_doc:
                first_line = method_doc.strip().split("\\n")[0]
                doc_preview = first_line[:100] + "..." if len(first_line) > 100 else first_line
            
            methods.append({{
                "name": name,
                "signature": method_sig,
                "doc_preview": doc_preview
            }})
        
        # Sort methods: __init__ first, then alphabetically
        methods.sort(key=lambda m: (0 if m["name"] == "__init__" else 1, m["name"]))
        # Limit to 30 methods to avoid huge responses
        methods = methods[:30]
    
    result = {{
        "name": getattr(obj, "__name__", str(obj)),
        "qualname": getattr(obj, "__qualname__", symbol_path),
        "kind": kind,
        "module": getattr(obj, "__module__", package_name),
        "docstring": docstring,
        "signature": signature,
        "source": source,
        "methods": methods
    }}
    print(json.dumps(result))
except Exception as e:
    error = {{"error": str(e), "type": type(e).__name__}}
    print(json.dumps(error))
    sys.exit(1)
"""


# Introspection script for package-level docstring
PACKAGE_DOCSTRING_SCRIPT = """
import json
import sys
from importlib import import_module

package_name = {package_name!r}

try:
    module = import_module(package_name)
    result = {{
        "docstring": getattr(module, "__doc__", None),
        "name": getattr(module, "__name__", package_name),
        "file": getattr(module, "__file__", None)
    }}
    print(json.dumps(result))
except Exception as e:
    error = {{"error": str(e), "type": type(e).__name__}}
    print(json.dumps(error))
    sys.exit(1)
"""


# Introspection script for searching symbols
SEARCH_SYMBOLS_SCRIPT = """
import json
import sys
import inspect
from importlib import import_module
import pkgutil

package_name = {package_name!r}
pattern = {pattern!r}

try:
    package = import_module(package_name)
    results = []
    scanned_modules = set()
    
    def scan_module(module, prefix=""):
        if module.__name__ in scanned_modules:
            return
        scanned_modules.add(module.__name__)
        
        members = inspect.getmembers(module)
        for name, obj in members:
            if name.startswith("_"):
                continue
            
            # Filter by package
            if hasattr(obj, "__module__"):
                obj_module = obj.__module__ or ""
                if not obj_module.startswith(package_name):
                    continue
            
            full_name = f"{{prefix}}{{name}}" if prefix else name
            
            # Pattern matching
            if pattern and pattern.lower() not in full_name.lower():
                continue
            
            # Determine kind
            if inspect.ismodule(obj):
                kind = "module"
            elif inspect.isclass(obj):
                kind = "class"
            elif inspect.isfunction(obj):
                kind = "function"
            elif inspect.ismethod(obj):
                kind = "method"
            else:
                continue
            
            # Get signature
            signature = None
            if callable(obj):
                try:
                    signature = str(inspect.signature(obj))
                except (ValueError, TypeError):
                    pass
            
            results.append({{
                "name": getattr(obj, "__name__", name),
                "qualname": getattr(obj, "__qualname__", full_name),
                "kind": kind,
                "module": getattr(obj, "__module__", package_name),
                "docstring": getattr(obj, "__doc__", None),
                "signature": signature
            }})
            
            # Limit results
            if len(results) >= 1000:
                return
    
    # Scan main package
    scan_module(package)
    
    # Discover and scan submodules
    if hasattr(package, "__path__") and len(results) < 1000:
        for importer, modname, ispkg in pkgutil.iter_modules(package.__path__, prefix=f"{{package_name}}."):
            if len(results) >= 1000:
                break
            try:
                submod = import_module(modname)
                submod_suffix = modname[len(package_name):].lstrip(".")
                scan_module(submod, prefix=f"{{submod_suffix}}.")
            except Exception:
                continue
    
    print(json.dumps({{"symbols": results, "count": len(results)}}))
except Exception as e:
    error = {{"error": str(e), "type": type(e).__name__}}
    print(json.dumps(error))
    sys.exit(1)
"""


def introspect_package_info(
    package_name: str, working_dir: Path, timeout: int = 15
) -> Optional[Dict[str, Any]]:
    """Get package info via subprocess introspection.

    Args:
        package_name: Name of the package to introspect
        working_dir: Starting directory for project detection
        timeout: Timeout in seconds

    Returns:
        Dictionary with package info, or None if subprocess fails
    """
    pm_result = detect_package_manager(working_dir)
    if not pm_result:
        logger.debug(f"No package manager detected at {working_dir}")
        return None

    runner, project_root = pm_result
    cache_key = f"pkg_info:{package_name}:{project_root}"

    cached = _get_from_cache(cache_key)
    if cached is not None:
        logger.debug(f"Using cached package info for {package_name}")
        return cached

    script = PACKAGE_INFO_SCRIPT.format(package_name=package_name)

    try:
        logger.info(
            f"Running subprocess introspection for package {package_name} at {project_root}"
        )
        result = subprocess.run(
            runner + ["-c", script],
            capture_output=True,
            text=True,
            cwd=project_root,
            timeout=timeout,
        )

        if result.returncode == 0:
            data = json.loads(result.stdout)
            if "error" not in data:
                logger.info(f"Successfully introspected {package_name} via subprocess")
                _add_to_cache(cache_key, data)
                return data
            else:
                logger.warning(f"Subprocess introspection error: {data.get('error')}")
        else:
            logger.warning(
                f"Subprocess introspection failed (exit {result.returncode}): {result.stderr}"
            )
    except subprocess.TimeoutExpired:
        logger.warning(f"Subprocess introspection timeout for {package_name}")
    except (json.JSONDecodeError, FileNotFoundError) as e:
        logger.warning(f"Subprocess introspection failed: {e}")

    return None


def introspect_symbol(
    package_name: str,
    symbol_path: str,
    working_dir: Path,
    timeout: int = 20,
) -> Optional[Dict[str, Any]]:
    """Get symbol info via subprocess introspection.

    Args:
        package_name: Name of the package
        symbol_path: Dot-separated path to symbol
        working_dir: Starting directory for project detection
        timeout: Timeout in seconds

    Returns:
        Dictionary with symbol info, or None if subprocess fails
    """
    pm_result = detect_package_manager(working_dir)
    if not pm_result:
        return None

    runner, project_root = pm_result
    cache_key = f"symbol:{package_name}:{symbol_path}:{project_root}"

    cached = _get_from_cache(cache_key)
    if cached is not None:
        logger.debug(f"Using cached symbol info for {package_name}.{symbol_path}")
        return cached

    script = SYMBOL_INFO_SCRIPT.format(
        package_name=package_name, symbol_path=symbol_path
    )

    try:
        logger.info(
            f"Running subprocess introspection for symbol {package_name}.{symbol_path}"
        )
        result = subprocess.run(
            runner + ["-c", script],
            capture_output=True,
            text=True,
            cwd=project_root,
            timeout=timeout,
        )

        if result.returncode == 0:
            data = json.loads(result.stdout)
            if "error" not in data:
                logger.info(f"Successfully introspected symbol via subprocess")
                _add_to_cache(cache_key, data)
                return data
            else:
                logger.debug(
                    f"Subprocess symbol introspection error: {data.get('error')}"
                )
        else:
            logger.debug(f"Subprocess symbol introspection failed: {result.stderr}")
    except subprocess.TimeoutExpired:
        logger.warning(f"Subprocess symbol introspection timeout")
    except (json.JSONDecodeError, FileNotFoundError) as e:
        logger.debug(f"Subprocess symbol introspection failed: {e}")

    return None


def search_symbols_subprocess(
    package_name: str,
    pattern: Optional[str],
    working_dir: Path,
    timeout: int = 45,
) -> Optional[List[Dict[str, Any]]]:
    """Search symbols via subprocess introspection.

    Args:
        package_name: Name of the package
        pattern: Optional search pattern
        working_dir: Starting directory for project detection
        timeout: Timeout in seconds

    Returns:
        List of symbol dictionaries, or None if subprocess fails
    """
    pm_result = detect_package_manager(working_dir)
    if not pm_result:
        return None

    runner, project_root = pm_result
    cache_key = f"search:{package_name}:{pattern}:{project_root}"

    cached = _get_from_cache(cache_key)
    if cached is not None:
        logger.debug(f"Using cached search results for {package_name}")
        return cached

    script = SEARCH_SYMBOLS_SCRIPT.format(
        package_name=package_name, pattern=pattern or ""
    )

    try:
        logger.info(f"Running subprocess search for {package_name} at {project_root}")
        result = subprocess.run(
            runner + ["-c", script],
            capture_output=True,
            text=True,
            cwd=project_root,
            timeout=timeout,
        )

        if result.returncode == 0:
            data = json.loads(result.stdout)
            if "error" not in data:
                symbols = data.get("symbols", [])
                logger.info(
                    f"Successfully searched symbols via subprocess: {len(symbols)} found"
                )
                _add_to_cache(cache_key, symbols)
                return symbols
            else:
                logger.warning(f"Subprocess search error: {data.get('error')}")
        else:
            logger.warning(f"Subprocess search failed: {result.stderr}")
    except subprocess.TimeoutExpired:
        logger.warning(f"Subprocess search timeout for {package_name}")
    except (json.JSONDecodeError, FileNotFoundError) as e:
        logger.warning(f"Subprocess search failed: {e}")

    return None


def introspect_package_docstring(
    package_name: str, working_dir: Path, timeout: int = 15
) -> Optional[Dict[str, Any]]:
    """Get package-level docstring via subprocess introspection.

    Args:
        package_name: Name of the package
        working_dir: Starting directory for project detection
        timeout: Timeout in seconds

    Returns:
        Dictionary with docstring and module info, or None if subprocess fails
    """
    pm_result = detect_package_manager(working_dir)
    if not pm_result:
        return None

    runner, project_root = pm_result
    cache_key = f"docstring:{package_name}:{project_root}"

    cached = _get_from_cache(cache_key)
    if cached is not None:
        logger.debug(f"Using cached docstring for {package_name}")
        return cached

    script = PACKAGE_DOCSTRING_SCRIPT.format(package_name=package_name)

    try:
        logger.info(f"Running subprocess docstring introspection for {package_name}")
        result = subprocess.run(
            runner + ["-c", script],
            capture_output=True,
            text=True,
            cwd=project_root,
            timeout=timeout,
        )

        if result.returncode == 0:
            data = json.loads(result.stdout)
            if "error" not in data:
                logger.info(
                    f"Successfully got docstring for {package_name} via subprocess"
                )
                _add_to_cache(cache_key, data)
                return data
            else:
                logger.debug(
                    f"Subprocess docstring introspection error: {data.get('error')}"
                )
        else:
            logger.debug(f"Subprocess docstring introspection failed: {result.stderr}")
    except subprocess.TimeoutExpired:
        logger.warning(f"Subprocess docstring introspection timeout")
    except (json.JSONDecodeError, FileNotFoundError) as e:
        logger.debug(f"Subprocess docstring introspection failed: {e}")

    return None


_client_working_directory: Optional[Path] = None


def set_working_directory(path: Optional[str]) -> None:
    """Set the working directory from MCP client roots.

    This is called when the MCP client provides workspace roots,
    allowing automatic detection without requiring PWD env var.

    Args:
        path: Path to the working directory (from client roots).
              Pass None to clear the client working directory.
    """
    global _client_working_directory

    if path is None:
        _client_working_directory = None
        logger.info("Working directory cleared (will re-fetch from client)")
        return

    path_obj = Path(path)
    if path_obj.exists() and path_obj.is_dir():
        _client_working_directory = path_obj
        logger.info(f"Working directory set from client roots: {path_obj}")
    else:
        logger.warning(f"Client root path does not exist: {path}")


def get_working_directory() -> Path:
    """Get the working directory for package manager detection.

    Priority order:
    1. Client roots (set via MCP roots capability) - automatic, no config needed
    2. PWD environment variable (preserves original directory)
    3. Current working directory (fallback)

    Returns:
        Path to working directory
    """
    import os

    # 1. Check if client roots were set (from MCP roots capability)
    if _client_working_directory is not None:
        return _client_working_directory

    # 2. Check PWD environment variable
    pwd = os.environ.get("PWD")
    if pwd:
        pwd_path = Path(pwd)
        if pwd_path.exists() and pwd_path.is_dir():
            return pwd_path

    # 3. Fall back to cwd
    return Path.cwd()


def refresh_working_directory() -> Path:
    """Get a fresh working directory, ignoring any cached results.

    This is useful for MCP servers where the working directory might
    change between requests.

    Priority order:
    1. Client roots (set via MCP roots capability)
    2. PWD environment variable
    3. Current working directory

    Returns:
        Path to working directory
    """
    import os

    # 1. Check if client roots were set (from MCP roots capability)
    if _client_working_directory is not None:
        return _client_working_directory

    # 2. Check PWD environment variable
    pwd = os.environ.get("PWD")
    if pwd:
        pwd_path = Path(pwd)
        if pwd_path.exists() and pwd_path.is_dir():
            return pwd_path

    # 3. Fall back to cwd
    return Path.cwd()


def clear_cache() -> None:
    """Clear all caches."""
    global _package_manager_cache, _introspection_cache
    _package_manager_cache.clear()
    _introspection_cache.clear()
    logger.info("Cleared subprocess introspection caches")


def is_subprocess_available(working_dir: Path) -> bool:
    """Check if subprocess introspection is available for a directory.

    Args:
        working_dir: Directory to check

    Returns:
        True if a package manager was detected and is available
    """
    return detect_package_manager(working_dir) is not None
