"""Core MCP server implementation for Python package documentation."""

from typing import List, Optional

from .analyzer import PackageAnalyzer
from .documentation import DocumentationParser
from .exceptions import (
    SourceCodeUnavailableError,
)
from .models import (
    ModuleDocumentationResult,
    PackageStructure,
    SourceCodeResult, 
    SymbolSearchResult,
)

class MCPyDoc:
    """MCP server for Python package documentation."""

    def __init__(self, python_paths: Optional[List[str]] = None) -> None:
        """Initialize the MCP server.

        Args:
            python_paths: List of paths to Python environments to search for packages.
                        If None, uses the current environment.
        """
        self.analyzer = PackageAnalyzer(python_paths=python_paths)
        self.doc_parser = DocumentationParser()

    async def get_module_documentation(
        self,
        package_name: str,
        module_path: Optional[str] = None,
        version: Optional[str] = None,
    ) -> ModuleDocumentationResult:
        """Get comprehensive documentation for a Python module/class.

        Args:
            package_name: Name of the package containing the module
            module_path: Optional dot-separated path to specific module/class
            version: Optional specific version to use

        Returns:
            ModuleDocumentationResult containing package and symbol documentation

        Raises:
            PackageNotFoundError: If package not found
            ImportError: If module cannot be imported
            SymbolNotFoundError: If symbol cannot be found
        """
        package_info = self.analyzer.get_package_info(package_name, version)

        if module_path:
            symbol_info = self.analyzer.get_symbol_info(package_name, module_path)
            documentation = self.doc_parser.parse_docstring(symbol_info.docstring)
            type_hints = self.analyzer.get_type_hints_safe(symbol_info)

            symbol_result = SymbolSearchResult(
                symbol=symbol_info,
                documentation=documentation,
                type_hints=type_hints,
            )

            return ModuleDocumentationResult(
                package=package_info,
                symbol=symbol_result,
            )
        else:
            # Return package-level documentation
            module = self.analyzer._import_module(package_name, version)
            documentation = self.doc_parser.parse_docstring(module.__doc__)
            
            return ModuleDocumentationResult(
                package=package_info,
                documentation=documentation,
            )

    async def search_package_symbols(
        self,
        package_name: str,
        search_pattern: Optional[str] = None,
        version: Optional[str] = None,
    ) -> List[SymbolSearchResult]:
        """Search for classes, functions, and constants in a package.

        Args:
            package_name: Name of the package to search
            search_pattern: Optional pattern to filter symbols
            version: Optional specific version to use

        Returns:
            List of SymbolSearchResult objects matching the criteria

        Raises:
            PackageNotFoundError: If package not found
            ImportError: If package cannot be imported
        """
        symbols = self.analyzer.search_symbols(package_name, search_pattern)
        results = []

        for symbol in symbols:
            documentation = self.doc_parser.parse_docstring(symbol.docstring)
            type_hints = self.analyzer.get_type_hints_safe(symbol)

            result = SymbolSearchResult(
                symbol=symbol,
                documentation=documentation,
                type_hints=type_hints,
            )
            results.append(result)

        return results

    async def get_source_code(
        self,
        package_name: str,
        symbol_name: str,
        version: Optional[str] = None,
    ) -> SourceCodeResult:
        """Get actual source code for a function/class.

        Args:
            package_name: Name of the package containing the symbol
            symbol_name: Dot-separated path to the symbol
            version: Optional specific version to use

        Returns:
            SourceCodeResult containing symbol information and source code

        Raises:
            PackageNotFoundError: If package not found
            ImportError: If module cannot be imported
            SymbolNotFoundError: If symbol cannot be found
            SourceCodeUnavailableError: If source code is not available
        """
        symbol_info = self.analyzer.get_symbol_info(package_name, symbol_name)
        
        if not symbol_info.source:
            raise SourceCodeUnavailableError(
                symbol_name, "Source code not available for this symbol"
            )

        documentation = self.doc_parser.parse_docstring(symbol_info.docstring)
        type_hints = self.analyzer.get_type_hints_safe(symbol_info)

        return SourceCodeResult(
            name=symbol_info.name,
            kind=symbol_info.kind,
            source=symbol_info.source,
            documentation=documentation,
            type_hints=type_hints,
        )

    async def analyze_package_structure(
        self,
        package_name: str,
        version: Optional[str] = None,
    ) -> PackageStructure:
        """Discover package structure and available modules.

        Args:
            package_name: Name of the package to analyze
            version: Optional specific version to use

        Returns:
            PackageStructure containing package metadata and symbol structure

        Raises:
            PackageNotFoundError: If package not found
            ImportError: If package cannot be imported
        """
        package_info = self.analyzer.get_package_info(package_name, version)
        symbols = self.analyzer.search_symbols(package_name)

        # Group symbols by kind
        modules = []
        classes = []
        functions = []
        other = []

        for symbol in symbols:
            documentation = self.doc_parser.parse_docstring(symbol.docstring)
            type_hints = self.analyzer.get_type_hints_safe(symbol)

            result = SymbolSearchResult(
                symbol=symbol,
                documentation=documentation,
                type_hints=type_hints,
            )

            if symbol.kind == "module":
                modules.append(result)
            elif symbol.kind == "class":
                classes.append(result)
            elif symbol.kind in ("function", "method"):
                functions.append(result)
            else:
                other.append(result)

        # Get package-level documentation
        module = self.analyzer._import_module(package_name, version)
        package_documentation = self.doc_parser.parse_docstring(module.__doc__)

        return PackageStructure(
            package=package_info,
            documentation=package_documentation,
            modules=modules,
            classes=classes,
            functions=functions,
            other=other,
        )
