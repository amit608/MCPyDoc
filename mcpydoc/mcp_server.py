#!/usr/bin/env python3
"""
MCP Server implementation for MCPyDoc.

This implements the Model Context Protocol (MCP) JSON-RPC interface
to expose MCPyDoc functionality as tools that can be used by MCP clients like Cline.
"""

import asyncio
import json
import logging
import sys
from typing import Any, Dict, Optional, Union

import mcpydoc

from .exceptions import (
    ValidationError,
)
from .security import (
    audit_log,
    validate_package_name,
    validate_symbol_path,
    validate_version,
)
from .server import MCPyDoc


class MCPServer:
    """MCP JSON-RPC server implementation for MCPyDoc."""

    def __init__(self):
        self.mcpydoc = MCPyDoc()
        self.request_id = 0
        self.logger = logging.getLogger(__name__)

    def _create_response(
        self,
        request_id: Optional[Union[str, int]],
        result: Any = None,
        error: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """Create a JSON-RPC response."""
        response = {"jsonrpc": "2.0", "id": request_id}

        if error:
            response["error"] = error
        else:
            response["result"] = result

        return response

    def _create_error(
        self, code: int, message: str, data: Any = None
    ) -> Dict[str, Any]:
        """Create a JSON-RPC error object."""
        error = {"code": code, "message": message}
        if data:
            error["data"] = data
        return error

    async def _handle_initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle MCP initialize request."""
        return {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}, "resources": {}},
            "serverInfo": {"name": "mcpydoc", "version": mcpydoc.__version__},
        }

    async def _handle_tools_list(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tools/list request."""
        return {
            "tools": [
                {
                    "name": "get_package_docs",
                    "description": "Get real-time comprehensive documentation for Python packages to prevent API hallucination. Essential when working with private libraries, unfamiliar packages, or when you need accurate method signatures instead of guessing. Use this to get actual documentation from the current environment rather than relying on potentially outdated training data. Perfect for understanding package capabilities, method parameters, return types, and usage examples. RECOMMENDED WORKFLOW: For unfamiliar packages, start with analyze_structure first to understand the package organization, then use this tool with the correct module paths. PROGRESSIVE APPROACH: Use 'ClassName' for class overview, then 'ClassName.method_name' for specific method documentation. Try method-level docs before get_source_code - they're often sufficient.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "package_name": {
                                "type": "string",
                                "description": "Name of the Python package to analyze (especially useful for private or unfamiliar packages)",
                            },
                            "module_path": {
                                "type": "string",
                                "description": "Optional path to specific class or module within the package. Use 'ClassName' for class docs, 'ClassName.method_name' for method docs. Examples: 'Session', 'Calculator', 'ClassName.method_name', 'utils.helper_class'",
                            },
                            "version": {
                                "type": "string",
                                "description": "Optional specific version to use (ensures version-accurate documentation)",
                            },
                        },
                        "required": ["package_name"],
                    },
                },
                {
                    "name": "search_symbols",
                    "description": "Discover available classes, functions, and modules in private or unfamiliar Python packages to prevent API guessing and hallucination. Use after analyze_structure when you need to find specific functionality by name. Perfect for exploring what functionality actually exists in a package that may not be in your training data before diving into documentation. Essential for finding the right methods before writing code, discovering package capabilities, or when users ask about available functionality in third-party or private libraries. Returns actual symbol names and signatures from the current environment. Follow up with get_package_docs for detailed documentation of interesting symbols.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "package_name": {
                                "type": "string",
                                "description": "Name of the Python package to search (particularly valuable for private or unfamiliar packages)",
                            },
                            "pattern": {
                                "type": "string",
                                "description": "Search pattern to filter symbols by name (case-insensitive substring match, e.g., 'auth', 'config', 'util')",
                            },
                            "version": {
                                "type": "string",
                                "description": "Optional specific version to ensure accurate symbol discovery",
                            },
                        },
                        "required": ["package_name"],
                    },
                },
                {
                    "name": "get_source_code",
                    "description": "Retrieve actual implementation source code for Python functions or classes to understand exact behavior and avoid implementation guessing. Required when working with private libraries or unfamiliar packages where you need to see the real implementation details, understand complex logic, or verify expected behavior after documentation proves insufficient. Use only when get_package_docs with specific method paths (e.g., 'ClassName.method_name') doesn't provide sufficient detail and always try method documentation first before inspecting source code. Provides the definitive answer to 'how does this function/class actually work?' Perfect for debugging edge cases or when adapting code to work with specific implementations.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "package_name": {
                                "type": "string",
                                "description": "Name of the Python package containing the symbol (especially valuable for private or complex libraries)",
                            },
                            "symbol_name": {
                                "type": "string",
                                "description": "Dot-separated path to the specific function/class/method (e.g., 'MyClass.method_name', 'utility_function')",
                            },
                            "version": {
                                "type": "string",
                                "description": "Optional specific version to ensure source code accuracy",
                            },
                        },
                        "required": ["package_name", "symbol_name"],
                    },
                },
                {
                    "name": "analyze_structure",
                    "description": "Get a comprehensive overview of a Python package's complete structure and organization to understand its architecture before diving into specific components. This is the mandatory starting point when encountering unfamiliar or private packages - use this FIRST to understand the package layout, available modules, main classes, and key functions. Prevents wasted time exploring incorrect paths and provides the foundation for making informed decisions about which specific tools to use next. Essential for understanding large, complex, or poorly documented packages. Follow up with search_symbols for targeted exploration or get_package_docs for specific components.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "package_name": {
                                "type": "string",
                                "description": "Name of the Python package to analyze structure (start here for unfamiliar packages)",
                            },
                            "version": {
                                "type": "string",
                                "description": "Optional specific version to ensure accurate structure analysis",
                            },
                        },
                        "required": ["package_name"],
                    },
                },
            ]
        }

    async def _handle_tools_call(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tools/call request."""
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        try:
            if tool_name == "get_package_docs":
                result = await self._get_package_docs(arguments)
            elif tool_name == "search_symbols":
                result = await self._search_symbols(arguments)
            elif tool_name == "get_source_code":
                result = await self._get_source_code(arguments)
            elif tool_name == "analyze_structure":
                result = await self._analyze_structure(arguments)
            else:
                raise ValueError(f"Unknown tool: {tool_name}")

            return {
                "content": [
                    {"type": "text", "text": json.dumps(result, indent=2, default=str)}
                ]
            }

        except Exception as e:
            # Enhanced error handling with recovery suggestions
            error_message = str(e)
            enhanced_response = {
                "error": error_message,
                "recovery_suggestions": [],
                "common_fixes": [],
            }

            # Provide context-aware recovery suggestions based on the tool and error
            if tool_name == "get_package_docs":
                if "module_path" in str(arguments):
                    module_path = arguments.get("module_path", "")
                    enhanced_response["recovery_suggestions"] = [
                        f"Try analyze_structure first to see the package organization",
                        f"Use search_symbols to find the correct class/method names",
                        f"For class documentation, use module_path='ClassName'",
                        f"For method documentation within a class context, this tool shows class info",
                    ]
                    if "." in module_path:
                        enhanced_response["common_fixes"] = [
                            f"Instead of '{module_path}', try just '{module_path.split('.')[0]}' for class info",
                            f"Or use get_source_code with symbol_name='{module_path}' for method details",
                            f"The module_path parameter is for modules/classes, not class.method paths",
                        ]
                else:
                    enhanced_response["recovery_suggestions"] = [
                        f"Try analyze_structure to see the package organization",
                        f"Use search_symbols to find available classes and functions",
                        f"Add module_path='ClassName' to get specific class documentation",
                    ]

            elif tool_name == "search_symbols" and "not found" in error_message.lower():
                enhanced_response["recovery_suggestions"] = [
                    f"Try analyze_structure to see all available symbols",
                    f"Search with a broader pattern or no pattern to see all symbols",
                    f"Check if the package name is correct and installed",
                ]

            elif tool_name == "get_source_code":
                if "symbol_name" in str(arguments):
                    symbol_name = arguments.get("symbol_name", "")
                    enhanced_response["recovery_suggestions"] = [
                        f"Use analyze_structure to see available classes and methods",
                        f"Try search_symbols to find the correct symbol name",
                        f"For methods, use format 'ClassName.method_name'",
                    ]
                    if "." not in symbol_name:
                        enhanced_response["common_fixes"] = [
                            f"For class methods, use 'ClassName.method_name' format",
                            f"For standalone functions, '{symbol_name}' should work if it exists",
                            f"Check the exact symbol name with search_symbols first",
                        ]
                    else:
                        parts = symbol_name.split(".")
                        enhanced_response["common_fixes"] = [
                            f"Verify '{parts[0]}' is the correct class name",
                            f"Verify '{parts[1]}' is the correct method name",
                            f"Check if symbol exists with search_symbols pattern='{parts[1]}'",
                        ]
                else:
                    enhanced_response["recovery_suggestions"] = [
                        f"Provide symbol_name parameter for the function/method to examine",
                        f"Use search_symbols to find available symbols first",
                    ]

            elif tool_name == "analyze_structure":
                enhanced_response["recovery_suggestions"] = [
                    f"Check if the package name is correct and installed",
                    f"Verify the package is importable in your current environment",
                    f"Try pip install {arguments.get('package_name', 'package_name')} if not installed",
                ]

            else:
                # Generic recovery suggestions
                enhanced_response["recovery_suggestions"] = [
                    f"Try analyze_structure to understand the package organization first",
                    f"Use search_symbols to explore available functionality",
                    f"Check the package name and ensure it's installed",
                ]

            # Add workflow guidance
            enhanced_response["recommended_workflow"] = [
                "1. Start with analyze_structure to see package organization",
                "2. Use search_symbols to find specific classes/methods",
                "3. Use get_package_docs with module_path='ClassName' for class info",
                "4. Use get_source_code with symbol_name='ClassName.method' for implementations",
            ]

            return {
                "isError": True,
                "content": [
                    {"type": "text", "text": json.dumps(enhanced_response, indent=2)}
                ],
            }

    async def _get_package_docs(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get package documentation."""
        package_name = args.get("package_name")
        module_path = args.get("module_path")
        version = args.get("version")

        if not package_name:
            raise ValueError("package_name is required")

        # Validate inputs
        validate_package_name(package_name)
        if module_path:
            validate_symbol_path(module_path)
        validate_version(version)

        # Audit log the operation
        audit_log(
            "mcp_get_package_docs",
            package_name=package_name,
            module_path=module_path,
            version=version,
        )

        result = await self.mcpydoc.get_module_documentation(
            package_name, module_path, version
        )

        response_data = {
            "package": {
                "name": result.package.name,
                "version": result.package.version,
                "summary": result.package.summary,
                "author": result.package.author,
                "license": result.package.license,
                "location": (
                    str(result.package.location) if result.package.location else None
                ),
            },
            "documentation": (
                {
                    "description": (
                        result.documentation.description
                        if result.documentation
                        else None
                    ),
                    "long_description": (
                        result.documentation.long_description
                        if result.documentation
                        else None
                    ),
                    "parameters": [
                        {
                            "name": param.get("name"),
                            "type": param.get("type"),
                            "description": param.get("description"),
                            "default": param.get("default"),
                            "optional": param.get("is_optional"),
                        }
                        for param in (
                            result.documentation.params if result.documentation else []
                        )
                    ],
                    "returns": (
                        {
                            "type": result.documentation.returns.get("type"),
                            "description": result.documentation.returns.get(
                                "description"
                            ),
                        }
                        if result.documentation and result.documentation.returns
                        else None
                    ),
                    "raises": [
                        {
                            "exception": exc.get("type"),
                            "description": exc.get("description"),
                        }
                        for exc in (
                            result.documentation.raises if result.documentation else []
                        )
                    ],
                }
                if result.documentation
                else None
            ),
            "symbol": (
                {
                    "name": result.symbol.symbol.name,
                    "kind": result.symbol.symbol.kind,
                    "module": result.symbol.symbol.module,
                    "signature": result.symbol.symbol.signature,
                    "type_hints": result.symbol.type_hints,
                    "parent_class": result.symbol.parent_class,
                }
                if result.symbol
                else None
            ),
            "suggested_next_steps": result.suggested_next_steps,
            "alternative_paths": result.alternative_paths,
        }
        return response_data

    async def _search_symbols(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Search for symbols in a package."""
        package_name = args.get("package_name")
        pattern = args.get("pattern")
        version = args.get("version")

        if not package_name:
            raise ValueError("package_name is required")

        # Validate inputs
        validate_package_name(package_name)
        if pattern and len(pattern) > 100:
            raise ValidationError(f"Search pattern too long: {len(pattern)} > 100")
        validate_version(version)

        # Audit log the operation
        audit_log(
            "mcp_search_symbols",
            package_name=package_name,
            pattern=pattern,
            version=version,
        )

        results = await self.mcpydoc.search_package_symbols(
            package_name, pattern, version
        )

        return {
            "query": {
                "package": package_name,
                "pattern": pattern,
                "total_results": len(results),
            },
            "symbols": [
                {
                    "name": result.symbol.name,
                    "qualified_name": result.symbol.qualname,
                    "kind": result.symbol.kind,
                    "module": result.symbol.module,
                    "signature": result.symbol.signature,
                    "documentation": (
                        {
                            "description": (
                                result.documentation.description
                                if result.documentation
                                else None
                            ),
                            "long_description": (
                                result.documentation.long_description
                                if result.documentation
                                else None
                            ),
                        }
                        if result.documentation
                        else None
                    ),
                    "type_hints": result.type_hints,
                    "parent_class": result.parent_class,
                }
                for result in results[:50]  # Limit results for performance
            ],
            "suggested_next_steps": (
                [
                    f"Use get_package_docs with module_path='ClassName' for detailed class documentation",
                    f"Use get_package_docs with module_path='ClassName.method_name' for method documentation first",
                    f"Use get_source_code only if method documentation isn't sufficient",
                    f"Try different search patterns if you didn't find what you're looking for",
                ]
                if results
                else [
                    f"Try analyze_structure to see the full package organization first",
                    f"Search with a broader pattern or no pattern to see all symbols",
                    f"Check if the package name is correct",
                ]
            ),
        }

    async def _get_source_code(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get source code for a symbol."""
        package_name = args.get("package_name")
        symbol_name = args.get("symbol_name")
        version = args.get("version")

        if not package_name or not symbol_name:
            raise ValueError("package_name and symbol_name are required")

        # Validate inputs
        validate_package_name(package_name)
        validate_symbol_path(symbol_name)
        validate_version(version)

        # Audit log the operation
        audit_log(
            "mcp_get_source_code",
            package_name=package_name,
            symbol_name=symbol_name,
            version=version,
        )

        result = await self.mcpydoc.get_source_code(package_name, symbol_name, version)

        return {
            "symbol": {
                "name": result.name,
                "kind": result.kind,
                "source_lines": len(result.source.split("\n")) if result.source else 0,
            },
            "source_code": result.source,
            "documentation": (
                {
                    "description": (
                        result.documentation.description
                        if result.documentation
                        else None
                    ),
                    "long_description": (
                        result.documentation.long_description
                        if result.documentation
                        else None
                    ),
                    "parameters": [
                        {
                            "name": param.arg_name,
                            "type": param.type_name,
                            "description": param.description,
                            "default": param.default,
                            "optional": param.optional,
                        }
                        for param in (
                            result.documentation.params if result.documentation else []
                        )
                    ],
                    "returns": (
                        {
                            "type": (
                                result.documentation.returns.type_name
                                if result.documentation and result.documentation.returns
                                else None
                            ),
                            "description": (
                                result.documentation.returns.description
                                if result.documentation and result.documentation.returns
                                else None
                            ),
                        }
                        if result.documentation and result.documentation.returns
                        else None
                    ),
                }
                if result.documentation
                else None
            ),
            "type_hints": result.type_hints,
        }

    async def _analyze_structure(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze package structure."""
        package_name = args.get("package_name")
        version = args.get("version")

        if not package_name:
            raise ValueError("package_name is required")

        # Validate inputs
        validate_package_name(package_name)
        validate_version(version)

        # Audit log the operation
        audit_log("mcp_analyze_structure", package_name=package_name, version=version)

        result = await self.mcpydoc.analyze_package_structure(package_name, version)

        return {
            "package": {
                "name": result.package.name,
                "version": result.package.version,
                "summary": result.package.summary,
                "location": (
                    str(result.package.location) if result.package.location else None
                ),
            },
            "documentation": (
                {
                    "description": (
                        result.documentation.description
                        if result.documentation
                        else None
                    ),
                    "long_description": (
                        result.documentation.long_description
                        if result.documentation
                        else None
                    ),
                }
                if result.documentation
                else None
            ),
            "structure": {
                "total_symbols": len(result.modules)
                + len(result.classes)
                + len(result.functions)
                + len(result.other),
                "modules": len(result.modules),
                "classes": len(result.classes),
                "functions": len(result.functions),
                "other": len(result.other),
            },
            "modules": [
                {
                    "name": mod.symbol.name,
                    "documentation": (
                        mod.documentation.description if mod.documentation else None
                    ),
                }
                for mod in result.modules[:10]  # Limit for readability
            ],
            "classes": [
                {
                    "name": cls.symbol.name,
                    "documentation": (
                        cls.documentation.description if cls.documentation else None
                    ),
                    "signature": cls.symbol.signature,
                }
                for cls in result.classes[:10]  # Limit for readability
            ],
            "functions": [
                {
                    "name": func.symbol.name,
                    "documentation": (
                        func.documentation.description if func.documentation else None
                    ),
                    "signature": func.symbol.signature,
                }
                for func in result.functions[:10]  # Limit for readability
            ],
            "suggested_next_steps": result.suggested_next_steps,
        }

    async def handle_request(self, request_data: str) -> str:
        """Handle incoming JSON-RPC request."""
        try:
            request = json.loads(request_data)
        except json.JSONDecodeError as e:
            error = self._create_error(-32700, "Parse error", str(e))
            return json.dumps(self._create_response(None, error=error))

        request_id = request.get("id")
        method = request.get("method")
        params = request.get("params", {})

        try:
            if method == "initialize":
                result = await self._handle_initialize(params)
            elif method == "tools/list":
                result = await self._handle_tools_list(params)
            elif method == "tools/call":
                result = await self._handle_tools_call(params)
            else:
                error = self._create_error(-32601, f"Method not found: {method}")
                return json.dumps(self._create_response(request_id, error=error))

            return json.dumps(self._create_response(request_id, result=result))

        except Exception as e:
            self.logger.exception(f"Error handling request: {e}")
            error = self._create_error(-32603, "Internal error", str(e))
            return json.dumps(self._create_response(request_id, error=error))

    async def run_stdio(self):
        """Run MCP server using stdio transport."""
        self.logger.info("Starting MCPyDoc MCP server on stdio")

        while True:
            try:
                # Read request from stdin
                line = await asyncio.get_event_loop().run_in_executor(
                    None, sys.stdin.readline
                )
                if not line:
                    break

                line = line.strip()
                if not line:
                    continue

                # Handle request
                response = await self.handle_request(line)

                # Send response to stdout
                print(response, flush=True)

            except KeyboardInterrupt:
                break
            except Exception as e:
                self.logger.exception(f"Error in stdio loop: {e}")
                error = self._create_error(-32603, "Internal error", str(e))
                response = json.dumps(self._create_response(None, error=error))
                print(response, flush=True)

        self.logger.info("MCPyDoc MCP server stopped")


async def main():
    """Main entry point for the MCP server."""
    logging.basicConfig(level=logging.INFO)
    server = MCPServer()
    await server.run_stdio()


if __name__ == "__main__":
    asyncio.run(main())
