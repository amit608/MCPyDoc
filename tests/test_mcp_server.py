import json

import pytest

import mcpydoc
from mcpydoc.mcp_server import MCPServer


@pytest.mark.asyncio
async def test_initialize_reports_correct_version():
    server = MCPServer()
    response_json = await server.handle_request(
        json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
    )
    response = json.loads(response_json)
    assert response["result"]["serverInfo"]["version"] == mcpydoc.__version__
