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
from typing import Any, Dict, List, Optional, Union

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
        # Track client capabilities for roots support
        self._client_capabilities: Dict[str, Any] = {}
        self._client_roots: List[str] = []
        self._pending_requests: Dict[int, Any] = {}
        self._next_request_id = 1
        self._roots_requested = False

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
        """Handle MCP initialize request.

        Captures client capabilities, particularly the 'roots' capability which
        allows us to automatically detect the user's workspace directory.
        """
        # Store client capabilities for later use
        self._client_capabilities = params.get("capabilities", {})

        self.logger.info(f"Client capabilities: {self._client_capabilities}")

        # Check if client supports roots
        if "roots" in self._client_capabilities:
            self.logger.info(
                "Client supports roots capability - will request workspace roots"
            )

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
        # Ensure we've requested roots from client (non-blocking)
        # The response will be processed asynchronously when it arrives
        self._ensure_roots_requested()

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

    def _create_request(
        self, method: str, params: Dict[str, Any] = None
    ) -> tuple[int, str]:
        """Create a JSON-RPC request to send to the client.

        Returns:
            Tuple of (request_id, json_string)
        """
        request_id = self._next_request_id
        self._next_request_id += 1

        request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
        }
        if params:
            request["params"] = params

        return request_id, json.dumps(request)

    def _send_roots_request(self) -> None:
        """Send a roots/list request to the client (non-blocking).

        The response will be handled asynchronously when it arrives.
        """
        if "roots" not in self._client_capabilities:
            self.logger.debug("Client does not support roots capability")
            return

        if self._roots_requested:
            return  # Already sent request

        self.logger.info("Requesting roots from client...")
        self._roots_requested = True

        # Create and send the request
        request_id, request_json = self._create_request("roots/list")
        self._pending_requests[request_id] = None  # Mark as pending (no future needed)

        # Send request to client via stdout
        print(request_json, flush=True)

    def _handle_response(self, response: Dict[str, Any]) -> bool:
        """Handle a JSON-RPC response (to a server-initiated request).

        Returns:
            True if this was a response to a pending request, False otherwise
        """
        response_id = response.get("id")
        if response_id is None:
            return False

        # Check if this is a response to a pending request
        if response_id not in self._pending_requests:
            return False

        # Remove from pending
        self._pending_requests.pop(response_id, None)

        # Handle the response
        if "error" in response:
            self.logger.warning(
                f"Error response for request {response_id}: {response['error']}"
            )
            return True

        result = response.get("result", {})

        # Check if this is a roots/list response
        if "roots" in result:
            self._handle_roots_response(result)

        return True

    def _handle_roots_response(self, result: Dict[str, Any]) -> None:
        """Handle the roots/list response from the client."""
        roots = result.get("roots", [])
        self._client_roots = []

        for root in roots:
            uri = root.get("uri", "")
            # Convert file:// URI to path
            if uri.startswith("file://"):
                path = uri[7:]  # Remove "file://" prefix
                self._client_roots.append(path)
                self.logger.info(f"Client root: {path}")

        # Update working directory based on roots
        if self._client_roots:
            from .subprocess_introspection import set_working_directory

            set_working_directory(self._client_roots[0])
            self.logger.info(
                f"Working directory set from client roots: {self._client_roots[0]}"
            )

            # Refresh the analyzer's environments to pick up the new workspace
            self.mcpydoc.analyzer.refresh_environments()

    def _ensure_roots_requested(self) -> None:
        """Ensure we've requested roots from the client (if supported).

        This is non-blocking - the roots will be processed when the
        response arrives. The first tool call may not have roots available,
        but subsequent calls will.
        """
        if "roots" in self._client_capabilities:
            if not self._roots_requested:
                self._send_roots_request()
            elif self._client_roots:
                self.logger.debug(f"Using cached client roots: {self._client_roots}")

    def _handle_roots_changed(self) -> None:
        """Handle notification that client roots have changed.

        This clears the cached roots and working directory so they
        will be re-fetched on the next tool call.
        """
        self.logger.info("Client roots changed, clearing cached roots")
        self._client_roots = []
        self._roots_requested = False  # Allow re-requesting

        # Clear the working directory so it will be re-fetched
        from .subprocess_introspection import set_working_directory

        set_working_directory(None)

        # Refresh the analyzer's environments (will re-detect when roots arrive)
        self.mcpydoc.analyzer.refresh_environments()

        # Request fresh roots
        self._send_roots_request()

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
                    "methods": (
                        [
                            {
                                "name": m.name,
                                "signature": m.signature,
                                "doc_preview": m.doc_preview,
                            }
                            for m in result.symbol.symbol.methods
                        ]
                        if result.symbol.symbol.methods
                        else None
                    ),
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
                            "type": (
                                result.documentation.returns.get("type")
                                if result.documentation and result.documentation.returns
                                else None
                            ),
                            "description": (
                                result.documentation.returns.get("description")
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

    async def handle_request(self, request_data: str) -> Optional[str]:
        """Handle incoming JSON-RPC request or response.

        Returns:
            JSON response string, or None if this was a response to our request
        """
        try:
            request = json.loads(request_data)
        except json.JSONDecodeError as e:
            error = self._create_error(-32700, "Parse error", str(e))
            return json.dumps(self._create_response(None, error=error))

        # Check if this is a response to a server-initiated request
        method = request.get("method")
        if method is None and ("result" in request or "error" in request):
            # This is a response, not a request
            if self._handle_response(request):
                return None  # Don't send a response back
            # Unknown response, ignore it
            self.logger.warning(f"Received response for unknown request: {request}")
            return None

        request_id = request.get("id")
        params = request.get("params", {})

        try:
            if method == "initialize":
                result = await self._handle_initialize(params)
            elif method == "notifications/initialized":
                # Client is ready, request roots immediately so they're likely
                # available before the first tool call
                self._ensure_roots_requested()
                # This is a notification, so no response needed
                return None
            elif method == "notifications/roots/list_changed":
                # Client's workspace roots changed, refresh our cached roots
                self._handle_roots_changed()
                # This is a notification, so no response needed
                return None
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

                # Handle request (may return None if it was a response to our request)
                response = await self.handle_request(line)

                # Only send response if this was a client request (not a response to us)
                if response is not None:
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
