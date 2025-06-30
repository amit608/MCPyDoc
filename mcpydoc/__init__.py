"""MCPyDoc - Model Context Protocol server for Python package documentation."""

from .analyzer import PackageAnalyzer
from .documentation import DocumentationParser
from .exceptions import (
    MCPyDocError,
    PackageNotFoundError,
    VersionConflictError,
    ImportError,
    SymbolNotFoundError,
    SourceCodeUnavailableError,
)
from .models import (
    PackageInfo,
    SymbolInfo,
    DocumentationInfo,
    SymbolSearchResult,
    PackageStructure,
    SourceCodeResult,
    ModuleDocumentationResult,
)
from .server import MCPyDoc

__version__ = "0.1.1"

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
