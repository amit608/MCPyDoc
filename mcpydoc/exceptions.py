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
        self,
        package_name: str,
        searched_paths: Optional[list] = None,
        searched_directories: Optional[list] = None,
    ) -> None:
        message = f"Package '{package_name}' not found"
        details = None

        if searched_paths:
            # Check if running in pipx/uvx isolated environment
            from .env_detection import get_searched_directories, is_pipx_environment

            in_pipx = any(is_pipx_environment(path) for path in searched_paths)

            # Build detailed error message
            details = f"Searched {len(searched_paths)} Python environment(s):\n"
            for i, path in enumerate(searched_paths, 1):
                details += f"  {i}. {path}\n"

            # Add searched directories if available
            if searched_directories:
                details += f"\nSearched {len(searched_directories)} directory(ies) for virtual environments:\n"
                for i, directory in enumerate(searched_directories, 1):
                    details += f"  {i}. {directory}\n"
            else:
                # Try to get from global state
                dirs = get_searched_directories()
                if dirs:
                    details += f"\nSearched {len(dirs)} directory(ies) for virtual environments:\n"
                    for i, directory in enumerate(dirs, 1):
                        details += f"  {i}. {directory}\n"

            # Add helpful suggestions based on context
            if in_pipx:
                details += (
                    "\n💡 MCPyDoc is running in an isolated pipx/uvx environment.\n"
                    "   To access packages from your project, try one of these solutions:\n\n"
                    "   Option 1 - Use environment variable (Recommended):\n"
                    "     Set MCPYDOC_PYTHON_PATH in your MCP configuration:\n"
                    '     "env": { "MCPYDOC_PYTHON_PATH": "/path/to/your/project/.venv" }\n\n'
                    "   Option 2 - Use MCPYDOC_SEARCH_PATHS:\n"
                    '     "env": { "MCPYDOC_SEARCH_PATHS": "~/projects,~/dev" }\n\n'
                    "   Option 3 - Create .mcpydoc.json in your project:\n"
                    '     { "python_path": ".venv" }\n\n'
                    "   Option 4 - Activate your virtual environment:\n"
                    "     source /path/to/your/project/.venv/bin/activate\n"
                    "     Then restart your AI assistant\n"
                )
            else:
                details += (
                    "\n💡 Troubleshooting suggestions:\n\n"
                    f"   1. Install the package:\n"
                    f"      pip install {package_name}\n\n"
                    "   2. If using a virtual environment, ensure it's in a common location:\n"
                    "      - Project/.venv, Project/venv, Project/env\n"
                    "      - Or in ~/projects, ~/dev, ~/code, etc.\n\n"
                    "   3. Configure MCPyDoc to find your environment:\n"
                    "      Set MCPYDOC_PYTHON_PATH or create .mcpydoc.json\n\n"
                    "   4. Check that your project is in a searched directory:\n"
                    "      Use MCPYDOC_SEARCH_PATHS to add custom locations\n"
                )

        super().__init__(message, details)
        self.package_name = package_name
        self.searched_paths = searched_paths or []
        self.searched_directories = searched_directories or []


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


class SubprocessIntrospectionError(MCPyDocError):
    """Raised when subprocess-based introspection fails."""

    def __init__(
        self,
        operation: str,
        runner: Optional[list] = None,
        exit_code: Optional[int] = None,
        stderr: Optional[str] = None,
        original_error: Optional[Exception] = None,
    ) -> None:
        message = f"Subprocess introspection failed during {operation}"
        details_parts = []

        if runner:
            details_parts.append(f"Runner: {' '.join(runner)}")
        if exit_code is not None:
            details_parts.append(f"Exit code: {exit_code}")
        if stderr:
            details_parts.append(f"Stderr: {stderr}")
        if original_error:
            details_parts.append(f"Error: {str(original_error)}")

        details = "\n".join(details_parts) if details_parts else None
        super().__init__(message, details)
        self.operation = operation
        self.runner = runner
        self.exit_code = exit_code
        self.stderr = stderr
        self.original_error = original_error
