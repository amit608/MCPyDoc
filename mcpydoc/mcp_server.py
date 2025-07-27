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
                    "description": "Get comprehensive documentation for a Python package or module",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "package_name": {
                                "type": "string",
                                "description": "Name of the Python package to analyze",
                            },
                            "module_path": {
                                "type": "string",
                                "description": "Optional dot-separated path to specific module/class within the package",
                            },
                            "version": {
                                "type": "string",
                                "description": "Optional specific version to use",
                            },
                        },
                        "required": ["package_name"],
                    },
                },
                {
                    "name": "search_symbols",
                    "description": "Search for classes, functions, and modules in a Python package",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "package_name": {
                                "type": "string",
                                "description": "Name of the Python package to search",
                            },
                            "pattern": {
                                "type": "string",
                                "description": "Search pattern to filter symbols (case-insensitive substring match)",
                            },
                            "version": {
                                "type": "string",
                                "description": "Optional specific version to use",
                            },
                        },
                        "required": ["package_name"],
                    },
                },
                {
                    "name": "get_source_code",
                    "description": "Get the actual source code for a Python function or class",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "package_name": {
                                "type": "string",
                                "description": "Name of the Python package containing the symbol",
                            },
                            "symbol_name": {
                                "type": "string",
                                "description": "Dot-separated path to the symbol (e.g., 'loads' or 'encoder.JSONEncoder')",
                            },
                            "version": {
                                "type": "string",
                                "description": "Optional specific version to use",
                            },
                        },
                        "required": ["package_name", "symbol_name"],
                    },
                },
                {
                    "name": "analyze_structure",
                    "description": "Analyze the complete structure of a Python package",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "package_name": {
                                "type": "string",
                                "description": "Name of the Python package to analyze",
                            },
                            "version": {
                                "type": "string",
                                "description": "Optional specific version to use",
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
            return {
                "isError": True,
                "content": [{"type": "text", "text": f"Error: {str(e)}"}],
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

        return {
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
                }
                if result.symbol
                else None
            ),
        }

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
                }
                for result in results[:50]  # Limit results for performance
            ],
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
