"""Package analysis functionality for MCPyDoc."""

import inspect
import logging
import os
import sys
from functools import lru_cache
from importlib import import_module, metadata
from pathlib import Path
from types import ModuleType
from typing import Dict, List, Optional, get_type_hints

from .exceptions import (
    ImportError,
    PackageNotFoundError,
    SymbolNotFoundError,
    ValidationError,
    VersionConflictError,
)
from .models import MethodSummary, PackageInfo, SymbolInfo
from .security import (
    audit_log,
    memory_limit,
    timeout,
    validate_package_name,
    validate_symbol_path,
    validate_version,
)
from .subprocess_introspection import (
    get_working_directory,
    introspect_package_docstring,
    introspect_package_info,
    introspect_symbol,
    search_symbols_subprocess,
)

logger = logging.getLogger(__name__)


class PackageAnalyzer:
    """Analyzes Python packages to extract documentation and structure."""

    def __init__(
        self,
        python_paths: Optional[List[str]] = None,
        enable_subprocess: bool = True,
        working_directory: Optional[Path] = None,
    ) -> None:
        """Initialize the analyzer with optional Python environment paths.

        Args:
            python_paths: List of paths to Python environments to search for packages.
                        If None, uses intelligent environment detection to find
                        the working directory's Python environment.
            enable_subprocess: If True, use subprocess introspection via package managers
                             as the primary method (solves Python version mismatches).
            working_directory: Working directory for package manager detection.
                             If None, uses get_working_directory().
        """
        self._package_cache: Dict[str, ModuleType] = {}
        self._explicit_python_paths = (
            python_paths  # Store if user provided explicit paths
        )
        if python_paths is None:
            from .env_detection import get_active_python_environments

            self._python_paths = get_active_python_environments()
        else:
            self._python_paths = python_paths
        self._version_cache: Dict[str, Dict[str, PackageInfo]] = {}
        self._subprocess_enabled = enable_subprocess
        self._working_directory = working_directory or get_working_directory()

    def refresh_environments(self) -> None:
        """Refresh Python environments and working directory.

        This should be called when the MCP client roots change,
        to pick up the new workspace's virtual environment.
        """
        # Only refresh if user didn't provide explicit paths
        if self._explicit_python_paths is None:
            from .env_detection import get_active_python_environments

            # Force re-detection (bypass cache)
            self._python_paths = get_active_python_environments(use_cache=False)
            logger.info(f"Refreshed Python environments: {self._python_paths}")

        # Always refresh working directory
        self._working_directory = get_working_directory()
        logger.info(f"Refreshed working directory: {self._working_directory}")

    @timeout(30)
    def get_package_info(
        self, package_name: str, version: Optional[str] = None
    ) -> PackageInfo:
        """Get metadata for a Python package.

        Args:
            package_name: Name of the package to analyze
            version: Specific version to use. If None, uses the latest available version

        Returns:
            PackageInfo object containing package metadata

        Raises:
            PackageNotFoundError: If package not found
            VersionConflictError: If version conflicts detected
            ValidationError: If input validation fails
            PackageSecurityError: If security checks fail
        """
        # Validate inputs
        validate_package_name(package_name)
        validate_version(version)

        # Audit log the operation
        audit_log("get_package_info", package_name=package_name, version=version)

        # Check version cache first
        if package_name in self._version_cache:
            versions = self._version_cache[package_name]
            if version:
                if version in versions:
                    return versions[version]
                raise VersionConflictError(package_name, version, "not found")
            # Return latest version if no specific version requested
            latest = max(versions.keys())
            return versions[latest]

        # Try subprocess introspection first (solves Python version mismatches)
        if self._subprocess_enabled:
            pkg_data = introspect_package_info(package_name, self._working_directory)
            if pkg_data and "error" not in pkg_data:
                logger.info(
                    f"Using subprocess introspection for {package_name} "
                    f"(avoids Python version mismatch)"
                )
                pkg_info = PackageInfo(
                    name=pkg_data["name"],
                    version=pkg_data["version"],
                    summary=pkg_data.get("summary"),
                    author=pkg_data.get("author"),
                    license=pkg_data.get("license"),
                    location=(
                        Path(pkg_data["location"]) if pkg_data.get("location") else None
                    ),
                )
                # Cache the result
                versions = {pkg_info.version: pkg_info}
                self._version_cache[package_name] = versions
                return pkg_info
            else:
                logger.debug(
                    f"Subprocess introspection not available for {package_name}, "
                    f"falling back to direct import"
                )

        versions = {}
        found = False

        # First, check if it's a built-in or standard library module
        try:
            module = import_module(package_name)

            # Check if it's a built-in module
            if package_name in sys.builtin_module_names:
                pkg_info = PackageInfo(
                    name=package_name,
                    version=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
                    summary=f"Built-in Python module",
                    author="Python Software Foundation",
                    license="Python Software Foundation License",
                    location=None,
                )
                versions[pkg_info.version] = pkg_info
                found = True
            # Check if it's a standard library module
            elif hasattr(module, "__file__") and module.__file__:
                module_file = Path(module.__file__)
                # Use base_prefix for standard library path (handles virtual envs)
                base_prefix = getattr(sys, "base_prefix", sys.prefix)
                if sys.platform == "win32":
                    stdlib_path = Path(base_prefix) / "Lib"
                else:
                    stdlib_path = (
                        Path(base_prefix)
                        / "lib"
                        / "python{}.{}".format(
                            sys.version_info.major, sys.version_info.minor
                        )
                    )

                in_site_packages = "site-packages" in module_file.parts
                if (
                    str(module_file).startswith(str(stdlib_path))
                    and not in_site_packages
                ):
                    pkg_info = PackageInfo(
                        name=package_name,
                        version=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
                        summary=f"Python standard library module",
                        author="Python Software Foundation",
                        license="Python Software Foundation License",
                        location=module_file.parent,
                    )
                    versions[pkg_info.version] = pkg_info
                    found = True
        except (ImportError, ModuleNotFoundError):
            pass

        # If not found as built-in/stdlib, search for installed packages
        if not found:
            from .env_detection import get_site_packages_paths

            # Get site-packages paths from python environment paths
            site_packages = get_site_packages_paths(self._python_paths)

            # Search in each environment
            for env_path in self._python_paths:
                # Temporarily add both the environment path and its site-packages to sys.path
                paths_to_add = [env_path]

                # Add corresponding site-packages if found
                # Use proper path containment checking to avoid false positives
                env_path_resolved = str(Path(env_path).resolve())
                for sp in site_packages:
                    sp_resolved = str(Path(sp).resolve())
                    # Check if site-packages path is within the environment path
                    if (
                        sp_resolved.startswith(env_path_resolved + os.sep)
                        or sp_resolved == env_path_resolved
                    ):
                        paths_to_add.append(sp)

                # Insert paths at the beginning to prioritize this environment
                inserted_count = 0
                for p in paths_to_add:
                    if p not in sys.path:
                        sys.path.insert(inserted_count, p)
                        inserted_count += 1

                try:
                    dist = metadata.distribution(package_name)
                    found = True
                    pkg_location = Path(dist.locate_file(""))

                    logger.info(
                        f"Found package '{package_name}' version {dist.metadata['Version']} "
                        f"in environment: {env_path}"
                    )

                    pkg_info = PackageInfo(
                        name=dist.metadata["Name"],
                        version=dist.metadata["Version"],
                        summary=dist.metadata.get("Summary"),
                        author=dist.metadata.get("Author"),
                        license=dist.metadata.get("License"),
                        location=pkg_location,
                    )
                    versions[pkg_info.version] = pkg_info

                    # Package found, break to keep these paths in sys.path for imports
                    break
                except metadata.PackageNotFoundError:
                    # Remove the temporarily added paths if package not found here
                    for _ in range(inserted_count):
                        if sys.path:
                            sys.path.pop(0)
                    continue

        if not found:
            from .env_detection import get_searched_directories

            searched_dirs = get_searched_directories()
            raise PackageNotFoundError(package_name, self._python_paths, searched_dirs)

        self._version_cache[package_name] = versions

        if version:
            if version in versions:
                return versions[version]
            available = list(versions.keys())
            raise VersionConflictError(package_name, version, f"Available: {available}")

        # Return latest version if no specific version requested
        latest = max(versions.keys())
        return versions[latest]

    def _import_module(
        self, module_path: str, version: Optional[str] = None
    ) -> ModuleType:
        """Safely import a module and cache it.

        Args:
            module_path: Full path to the module
            version: Specific version to import. If None, uses latest available

        Returns:
            Imported module object

        Raises:
            ImportError: If module cannot be imported
            VersionConflictError: If version conflicts detected
        """
        cache_key = f"{module_path}@{version if version else 'latest'}"

        if cache_key in self._package_cache:
            return self._package_cache[cache_key]

        # Try to import directly first (for built-in modules)
        try:
            module = import_module(module_path)

            # Check if this is a built-in module or standard library
            if hasattr(module, "__file__") and module.__file__:
                # It's a file-based module, check if it's in standard library
                module_file = Path(module.__file__)
                # Use base_prefix for standard library path (handles virtual envs)
                base_prefix = getattr(sys, "base_prefix", sys.prefix)
                if sys.platform == "win32":
                    stdlib_path = Path(base_prefix) / "Lib"
                else:
                    stdlib_path = (
                        Path(base_prefix)
                        / "lib"
                        / "python{}.{}".format(
                            sys.version_info.major, sys.version_info.minor
                        )
                    )

                # If it's in standard library or built-in, no need for package info
                if (
                    str(module_file).startswith(str(stdlib_path))
                    or module_path in sys.builtin_module_names
                ):
                    self._package_cache[cache_key] = module
                    return module
            elif module_path in sys.builtin_module_names:
                # It's a built-in module
                self._package_cache[cache_key] = module
                return module

            # If we get here, it might be a third-party package
            # Get package name from module path
            package_name = module_path.split(".")[0]

            # Get package info to ensure correct version
            pkg_info = self.get_package_info(package_name, version)

            # Verify imported version matches requested
            if hasattr(module, "__version__") and version:
                if module.__version__ != version:
                    raise VersionConflictError(
                        package_name, version, module.__version__
                    )

            self._package_cache[cache_key] = module
            return module

        except ImportError as e:
            raise ImportError(module_path, e)
        except Exception as e:
            raise ImportError(module_path, e)

    def get_package_docstring(
        self, package_name: str, version: Optional[str] = None
    ) -> Optional[str]:
        """Get the package-level docstring.

        Uses subprocess introspection if available, falling back to direct import.

        Args:
            package_name: Name of the package
            version: Specific version to use (optional)

        Returns:
            Package docstring, or None if not available
        """
        # Try subprocess introspection first
        if self._subprocess_enabled:
            docstring_data = introspect_package_docstring(
                package_name, self._working_directory
            )
            if docstring_data and "error" not in docstring_data:
                logger.info(
                    f"Using subprocess introspection for {package_name} docstring"
                )
                return docstring_data.get("docstring")
            else:
                logger.debug(
                    f"Subprocess docstring introspection not available, "
                    f"falling back to direct import"
                )

        # Fall back to direct import
        try:
            module = self._import_module(package_name, version)
            return module.__doc__
        except Exception as e:
            logger.warning(f"Failed to get docstring for {package_name}: {e}")
            return None

    @timeout(20)
    def get_symbol_info(self, package_name: str, symbol_path: str) -> SymbolInfo:
        """Get detailed information about a symbol in a package.

        Args:
            package_name: Name of the package containing the symbol
            symbol_path: Dot-separated path to the symbol (e.g., 'ClassName', 'ClassName.method', 'module.ClassName')

        Returns:
            SymbolInfo object containing symbol details

        Raises:
            ImportError: If module cannot be imported
            SymbolNotFoundError: If symbol cannot be found
            ValidationError: If input validation fails
        """
        # Validate inputs
        validate_package_name(package_name)
        validate_symbol_path(symbol_path)

        # Audit log the operation
        audit_log("get_symbol_info", package_name=package_name, symbol_path=symbol_path)

        # Try subprocess introspection first
        if self._subprocess_enabled:
            symbol_data = introspect_symbol(
                package_name, symbol_path, self._working_directory
            )
            if symbol_data and "error" not in symbol_data:
                logger.info(
                    f"Using subprocess introspection for {package_name}.{symbol_path}"
                )
                # Convert methods list to MethodSummary objects
                methods = None
                if symbol_data.get("methods"):
                    methods = [
                        MethodSummary(
                            name=m["name"],
                            signature=m.get("signature"),
                            doc_preview=m.get("doc_preview"),
                        )
                        for m in symbol_data["methods"]
                    ]
                return SymbolInfo(
                    name=symbol_data["name"],
                    qualname=symbol_data["qualname"],
                    kind=symbol_data["kind"],
                    module=symbol_data["module"],
                    docstring=symbol_data.get("docstring"),
                    signature=symbol_data.get("signature"),
                    source=symbol_data.get("source"),
                    methods=methods,
                )
            else:
                logger.debug(
                    f"Subprocess introspection not available for symbol, "
                    f"falling back to direct import"
                )

        # Enhanced symbol resolution with multiple fallback strategies
        strategies = []

        if "." in symbol_path:
            parts = symbol_path.split(".")

            # Strategy 1: Treat first part as module, rest as nested symbols
            strategies.append(
                {"module_name": f"{package_name}.{parts[0]}", "symbol_parts": parts[1:]}
            )

            # Strategy 2: Treat entire path as nested symbols in main package
            strategies.append({"module_name": package_name, "symbol_parts": parts})

            # Strategy 3: Try progressive module resolution (for deep nesting)
            for i in range(1, len(parts)):
                module_parts = parts[:i]
                symbol_parts = parts[i:]
                strategies.append(
                    {
                        "module_name": f"{package_name}.{'.'.join(module_parts)}",
                        "symbol_parts": symbol_parts,
                    }
                )
        else:
            # Single symbol - try main package first
            strategies.append(
                {"module_name": package_name, "symbol_parts": [symbol_path]}
            )

        # Try each strategy until one succeeds
        last_error = None
        for strategy in strategies:
            try:
                module = self._import_module(strategy["module_name"])
                obj = module
                full_path = strategy["module_name"]

                # Navigate to the requested symbol
                for part in strategy["symbol_parts"]:
                    try:
                        obj = getattr(obj, part)
                        full_path += f".{part}"
                    except AttributeError:
                        raise SymbolNotFoundError(
                            symbol_path, f"'{part}' not found in {full_path}"
                        )

                # Determine the symbol kind
                kind = self._get_symbol_kind(obj)

                # Get the symbol's signature if applicable
                signature = self._get_signature(obj)

                # Get source code if available
                source = self._get_source_code(obj)

                # For classes, extract method summaries
                methods = None
                if kind == "class":
                    methods = self._get_class_methods(obj)

                return SymbolInfo(
                    name=getattr(obj, "__name__", str(obj)),
                    qualname=getattr(obj, "__qualname__", symbol_path),
                    kind=kind,
                    module=getattr(obj, "__module__", package_name),
                    docstring=getattr(obj, "__doc__", None),
                    signature=signature,
                    source=source,
                    methods=methods,
                )

            except (ImportError, SymbolNotFoundError) as e:
                last_error = e
                continue

        # If all strategies failed, provide helpful error message
        if last_error:
            error_msg = (
                f"Symbol '{symbol_path}' not found in package '{package_name}'. "
            )
            error_msg += "Try using analyze_structure to see available symbols, "
            error_msg += "or search_symbols to find the correct symbol name."
            raise SymbolNotFoundError(symbol_path, error_msg)
        else:
            raise SymbolNotFoundError(
                symbol_path, f"No valid resolution strategy found for '{symbol_path}'"
            )

    def _get_symbol_kind(self, obj: any) -> str:
        """Determine the kind of a Python object."""
        if inspect.ismodule(obj):
            return "module"
        elif inspect.isclass(obj):
            return "class"
        elif inspect.isfunction(obj):
            return "function"
        elif inspect.ismethod(obj):
            return "method"
        elif inspect.isbuiltin(obj):
            return "builtin"
        elif inspect.isdatadescriptor(obj):
            return "property"
        else:
            return "other"

    def _get_signature(self, obj: any) -> Optional[str]:
        """Get the signature of a callable object."""
        if not callable(obj):
            return None
        try:
            return str(inspect.signature(obj))
        except (ValueError, TypeError):
            return None

    def _get_source_code(self, obj: any) -> Optional[str]:
        """Get source code for an object if available."""
        try:
            return inspect.getsource(obj)
        except (TypeError, OSError, AttributeError):
            return None

    def _get_class_methods(self, cls: type) -> Optional[List[MethodSummary]]:
        """Get a summary of methods for a class.

        Args:
            cls: The class to extract methods from

        Returns:
            List of MethodSummary objects, or None if extraction fails
        """
        try:
            methods = []
            for name, method in inspect.getmembers(
                cls, predicate=lambda x: inspect.isfunction(x) or inspect.ismethod(x)
            ):
                # Skip private methods but keep important dunders
                if name.startswith("_") and not name.startswith("__"):
                    continue
                if name.startswith("__") and name not in (
                    "__init__",
                    "__call__",
                    "__enter__",
                    "__exit__",
                    "__aenter__",
                    "__aexit__",
                ):
                    continue

                method_sig = self._get_signature(method)
                method_doc = getattr(method, "__doc__", None)

                # Get first line of docstring as preview
                doc_preview = None
                if method_doc:
                    first_line = method_doc.strip().split("\n")[0]
                    doc_preview = (
                        first_line[:100] + "..."
                        if len(first_line) > 100
                        else first_line
                    )

                methods.append(
                    MethodSummary(
                        name=name,
                        signature=method_sig,
                        doc_preview=doc_preview,
                    )
                )

            # Sort: __init__ first, then alphabetically
            methods.sort(key=lambda m: (0 if m.name == "__init__" else 1, m.name))
            # Limit to 30 methods
            return methods[:30] if methods else None
        except Exception:
            return None

    @timeout(45)
    @memory_limit(256)
    def search_symbols(
        self,
        package_name: str,
        pattern: Optional[str] = None,
        version: Optional[str] = None,
    ) -> List[SymbolInfo]:
        """Search for symbols in a package matching an optional pattern.

        Args:
            package_name: Name of the package to search
            pattern: Optional pattern to filter symbols
            version: Optional specific version to search

        Returns:
            List of SymbolInfo objects matching the criteria

        Raises:
            ImportError: If package cannot be imported
            ValidationError: If input validation fails
            ResourceLimitError: If resource limits are exceeded
        """
        # Validate inputs
        validate_package_name(package_name)
        if pattern is not None:
            if len(pattern) > 100:  # Limit pattern length
                raise ValidationError(f"Search pattern too long: {len(pattern)} > 100")

        # Audit log the operation
        audit_log(
            "search_symbols",
            package_name=package_name,
            pattern=pattern,
            version=version,
        )

        # Try subprocess introspection first
        if self._subprocess_enabled:
            symbols_data = search_symbols_subprocess(
                package_name, pattern, self._working_directory
            )
            if symbols_data is not None:
                logger.info(
                    f"Using subprocess introspection for searching {package_name} "
                    f"(found {len(symbols_data)} symbols)"
                )
                results = []
                for symbol_data in symbols_data:
                    results.append(
                        SymbolInfo(
                            name=symbol_data["name"],
                            qualname=symbol_data["qualname"],
                            kind=symbol_data["kind"],
                            module=symbol_data["module"],
                            docstring=symbol_data.get("docstring"),
                            signature=symbol_data.get("signature"),
                            source=None,  # Source not included in search results
                        )
                    )
                return results
            else:
                logger.debug(
                    f"Subprocess introspection not available for search, "
                    f"falling back to direct import"
                )

        results = []
        logger.info(f"Starting symbol search for package: {package_name}")
        package = self._import_module(package_name, version)
        logger.info(f"Successfully imported {package_name}, module: {package.__name__}")

        def _scan_module(module: ModuleType, prefix: str = "") -> None:
            # Get all module contents, both direct and imported
            members = inspect.getmembers(module)
            logger.debug(
                f"Scanning module {module.__name__} (prefix: '{prefix}'), found {len(members)} members"
            )

            for name, obj in members:
                # Skip private attributes
                if name.startswith("_"):
                    continue

                # Filter out symbols not from this package
                # Only include symbols that belong to the target package or its submodules
                if hasattr(obj, "__module__"):
                    obj_module = obj.__module__ or ""
                    # Skip if symbol is from a different package entirely
                    if not obj_module.startswith(package_name):
                        continue

                full_name = f"{prefix}{name}" if prefix else name

                # If a pattern is provided, check if it matches
                if pattern and pattern.lower() not in full_name.lower():
                    continue

                try:
                    # Try to get symbol info
                    # For root level, first try the simple name
                    if not prefix:
                        try:
                            info = self.get_symbol_info(package_name, name)
                        except (SymbolNotFoundError, AttributeError):
                            # If that fails and object has __module__, try the full path
                            if (
                                hasattr(obj, "__module__")
                                and obj.__module__ != package_name
                            ):
                                # Construct the path from the module
                                module_suffix = obj.__module__[
                                    len(package_name) :
                                ].lstrip(".")
                                if module_suffix:
                                    full_path = f"{module_suffix}.{name}"
                                    info = self.get_symbol_info(package_name, full_path)
                                else:
                                    raise
                            else:
                                raise
                    else:
                        info = self.get_symbol_info(package_name, full_name)
                    results.append(info)
                except (ImportError, SymbolNotFoundError, AttributeError) as e:
                    # Log the error for debugging but continue scanning
                    logger.debug(f"Could not get symbol info for {full_name}: {e}")
                    continue

                # Search for methods within classes
                if inspect.isclass(obj):
                    for method_name, method_obj in inspect.getmembers(
                        obj, inspect.ismethod
                    ):
                        if method_name.startswith("_"):
                            continue

                        method_full_name = f"{full_name}.{method_name}"

                        # Check pattern match for methods
                        if pattern and pattern.lower() not in method_name.lower():
                            continue

                        try:
                            method_info = SymbolInfo(
                                name=method_name,
                                qualname=f"{obj.__name__}.{method_name}",
                                kind="method",
                                module=getattr(obj, "__module__", package_name),
                                docstring=getattr(method_obj, "__doc__", None),
                                signature=self._get_signature(method_obj),
                                source=self._get_source_code(method_obj),
                            )
                            results.append(method_info)
                        except Exception:
                            continue

                    # Also search for functions within classes (static methods, class methods)
                    for func_name, func_obj in inspect.getmembers(
                        obj, inspect.isfunction
                    ):
                        if func_name.startswith("_"):
                            continue

                        # Check pattern match for functions
                        if pattern and pattern.lower() not in func_name.lower():
                            continue

                        try:
                            func_info = SymbolInfo(
                                name=func_name,
                                qualname=f"{obj.__name__}.{func_name}",
                                kind="method",
                                module=getattr(obj, "__module__", package_name),
                                docstring=getattr(func_obj, "__doc__", None),
                                signature=self._get_signature(func_obj),
                                source=self._get_source_code(func_obj),
                            )
                            results.append(func_info)
                        except Exception:
                            continue

                # Recursively scan submodules
                if (
                    inspect.ismodule(obj)
                    and obj.__name__.startswith(package_name)
                    and len(results) < 1000  # Prevent infinite recursion
                ):
                    _scan_module(obj, prefix=f"{full_name}." if prefix else f"{name}.")

        _scan_module(package)

        # Explicitly discover and scan submodules that aren't imported in __init__.py
        # This is crucial for packages like fido2 where classes are in submodules
        if hasattr(package, "__path__") and len(results) < 1000:
            logger.info(f"Discovering submodules for {package_name}")
            try:
                import pkgutil

                scanned_modules = {package.__name__}  # Track what we've scanned
                submodule_count = 0

                for importer, modname, ispkg in pkgutil.iter_modules(
                    package.__path__, prefix=f"{package_name}."
                ):
                    submodule_count += 1
                    logger.info(f"Found submodule: {modname}")

                    if modname not in scanned_modules and len(results) < 1000:
                        try:
                            # Import the submodule
                            logger.info(f"Importing submodule: {modname}")
                            submod = self._import_module(modname, version)
                            scanned_modules.add(modname)

                            # Extract just the submodule name for prefix
                            submod_suffix = modname[len(package_name) :].lstrip(".")

                            # Scan it
                            logger.info(
                                f"Scanning submodule: {modname} with prefix: {submod_suffix}"
                            )
                            before_count = len(results)
                            _scan_module(submod, prefix=f"{submod_suffix}.")
                            after_count = len(results)
                            logger.info(
                                f"Submodule {modname} yielded {after_count - before_count} symbols"
                            )
                        except Exception as e:
                            logger.error(
                                f"Failed to scan submodule {modname}: {type(e).__name__}: {e}",
                                exc_info=True,
                            )
                            continue

                logger.info(
                    f"Discovered {submodule_count} submodules for {package_name}, total results: {len(results)}"
                )
            except Exception as e:
                logger.error(
                    f"Failed to discover submodules for {package_name}: {type(e).__name__}: {e}",
                    exc_info=True,
                )
        else:
            if not hasattr(package, "__path__"):
                logger.warning(
                    f"Package {package_name} does not have __path__, cannot discover submodules"
                )

        logger.info(f"Total symbols found for {package_name}: {len(results)}")
        return results

    def get_type_hints_safe(self, obj: any) -> Dict[str, str]:
        """Safely extract type hints from an object.

        Args:
            obj: Object to extract type hints from

        Returns:
            Dictionary of type hints as strings
        """
        try:
            hints = get_type_hints(obj)
            return {name: str(hint) for name, hint in hints.items()}
        except (NameError, AttributeError, TypeError):
            return {}
