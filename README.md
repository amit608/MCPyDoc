# MCPyDoc - Python Package Documentation MCP Server

[![CI](https://github.com/amit608/MCPyDoc/workflows/CI/badge.svg)](https://github.com/amit608/MCPyDoc/actions/workflows/ci.yml)
[![PyPI version](https://badge.fury.io/py/mcpydoc.svg)](https://badge.fury.io/py/mcpydoc)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

MCPyDoc is a Model Context Protocol (MCP) server that provides comprehensive documentation and code analysis capabilities for Python packages. It enables AI agents like Cline and GitHub Copilot to understand and work with Python codebases more effectively.

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
# Clone the repository
git clone https://github.com/mcpydoc/mcpydoc.git
cd mcpydoc

# Install the package
pip install .
```

### Verify Installation

```bash
# Run all tests to ensure everything works
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=mcpydoc --cov-report=html
```

Once installed and configured with your AI agent, the server will automatically start when needed.

## 🔌 Integration with Cline

### Configuration

Add MCPyDoc to your Cline MCP configuration:

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

### Available Tools

Once configured, Cline will have access to these tools:

- **`get_package_docs`** - Get comprehensive documentation for Python packages
- **`search_symbols`** - Search for classes, functions, and modules
- **`get_source_code`** - Retrieve actual source code
- **`analyze_structure`** - Analyze complete package structure

### Recommended Cline Rules

To help Cline use MCPyDoc effectively, consider adding these rules to your `.clinerules` file:

```markdown
# Python Package Analysis Guidelines

## When to Use MCPyDoc Tools

### Always use MCPyDoc when:
- User asks about Python package functionality or capabilities
- Need to understand how to use a specific Python library
- Looking for specific functions or classes in a package
- Want to see source code implementation details
- Need to understand package structure or available modules
- Troubleshooting Python package usage issues

### Recommended workflow:
1. **Start with `analyze_structure`** to understand package organization
2. **Use `search_symbols`** to find relevant functions/classes
3. **Use `get_package_docs`** for comprehensive documentation of packages/modules
4. **Use `get_package_docs` with `module_path`** for specific method/class documentation
5. **Use `get_source_code`** when you need to see implementation details

### For specific method documentation:
- **Option 1**: `get_package_docs` with `module_path` parameter (e.g., `package="requests", module_path="Session.get"`)
- **Option 2**: `search_symbols` to find the method, then `get_package_docs` for details
- **Option 3**: `get_source_code` for the method implementation and its docstring

### Examples of when to use MCPyDoc:
- "I need to understand how to use the SQLAlchemy Session.query() method - show me its documentation and parameters"
- "How do I use requests to make HTTP calls?"
- "What classes are available in the pathlib module?"
- "Show me the source code for json.loads"
- "What functions does the os module provide for file operations?"
- "How do I use pandas for data analysis?"

### Don't use MCPyDoc for:
- Questions about Python language syntax
- General programming concepts
- Non-Python packages or libraries
- Questions already answered in previous context
```

Place this in your `.clinerules` file to help Cline automatically use MCPyDoc when working with Python packages.

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

## 📈 Performance

- **Package Info**: < 100ms (cached after first request)
- **Symbol Search**: < 200ms for most packages
- **Source Retrieval**: < 150ms
- **Structure Analysis**: < 500ms for typical packages
- **Memory Usage**: < 100MB for normal operations


## 🐛 Troubleshooting

### Common Issues

1. **"Package not found" errors**
   - Ensure the package is installed: `pip install package_name`
   - Check virtual environment activation

2. **Import errors**
   - Verify MCPyDoc installation: `pip install .`
   - Check Python path configuration

3. **Source code unavailable**
   - Some built-in functions don't have accessible source
   - This is expected behavior for C extensions

### Debug Commands

```bash
# Check environment
python -c "import sys; print(f'Python: {sys.version}'); print(f'Prefix: {sys.prefix}')"

# Test basic functionality
python -c "
import asyncio
from mcpydoc import MCPyDoc
async def test():
    mcpydoc = MCPyDoc()
    result = await mcpydoc.get_module_documentation('json')
    print(f'Success: {result.package.name}')
asyncio.run(test())
"
```

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
