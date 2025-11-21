# MCPyDoc - Python Package Documentation MCP Server

[![CI](https://github.com/amit608/MCPyDoc/workflows/CI/badge.svg)](https://github.com/amit608/MCPyDoc/actions/workflows/ci.yml)
[![PyPI version](https://badge.fury.io/py/mcpydoc.svg)](https://badge.fury.io/py/mcpydoc)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

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

### Installation for PyCharm AI Assistant

1. **Install MCPyDoc** in the Python interpreter PyCharm will use for AI Assistant:

   ```bash
   pip install mcpydoc
   ```

   > 💡 If you use multiple interpreters/virtual environments, make sure `mcpydoc` is installed in the same environment PyCharm uses for MCP servers.
   > You can check or change this in **Settings → Project → Python Interpreter**.

2. **Open MCP configuration**:
   Go to **Settings → Tools → AI Assistant → Model Context Protocol (MCP)**.

3. **Add a new server**:

   * Click **Add → As JSON**, and paste:

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

     Or use **Add → Command** and fill:

     * **Command**: `python`
     * **Arguments**: `-m mcpydoc`

4. **Apply and restart AI Assistant**:
   PyCharm will launch MCPyDoc automatically when the AI Assistant starts.

### Installation for Other Platforms

#### Option 1: No Installation Required (Recommended)

Use `pipx` to run MCPyDoc without installing it first:

```json
{
  "mcpServers": {
    "mcpydoc": {
      "command": "pipx",
      "args": ["run", "mcpydoc"],
      "description": "Python package documentation and code analysis server"
    }
  }
}
```

> **💡 Alternative**: You can also use `uvx` instead of `pipx` - just replace `"command": "pipx"` with `"command": "uvx"` and `"args": ["run", "mcpydoc"]` with `"args": ["mcpydoc"]`.

Alternatively, if you prefer to install it once:
```bash
pipx install mcpydoc
```

Then use:
```json
{
  "mcpServers": {
    "mcpydoc": {
      "command": "mcpydoc",
      "args": [],
      "description": "Python package documentation and code analysis server"
    }
  }
}
```

#### Option 2: Traditional pip Installation

1. **Install MCPyDoc**:
   ```bash
   pip install mcpydoc
   ```

2. **Add to your MCP configuration**:
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

   > **💡 Platform Note**: On some Linux/macOS systems, you may need to use `python3` instead of `python`. To check which command is available, run `python --version` or `python3 --version` in your terminal.

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

## 🔧 Environment Detection

MCPyDoc automatically detects and uses the correct Python environment for your project, even when installed via pipx or uvx. This ensures it can access packages installed in your working repository.

### How It Works

MCPyDoc searches for Python environments in the following order:

1. **`MCPYDOC_PYTHON_PATH`** environment variable (manual override)
2. **`VIRTUAL_ENV`** environment variable (activated virtual environment)
3. **Virtual environment in current directory** (`.venv/`, `venv/`, `env/`, `.env/`)
4. **Poetry environments** (detected via `poetry.toml` or `pyproject.toml`)
5. **System Python** (if not in pipx/uvx isolated environment)
6. **Current environment** (fallback)

### Configuration

If automatic detection doesn't work for your setup, you can manually specify the Python environment:

```bash
# Set the environment variable before running your AI assistant
export MCPYDOC_PYTHON_PATH=/path/to/your/project/.venv

# Or add it to your MCP configuration
{
  "mcpServers": {
    "mcpydoc": {
      "command": "python",
      "args": ["-m", "mcpydoc"],
      "env": {
        "MCPYDOC_PYTHON_PATH": "/path/to/your/project/.venv"
      }
    }
  }
}
```

## 🔍 Troubleshooting

### Package Not Found Errors

If MCPyDoc can't find a package that you know is installed:

1. **Activate your virtual environment** before starting your AI assistant:
   ```bash
   source .venv/bin/activate  # Linux/macOS
   .venv\Scripts\activate     # Windows
   ```

2. **Create a virtual environment in your project** if you don't have one:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install your-package
   ```

3. **Use the `MCPYDOC_PYTHON_PATH` environment variable** to point to your Python environment:
   ```bash
   export MCPYDOC_PYTHON_PATH=/path/to/your/.venv
   ```

4. **Check which environments MCPyDoc is searching**: The error message will list all searched paths and provide context-aware suggestions.

### pipx/uvx Installations

When MCPyDoc is installed via pipx or uvx, it runs in an isolated environment. The environment detection feature automatically handles this by:

- Detecting when running in a pipx/uvx isolated environment
- Prioritizing your project's virtual environment over the isolated environment
- Providing clear error messages with setup instructions when packages aren't found

For best results with pipx/uvx:
- Work in a directory with a virtual environment (`.venv`, `venv`, etc.)
- Or activate your project's virtual environment before starting the AI assistant
- Or set `MCPYDOC_PYTHON_PATH` in your MCP server configuration

## 📝 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Run the test suite
6. Submit a pull request
