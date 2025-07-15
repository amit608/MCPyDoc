"""Package analysis functionality for MCPyDoc."""

import inspect
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
from .models import PackageInfo, SymbolInfo
from .security import (
    audit_log,
    memory_limit,
    timeout,
    validate_package_name,
    validate_symbol_path,
    validate_version,
)


class PackageAnalyzer:
    """Analyzes Python packages to extract documentation and structure."""

    def __init__(self, python_paths: Optional[List[str]] = None) -> None:
        """Initialize the analyzer with optional Python environment paths.

        Args:
            python_paths: List of paths to Python environments to search for packages.
                        If None, uses the current environment.
        """
        self._package_cache: Dict[str, ModuleType] = {}
        self._python_paths = python_paths or [sys.prefix]
        self._version_cache: Dict[str, Dict[str, PackageInfo]] = {}

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
                if str(module_file).startswith(str(stdlib_path)) and not in_site_packages:
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
            for path in self._python_paths:
                sys.path.insert(0, path)
                try:
                    dist = metadata.distribution(package_name)
                    found = True
                    pkg_info = PackageInfo(
                        name=dist.metadata["Name"],
                        version=dist.metadata["Version"],
                        summary=dist.metadata.get("Summary"),
                        author=dist.metadata.get("Author"),
                        license=dist.metadata.get("License"),
                        location=Path(dist.locate_file("")),
                    )
                    versions[pkg_info.version] = pkg_info
                except metadata.PackageNotFoundError:
                    continue
                finally:
                    sys.path.pop(0)

        if not found:
            raise PackageNotFoundError(package_name, self._python_paths)

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

    @timeout(20)
    def get_symbol_info(self, package_name: str, symbol_path: str) -> SymbolInfo:
        """Get detailed information about a symbol in a package.

        Args:
            package_name: Name of the package containing the symbol
            symbol_path: Dot-separated path to the symbol

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
        # Handle both package-level and module-level symbols
        if "." in symbol_path:
            module_path, *symbol_parts = symbol_path.split(".")
            module = self._import_module(f"{package_name}.{module_path}")
        else:
            module = self._import_module(package_name)
            symbol_parts = [symbol_path]

        obj = module
        full_path = package_name

        # Navigate to the requested symbol
        for part in symbol_parts:
            try:
                obj = getattr(obj, part)
                full_path += f".{part}"
            except AttributeError:
                raise SymbolNotFoundError(symbol_path, full_path)

        # Determine the symbol kind
        kind = self._get_symbol_kind(obj)

        # Get the symbol's signature if applicable
        signature = self._get_signature(obj)

        # Get source code if available
        source = self._get_source_code(obj)

        return SymbolInfo(
            name=getattr(obj, "__name__", str(obj)),
            qualname=getattr(obj, "__qualname__", symbol_path),
            kind=kind,
            module=getattr(obj, "__module__", package_name),
            docstring=getattr(obj, "__doc__", None),
            signature=signature,
            source=source,
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

    @timeout(45)
    @memory_limit(256)
    def search_symbols(
        self, package_name: str, pattern: Optional[str] = None
    ) -> List[SymbolInfo]:
        """Search for symbols in a package matching an optional pattern.

        Args:
            package_name: Name of the package to search
            pattern: Optional pattern to filter symbols

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
        audit_log("search_symbols", package_name=package_name, pattern=pattern)
        results = []
        package = self._import_module(package_name)

        def _scan_module(module: ModuleType, prefix: str = "") -> None:
            # Get all module contents, both direct and imported
            for name, obj in inspect.getmembers(module):
                # Skip private attributes
                if name.startswith("_"):
                    continue

                # For the root package, include all objects
                # For submodules, only include objects defined in the package
                if prefix and hasattr(obj, "__module__"):
                    if not (obj.__module__ or "").startswith(package_name):
                        continue

                full_name = f"{prefix}{name}" if prefix else name

                # If a pattern is provided, check if it matches
                if pattern and pattern.lower() not in full_name.lower():
                    continue

                try:
                    # For root level symbols, use the name directly
                    if not prefix:
                        info = self.get_symbol_info(package_name, name)
                    else:
                        info = self.get_symbol_info(package_name, full_name)
                    results.append(info)
                except (ImportError, SymbolNotFoundError, AttributeError):
                    continue

                # Recursively scan submodules
                if (
                    inspect.ismodule(obj)
                    and obj.__name__.startswith(package_name)
                    and len(results) < 1000  # Prevent infinite recursion
                ):
                    _scan_module(obj, prefix=f"{full_name}." if prefix else f"{name}.")

        _scan_module(package)
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
