#!/usr/bin/env python3
"""
Command-line entry point for MCPyDoc MCP server.
"""

import sys
import asyncio
from .mcp_server import main

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
