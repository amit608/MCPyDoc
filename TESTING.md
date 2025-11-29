# Testing Environment Detection

This document describes how to test the environment detection feature, especially in pipx/uvx setups.

## Manual Testing Scenarios

### Scenario 1: pipx Installation with Project Virtual Environment

1. Install MCPyDoc via pipx:
   ```bash
   pipx install mcpydoc
   ```

2. Create a test project with a virtual environment:
   ```bash
   mkdir ~/test-project
   cd ~/test-project
   python3 -m venv .venv
   source .venv/bin/activate
   pip install requests  # or any package
   ```

3. Test that MCPyDoc can find the package:
   ```bash
   # Use the MCP tools through your AI assistant (Cursor, etc.)
   # or create a test script:
   python3 -c "
   from mcpydoc.analyzer import PackageAnalyzer
   analyzer = PackageAnalyzer()
   print('Python paths:', analyzer._python_paths)
   info = analyzer.get_package_info('requests')
   print(f'Found {info.name} version {info.version}')
   "
   ```

**Expected Result**: MCPyDoc should detect the `.venv` directory and find the `requests` package.

### Scenario 2: Using MCPYDOC_PYTHON_PATH

1. Install MCPyDoc via pipx
2. Set the environment variable:
   ```bash
   export MCPYDOC_PYTHON_PATH=/path/to/your/project/.venv
   ```
3. Run the test

**Expected Result**: MCPyDoc should use the specified path first.

### Scenario 3: Activated Virtual Environment

1. Install MCPyDoc via pipx
2. Activate your project's virtual environment:
   ```bash
   source /path/to/project/.venv/bin/activate
   ```
3. Launch your AI assistant

**Expected Result**: MCPyDoc should detect `VIRTUAL_ENV` and use that environment.

### Scenario 4: No Virtual Environment (Error Case)

1. Install MCPyDoc via pipx
2. Navigate to a directory without a virtual environment
3. Try to access a package not installed in the pipx environment

**Expected Result**: Clear error message explaining:
- That MCPyDoc is running in an isolated pipx environment
- How to activate a virtual environment
- How to use `MCPYDOC_PYTHON_PATH`
- How to create a virtual environment

## Automated Testing

To run the full test suite (requires dependencies):

```bash
cd MCPyDoc
pip install -e .[dev]
pytest tests/ -v
```

## Verification Checklist

- [ ] Environment detection finds `.venv` in current directory
- [ ] Environment detection respects `VIRTUAL_ENV` variable
- [ ] Environment detection respects `MCPYDOC_PYTHON_PATH` variable
- [ ] Detects pipx/uvx isolated environments
- [ ] Provides helpful error messages when package not found
- [ ] Works with Poetry projects
- [ ] Works with standard venv setups
- [ ] Falls back gracefully when no project environment exists

## Debugging

To see which environments MCPyDoc is searching:

```python
import logging
logging.basicConfig(level=logging.INFO)

from mcpydoc.env_detection import get_active_python_environments
paths = get_active_python_environments()
print("Detected environments:", paths)
```

The logs will show:
- Which environments were detected
- Priority order
- Whether running in pipx/uvx
- Which environment a package was found in

