# Subprocess-Based Package Introspection

## Overview

MCPyDoc now supports subprocess-based package introspection via package managers (uv, poetry, pipenv). This solves two critical issues:

1. **Python version mismatch**: When MCPyDoc is installed via pipx (e.g., Python 3.14) and tries to introspect packages in a project using a different Python version (e.g., 3.13), C extensions fail to load.
2. **Workspace boundaries**: In uv workspaces or monorepos, different services can have different dependencies that aren't visible from the root.

## How It Works

Instead of importing packages directly into MCPyDoc's Python process, the new implementation:

1. **Searches parent directories** for package manager files (uv.lock, poetry.lock, Pipfile, pyproject.toml)
2. **Verifies the package manager is installed** (checks if `uv`, `poetry`, or `pipenv` commands exist)
3. **Runs introspection scripts** in the project's own Python environment via `uv run python`, `poetry run python`, etc.
4. **Returns serialized package information** as JSON
5. **Falls back to direct import** if no package manager is detected or available

## Architecture

```
MCPyDoc Process (Python 3.14 via pipx)
    │
    ├─ Try: subprocess introspection via package manager
    │       └─ Spawns project's Python (3.13) → C extensions load correctly
    │       └─ Returns JSON with package info, symbols, source code
    │
    └─ Fallback: direct import (current behavior)
            └─ Works for packages without C extensions
```

## Files Changed

### New Files

- **`mcpydoc/subprocess_introspection.py`**: Core subprocess introspection logic
  - `detect_package_manager()`: Detects uv/poetry/pipenv
  - `introspect_package_info()`: Gets package metadata via subprocess
  - `introspect_symbol()`: Gets symbol info via subprocess
  - `search_symbols_subprocess()`: Searches symbols via subprocess
  - Caching for package manager detection and introspection results

- **`tests/test_subprocess_introspection.py`**: Comprehensive test suite
  - Tests for package manager detection
  - Tests for subprocess introspection (success/failure/timeout)
  - Tests for caching behavior
  - Integration tests with PackageAnalyzer

### Modified Files

- **`mcpydoc/analyzer.py`**: Integrated subprocess introspection
  - Added `enable_subprocess` and `working_directory` parameters to `PackageAnalyzer`
  - Modified `get_package_info()` to try subprocess first
  - Modified `get_symbol_info()` to try subprocess first
  - Modified `search_symbols()` to try subprocess first
  - Falls back to direct import if subprocess fails

- **`mcpydoc/exceptions.py`**: Added `SubprocessIntrospectionError`
  - New exception for subprocess failures
  - Includes diagnostic info (runner, exit code, stderr)

- **`mcpydoc/env_detection.py`**: Added documentation reference
  - Updated module docstring to reference subprocess introspection

## Usage

### Automatic (Zero Config)

If your project uses uv, poetry, or pipenv, MCPyDoc will automatically detect and use subprocess introspection:

```bash
# Just open your IDE in the project directory
cd /path/to/your/project
cursor .
```

MCPyDoc will:
1. Detect `uv.lock`, `poetry.lock`, or `Pipfile`
2. Use `uv run python` / `poetry run python` / `pipenv run python`
3. Introspect packages in your project's Python environment

### Manual Configuration

You can disable subprocess introspection if needed:

```python
from mcpydoc.analyzer import PackageAnalyzer

# Disable subprocess introspection
analyzer = PackageAnalyzer(enable_subprocess=False)

# Or specify a different working directory
analyzer = PackageAnalyzer(working_directory=Path("/custom/path"))
```

## Benefits

| Problem | Before | After |
|---------|--------|-------|
| Python version mismatch | ❌ Fails with C extensions (cryptography, numpy, etc.) | ✅ Uses project's Python |
| Workspace dependencies | ❌ Can't see service-specific packages | ✅ Respects workspace boundaries |
| Manual configuration | ⚠️ Required for complex setups | ✅ Zero-config for uv/poetry/pipenv |
| Environment detection | ⚠️ Static path searching | ✅ Dynamic via package manager |

## Examples

### Example 1: Python Version Mismatch (Solved)

**Before:**
```
MCPyDoc (Python 3.14) → import fido2 (built for Python 3.13)
❌ Error: cannot load _cffi_backend.cpython-313.so
```

**After:**
```
MCPyDoc (Python 3.14) → uv run python (Python 3.13) → import fido2
✅ Success: C extensions load correctly
```

### Example 2: uv Workspace (Solved)

**Before:**
```
Root: has shared, gateway-utils
Auth service: has cachetools (not visible from root)

MCPyDoc at root → import cachetools
❌ Error: ModuleNotFoundError
```

**After:**
```
MCPyDoc at auth service → uv run python → import cachetools
✅ Success: uv respects workspace boundaries
```

## Caching

To avoid repeated subprocess calls, introspection results are cached:

- Package manager detection is cached per directory
- Introspection results are cached with a size limit (100 items, FIFO eviction)
- Cache can be cleared with `clear_cache()`

## Testing

Run the test suite:

```bash
# Install dev dependencies
pip install -e .[dev]

# Run subprocess introspection tests
pytest tests/test_subprocess_introspection.py -v

# Run all tests
pytest tests/ -v
```

## Fallback Behavior

If subprocess introspection fails or no package manager is detected:

1. MCPyDoc logs a debug message
2. Falls back to direct import (current behavior)
3. Works for packages without C extensions or version-specific features

## Performance

- **First call**: ~100-500ms (subprocess startup + import)
- **Cached calls**: <1ms (direct cache lookup)
- **Fallback**: Same as before (direct import)

## Limitations

- Requires uv, poetry, or pipenv to be installed
- Subprocess calls have startup overhead (mitigated by caching)
- Timeout set to 15s for package info, 20s for symbols, 45s for search

## Future Enhancements

Potential improvements:

1. Support for conda environments (`conda run python`)
2. Persistent cache across MCPyDoc sessions
3. Background subprocess pool for better performance
4. Support for custom package manager runners

## Related Issues

This implementation addresses:

- Python version mismatch with C extensions (fido2, cryptography, numpy, etc.)
- uv workspace package boundaries
- Monorepo dependency isolation
- Zero-config environment detection for modern Python projects


