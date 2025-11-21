# MCPyDoc for VS Code — Real docs for your Python deps

[![GitHub](https://img.shields.io/badge/GitHub-MCPyDoc-blue?logo=github)](https://github.com/amit608/MCPyDoc)
[![PyPI](https://img.shields.io/pypi/v/mcpydoc.svg)](https://pypi.org/project/mcpydoc)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)

AI assistants often hallucinate when code depends on private or unfamiliar Python packages: guessed APIs, wrong signatures, and outdated usage that breaks at runtime. MCPyDoc fixes that by giving your assistant real-time access to the actual documentation and source code of the Python packages installed in your environment.

This extension wires MCPyDoc into VS Code via the MCP Server Definition Provider API. It auto-installs the `mcpydoc` package if missing and exposes it to any MCP‑capable assistant you use in VS Code.

## What you get

- 📚 Live documentation retrieval for any installed Python package
- 🔍 Symbol search across package hierarchies
- 💻 Source code access for real implementations
- 🏗️ Structure analysis (modules, classes, functions)
- 🔧 Type hints and signatures
- 📖 Docstring parsing (Google, NumPy, Sphinx)

## Quick start

1) Install this extension in VS Code.
2) Use an MCP‑capable assistant (e.g., Cline, Cursor, GitHub Copilot).
3) To validate - ask it to consult MCPyDoc, for example:
	 - "Use MCPyDoc to show the docs for requests.get."
	 - "Search symbols in pandas for DataFrame methods."

That's it—no manual configuration required. The extension automatically:
- Detects whether you're using `python`, `python3`, or `py`
- Chooses the best package manager (`pipx`, `uvx`, or `pip`)
- Installs and runs MCPyDoc with optimal isolation

## Requirements

- **Python 3.9+** available as `python`, `python3`, or `py` in your PATH
- **One of the following package managers:**
  - `pipx` (recommended - provides isolated execution)
  - `uvx` / `uv` (fast, modern alternative)
  - `pip` (standard Python package manager)
- If you rely on a virtual environment, ensure that environment is active (or that its Python is first on PATH) so MCPyDoc analyzes the correct installed packages

The extension automatically detects and uses the best available option, with preference for `pipx` or `uvx` for better isolation.

## Example scenario

Fixing a bug in code that calls into a private package:
1) Your assistant queries MCPyDoc automatically
2) It retrieves the class documentation and source
3) It applies the correct method name/signature — no guesswork

## Privacy & security

MCPyDoc reads locally installed package metadata, docstrings, and source to answer queries. Content may be provided to your chosen assistant inside VS Code; review your assistant’s data policies before sharing proprietary code.

## License

MIT License — see the repository [LICENSE](https://github.com/amit608/MCPyDoc/blob/main/LICENSE).
