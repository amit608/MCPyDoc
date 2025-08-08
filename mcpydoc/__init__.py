"""MCPyDoc - Model Context Protocol server for Python package documentation."""

from .analyzer import PackageAnalyzer
from .documentation import DocumentationParser
from .exceptions import (
    ImportError,
    MCPyDocError,
    PackageNotFoundError,
    SourceCodeUnavailableError,
    SymbolNotFoundError,
    VersionConflictError,
)
from .models import (
    DocumentationInfo,
    ModuleDocumentationResult,
    PackageInfo,
    PackageStructure,
    SourceCodeResult,
    SymbolInfo,
    SymbolSearchResult,
)
from .server import MCPyDoc

__version__ = "0.5.0"

__all__ = [
    # Main server class
    "MCPyDoc",
    # Core components
    "PackageAnalyzer",
    "DocumentationParser",
    # Data models
    "PackageInfo",
    "SymbolInfo",
    "DocumentationInfo",
    "SymbolSearchResult",
    "PackageStructure",
    "SourceCodeResult",
    "ModuleDocumentationResult",
    # Exceptions
    "MCPyDocError",
    "PackageNotFoundError",
    "VersionConflictError",
    "ImportError",
    "SymbolNotFoundError",
    "SourceCodeUnavailableError",
]
