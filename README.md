# MCPyDoc - Python Package Documentation MCP Server

[![CI](https://github.com/amit608/MCPyDoc/workflows/CI/badge.svg)](https://github.com/amit608/MCPyDoc/actions/workflows/ci.yml)
[![PyPI version](https://badge.fury.io/py/mcpydoc.svg)](https://badge.fury.io/py/mcpydoc)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

AI assistants hallucinate when working with unfamiliar Python packages—guessing APIs, wrong signatures, outdated usage. **MCPyDoc fixes that** by giving your assistant real-time access to actual documentation and source code from your environment.

## ✨ Features

- **📚 Package Documentation** - Comprehensive docs for any Python package
- **🔍 Symbol Search** - Find classes, functions, and modules by pattern  
- **💻 Source Code Access** - Retrieve actual implementation code
- **🏗️ Structure Analysis** - Analyze complete package architecture
- **🔧 Auto-Environment Detection** - Finds your project's venv automatically

## 🚀 Quick Start

### Zero Config (Recommended)

With compatible MCP clients (Cursor, VS Code), MCPyDoc **automatically detects your workspace** and virtual environment. Just add to your MCP config:

```json
{
  "mcpServers": {
    "mcpydoc": {
      "command": "uvx",
      "args": ["mcpydoc"]
    }
  }
}
```

> **Alternatives**: Use `pipx run mcpydoc` instead of `uvx`, or install globally with `pip install mcpydoc` and use `python -m mcpydoc`.

### VS Code Extension

For VS Code, install the [**MCPyDoc extension**](https://marketplace.visualstudio.com/items?itemName=amit608.mcpydoc-vscode) for a fully automatic setup.

## 🔧 Environment Detection

MCPyDoc automatically finds your Python environment in this priority order:

1. **MCP Client Roots** - Auto-detected from your IDE workspace (zero config!)
2. **`MCPYDOC_PYTHON_PATH`** - Manual override: `"env": {"MCPYDOC_PYTHON_PATH": "~/myproject/.venv"}`
3. **`VIRTUAL_ENV`** - Activated virtual environment
4. **Common directories** - Searches `~/projects`, `~/dev`, `~/code`, etc.
5. **`MCPYDOC_SEARCH_PATHS`** - Custom: `"env": {"MCPYDOC_SEARCH_PATHS": "~/work,~/repos"}`

### Per-Project Config

Create `.mcpydoc.json` in your project root:
```json
{"python_path": ".venv"}
```

## 🔍 Troubleshooting

**Package not found?**

1. Check your project has a `.venv` or `venv` directory
2. Verify the package is installed: `pip list | grep package-name`
3. If needed, set `MCPYDOC_PYTHON_PATH` explicitly

**MCPyDoc shows "isolated pipx/uvx environment"?**

Add your projects directory:
```json
"env": {"MCPYDOC_SEARCH_PATHS": "~/projects"}
```

Or point directly to your venv:
```json
"env": {"MCPYDOC_PYTHON_PATH": "~/myproject/.venv"}
```

## 📝 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Submit a pull request
