# MCPyDoc - Python Package Documentation MCP Server

[![CI](https://github.com/amit608/MCPyDoc/workflows/CI/badge.svg)](https://github.com/amit608/MCPyDoc/actions/workflows/ci.yml)
[![PyPI version](https://badge.fury.io/py/mcpydoc.svg)](https://badge.fury.io/py/mcpydoc)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

MCPyDoc is a Model Context Protocol (MCP) server that provides comprehensive documentation and code analysis capabilities for Python packages. It enables AI agents like Cline and GitHub Copilot to understand and work with Python codebases more effectively, especially when working with private libraries and unfamiliar packages.

## ✨ Features

- **📚 Package Documentation**: Get comprehensive docs for any Python package
- **🔍 Symbol Search**: Find classes, functions, and modules by pattern
- **💻 Source Code Access**: Retrieve actual implementation code
- **🏗️ Structure Analysis**: Analyze complete package architecture
- **🔧 Type Hints**: Extract and analyze type annotations
- **📖 Docstring Parsing**: Support for Google, NumPy, and Sphinx formats
- **🏃 High Performance**: Efficient caching and optimized operations
- **🛡️ Error Handling**: Robust error management and validation

## 🚀 Quick Start

### Installation

```bash
# Install from PyPI (Recommended)
pip install mcpydoc
```

Once installed and configured with your AI agent, the server will automatically start when needed.

### Development Installation

If you want to contribute or modify the source code:

```bash
git clone https://github.com/amit608/MCPyDoc.git
cd MCPyDoc
pip install -e .[dev]
```

## 🔌 Integration with you favorite coding AI agent

### Configuration

Add MCPyDoc to your Cline/Claude Code/Cursor/Github Copilot MCP configuration:

```json
{
  "mcpServers": {
    "mcpydoc": {
      "command": "python",
      "args": ["-m", "mcpydoc"],
      "env": {},
      "description": "Python package documentation and code analysis server"
    }
  }
}
```

## 📊 Supported Package Types

- ✅ **Standard Library** - Built-in modules (`json`, `os`, `sys`, etc.)
- ✅ **Third-Party Packages** - pip-installed packages
- ✅ **Local Packages** - Development packages in current environment
- ✅ **Virtual Environments** - Proper path resolution

## 🛠️ API Reference

### Core Methods

#### `get_module_documentation(package, module_path=None, version=None)`
Get comprehensive documentation for a package or specific module.

**Parameters:**
- `package` (str): Package name
- `module_path` (str, optional): Dot-separated path to specific module
- `version` (str, optional): Specific version to use

**Returns:** `ModuleDocumentationResult`

#### `search_package_symbols(package, pattern=None, version=None)`
Search for symbols in a package.

**Parameters:**
- `package` (str): Package name
- `pattern` (str, optional): Search pattern (case-insensitive)
- `version` (str, optional): Specific version to use

**Returns:** `List[SymbolSearchResult]`

#### `get_source_code(package, symbol_name, version=None)`
Get source code for a specific symbol.

**Parameters:**
- `package` (str): Package name
- `symbol_name` (str): Dot-separated path to symbol
- `version` (str, optional): Specific version to use

**Returns:** `SourceCodeResult`

#### `analyze_package_structure(package, version=None)`
Analyze complete package structure.

**Parameters:**
- `package` (str): Package name
- `version` (str, optional): Specific version to use

**Returns:** `PackageStructure`

## 🏗️ Architecture

MCPyDoc uses a clean, modular architecture:

```
mcpydoc/
├── __init__.py          # Package interface
├── __main__.py          # CLI entry point
├── server.py            # Core MCPyDoc class
├── mcp_server.py        # MCP JSON-RPC server
├── analyzer.py          # Package analysis engine
├── documentation.py     # Docstring parsing
├── models.py            # Pydantic data models
├── exceptions.py        # Custom exceptions
└── utils.py             # Utility functions
```

### Key Components

- **Analyzer**: Package introspection and symbol discovery
- **Documentation Parser**: Multi-format docstring parsing
- **MCP Server**: JSON-RPC protocol implementation
- **Models**: Type-safe data structures with Pydantic
- **Exception Handling**: Comprehensive error management

## 📝 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Run the test suite
6. Submit a pull request

---

**Made with ❤️ for the Python community**
