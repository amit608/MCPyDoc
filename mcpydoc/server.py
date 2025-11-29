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

            # Generate suggested next steps
            suggested_next_steps = []
            if symbol_info.kind == "class":
                suggested_next_steps.extend(
                    [
                        f"Use search_symbols with pattern='method_name' to find methods in {symbol_info.name}",
                        f"Use get_source_code with symbol_name='{module_path}' to see the full implementation",
                    ]
                )
            elif symbol_info.kind == "method":
                suggested_next_steps.extend(
                    [
                        f"Use get_source_code with symbol_name='{module_path}' to see the method implementation",
                        f"Check the parent class documentation for context",
                    ]
                )

            # Generate alternative paths for common mistakes
            alternative_paths = []
            if "." not in module_path:
                # Try common submodule patterns
                alternative_paths.extend(
                    [
                        f"calculator.{module_path}",
                        f"core.{module_path}",
                        f"main.{module_path}",
                    ]
                )

            return ModuleDocumentationResult(
                package=package_info,
                symbol=symbol_result,
                suggested_next_steps=suggested_next_steps,
                alternative_paths=alternative_paths,
            )
        else:
            # Return package-level documentation
            # Use get_package_docstring which uses subprocess introspection
            docstring = self.analyzer.get_package_docstring(package_name, version)
            documentation = self.doc_parser.parse_docstring(docstring)

            # Suggest starting points for package exploration
            suggested_next_steps = [
                f"Use analyze_structure to see the full package organization",
                f"Use search_symbols to find specific classes or functions",
                f"Look for main classes or entry points in the package",
            ]

            return ModuleDocumentationResult(
                package=package_info,
                documentation=documentation,
                suggested_next_steps=suggested_next_steps,
                alternative_paths=[],
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
        symbols = self.analyzer.search_symbols(package_name, search_pattern, version)
        results = []

        for symbol in symbols:
            documentation = self.doc_parser.parse_docstring(symbol.docstring)
            type_hints = self.analyzer.get_type_hints_safe(symbol)

            # Determine parent class for methods
            parent_class = None
            if symbol.kind == "method" and "." in symbol.qualname:
                parent_class = symbol.qualname.split(".")[-2]

            result = SymbolSearchResult(
                symbol=symbol,
                documentation=documentation,
                type_hints=type_hints,
                parent_class=parent_class,
            )
            results.append(result)

        # Sort results with exact matches first, then partial matches
        def sort_key(result):
            if search_pattern:
                name = result.symbol.name.lower()
                pattern = search_pattern.lower()
                if name == pattern:
                    return 0  # Exact match - highest priority
                elif pattern in name:
                    return 1  # Partial match - medium priority
                else:
                    return 2  # Other matches - lowest priority
            return 0  # No pattern, maintain original order

        results.sort(key=sort_key)
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

        # Get package-level documentation using subprocess introspection
        docstring = self.analyzer.get_package_docstring(package_name, version)
        package_documentation = self.doc_parser.parse_docstring(docstring)

        # Generate suggested next steps based on what was found
        suggested_next_steps = []
        if classes:
            main_class = classes[0].symbol.name  # Most likely main class
            suggested_next_steps.extend(
                [
                    f"Use get_package_docs with module_path='{main_class}' to explore the main class",
                    f"Use search_symbols with pattern='method_name' to find specific methods",
                    f"Use get_source_code to see implementations of interesting classes",
                ]
            )
        elif functions:
            main_function = functions[0].symbol.name
            suggested_next_steps.extend(
                [
                    f"Use get_package_docs with module_path='{main_function}' to get function details",
                    f"Use get_source_code to see function implementations",
                ]
            )
        else:
            suggested_next_steps.extend(
                [
                    f"Use search_symbols with a specific pattern to find symbols",
                    f"Try exploring submodules if this package has them",
                ]
            )

        return PackageStructure(
            package=package_info,
            documentation=package_documentation,
            modules=modules,
            classes=classes,
            functions=functions,
            other=other,
            suggested_next_steps=suggested_next_steps,
        )
