# MCPyDoc - Python Package Documentation MCP Server

[![CI](https://github.com/amit608/MCPyDoc/workflows/CI/badge.svg)](https://github.com/amit608/MCPyDoc/actions/workflows/ci.yml)
[![PyPI version](https://badge.fury.io/py/mcpydoc.svg)](https://badge.fury.io/py/mcpydoc)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

AI assistants often hallucinate when code depends on private or unfamiliar Python packages: guessed APIs, wrong signatures, and outdated usage that breaks at runtime. MCPyDoc fixes that by giving your assistant real-time access to the actual documentation and source code of the Python packages installed in your environment.

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

### VS Code Extension

For a zero-config setup inside VS Code, install the [**MCPyDoc** extension](https://marketplace.visualstudio.com/items?itemName=amit608.mcpydoc-vscode).
It registers the server using the MCP Server Definition Provider API and
automatically ensures the `mcpydoc` package is available when the server starts.

### Installation for other platforms

```bash
pip install mcpydoc
```

Add MCPyDoc to your platform MCP configuration:

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

Once installed and configured with your AI agent, the server will automatically start when needed.

### Development Installation

If you want to contribute or modify the source code:

```bash
git clone https://github.com/amit608/MCPyDoc.git
cd MCPyDoc
pip install -e .[dev]
```

## 📊 Supported Package Types

- ✅ **Standard Library** - Built-in modules (`json`, `os`, `sys`, etc.)
- ✅ **Third-Party Packages** - pip-installed packages
- ✅ **Local Packages** - Development packages in current environment
- ✅ **Virtual Environments** - Proper path resolution

## 📝 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Run the test suite
6. Submit a pull request

