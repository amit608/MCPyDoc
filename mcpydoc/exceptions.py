"""Custom exceptions for MCPyDoc."""

from typing import Optional


class MCPyDocError(Exception):
    """Base exception for all MCPyDoc errors."""

    def __init__(self, message: str, details: Optional[str] = None) -> None:
        self.message = message
        self.details = details
        super().__init__(message)

    def __str__(self) -> str:
        if self.details:
            return f"{self.message}: {self.details}"
        return self.message


class PackageNotFoundError(MCPyDocError):
    """Raised when a package cannot be found."""

    def __init__(
        self, package_name: str, searched_paths: Optional[list] = None
    ) -> None:
        message = f"Package '{package_name}' not found"
        details = None

        if searched_paths:
            # Check if running in pipx/uvx isolated environment
            from .env_detection import is_pipx_environment

            in_pipx = any(is_pipx_environment(path) for path in searched_paths)

            details = f"Searched paths: {', '.join(searched_paths)}"

            # Add helpful suggestions
            if in_pipx:
                details += (
                    "\n\nℹ️  MCPyDoc is running in an isolated pipx/uvx environment. "
                    "To access packages from your project:\n"
                    "  1. Activate your project's virtual environment before running the AI assistant\n"
                    "  2. Or set MCPYDOC_PYTHON_PATH to your project's Python environment path\n"
                    "  3. Or ensure your project has a .venv, venv, or env folder in the current directory"
                )
            else:
                details += (
                    "\n\nℹ️  Troubleshooting:\n"
                    "  1. Ensure the package is installed: pip install "
                    + package_name
                    + "\n"
                    "  2. Activate your virtual environment if using one\n"
                    "  3. Set MCPYDOC_PYTHON_PATH to specify a custom Python environment path"
                )

        super().__init__(message, details)
        self.package_name = package_name
        self.searched_paths = searched_paths or []


class VersionConflictError(MCPyDocError):
    """Raised when there's a version conflict."""

    def __init__(self, package_name: str, requested: str, found: str) -> None:
        message = f"Version conflict for package '{package_name}'"
        details = f"Requested: {requested}, Found: {found}"
        super().__init__(message, details)
        self.package_name = package_name
        self.requested_version = requested
        self.found_version = found


class ImportError(MCPyDocError):
    """Raised when a module cannot be imported."""

    def __init__(self, module_path: str, original_error: Exception) -> None:
        message = f"Could not import module '{module_path}'"
        details = str(original_error)
        super().__init__(message, details)
        self.module_path = module_path
        self.original_error = original_error


class SymbolNotFoundError(MCPyDocError):
    """Raised when a symbol cannot be found in a module."""

    def __init__(self, symbol_path: str, module_path: str) -> None:
        message = f"Symbol '{symbol_path}' not found in module '{module_path}'"
        super().__init__(message)
        self.symbol_path = symbol_path
        self.module_path = module_path


class SourceCodeUnavailableError(MCPyDocError):
    """Raised when source code is not available for a symbol."""

    def __init__(self, symbol_name: str, reason: Optional[str] = None) -> None:
        message = f"Source code not available for '{symbol_name}'"
        super().__init__(message, reason)
        self.symbol_name = symbol_name


class SecurityError(MCPyDocError):
    """Base class for security-related errors."""

    pass


class ValidationError(SecurityError):
    """Raised when input validation fails."""

    pass


class ResourceLimitError(SecurityError):
    """Raised when resource limits are exceeded."""

    pass


class PackageSecurityError(SecurityError):
    """Raised when package security checks fail."""

    pass
