# Contributing to MCPyDoc

Thank you for your interest in contributing to MCPyDoc! This document provides guidelines and information for contributors.

## 🚀 Quick Start

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/amit608/MCPyDoc.git
   cd mcpydoc
   ```
3. **Set up development environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -e .[dev]
   ```
4. **Run tests** to ensure everything works:
   ```bash
   pytest tests/ -v
   ```

## 🛠️ Development Setup

### Prerequisites

- Python 3.9+
- Git
- Virtual environment (recommended)

### Installation

```bash
# Clone the repository
git clone https://github.com/amit608/MCPyDoc.git
cd mcpydoc

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode with dev dependencies
pip install -e .[dev]

# Verify installation
mcpydoc-server --help
```

## 🧪 Testing

We use pytest for testing. Make sure all tests pass before submitting a PR.

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=mcpydoc --cov-report=html

# Run specific test files
pytest tests/test_mcpydoc.py -v
pytest tests/test_security.py -v

# Run tests matching a pattern
pytest tests/ -k "test_package" -v
```

### Test Categories

- **Unit Tests**: Test individual components and functions
- **Integration Tests**: Test MCP server protocol compliance
- **Package Analysis Tests**: Test various Python package types
- **Security Tests**: Test input validation and security protections
- **Error Handling Tests**: Test edge cases and error conditions

### Writing Tests

When adding new functionality:

1. **Add tests** for new features and bug fixes
2. **Follow existing patterns** in the test suite
3. **Test edge cases** and error conditions
4. **Ensure good coverage** for your changes

Example test structure:
```python
import pytest
from mcpydoc import MCPyDoc

@pytest.mark.asyncio
async def test_your_feature():
    mcpydoc = MCPyDoc()
    result = await mcpydoc.your_method("test_input")
    assert result.expected_property == "expected_value"
```

## 📝 Code Style

We use several tools to maintain code quality:

```bash
# Format code with black
black mcpydoc tests

# Sort imports with isort
isort mcpydoc tests

# Type checking with mypy
mypy mcpydoc

# Run tests with coverage
pytest tests/ --cov=mcpydoc --cov-report=term-missing
```

### Code Style Guidelines

- **Line length**: 88 characters (Black default)
- **Type hints**: Required for all public functions
- **Docstrings**: Google style for all public modules, classes, and functions
- **Import order**: Standard library, third-party, local imports

## 🔧 Project Structure

```
mcpydoc/
├── mcpydoc/              # Main package (clean modular architecture)
│   ├── __init__.py       # Package interface
│   ├── __main__.py       # CLI entry point
│   ├── server.py         # Core MCPyDoc server implementation
│   ├── mcp_server.py     # MCP JSON-RPC server protocol
│   ├── analyzer.py       # Package analysis engine
│   ├── documentation.py  # Docstring parsing and formatting
│   ├── models.py         # Pydantic data models with validation
│   ├── exceptions.py     # Custom exception hierarchy
│   ├── security.py       # Security layer and input validation
│   └── utils.py          # Utility functions and helpers
├── tests/                # Comprehensive test suite
│   ├── test_mcpydoc.py   # Core functionality tests
│   └── test_security.py  # Security implementation tests
├── memory-bank/          # Project documentation and context
├── .github/              # GitHub templates and workflows
│   ├── ISSUE_TEMPLATE/   # Issue templates
│   └── pull_request_template.md
├── pyproject.toml        # Project configuration and dependencies
├── README.md             # Project README
├── LICENSE               # MIT License
└── CONTRIBUTING.md       # This file
```

## 🐛 Reporting Issues

When reporting issues, please include:

1. **Python version**: `python --version`
2. **MCPyDoc version**: `python -c "import mcpydoc; print(mcpydoc.__version__)"`
3. **Operating system**: Windows/macOS/Linux
4. **Error message**: Full traceback if applicable
5. **Minimal reproduction**: Code that reproduces the issue

Use our issue template:

```markdown
## Bug Description
[Brief description of the bug]

## Environment
- Python version: 
- MCPyDoc version: 
- OS: 

## Steps to Reproduce
1. 
2. 
3. 

## Expected Behavior
[What you expected to happen]

## Actual Behavior
[What actually happened]

## Error Message
```
[Error message or traceback]
```
```

## 💡 Feature Requests

We welcome feature requests! Please:

1. **Check existing issues** to avoid duplicates
2. **Describe the use case** clearly
3. **Provide examples** of how the feature would be used
4. **Consider implementation** complexity and compatibility

## 🔄 Pull Request Process

1. **Create a feature branch** from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** following our coding standards

3. **Add tests** for new functionality:
   ```bash
   # Add tests to tests/ directory
   # Ensure they follow existing patterns
   ```

4. **Update documentation** if needed:
   ```bash
   # Update docstrings
   # Update README.md if adding user-facing features
   ```

5. **Run the full test suite**:
   ```bash
   pytest tests/ -v
   black mcpydoc tests
   isort mcpydoc tests
   mypy mcpydoc
   ```

6. **Commit your changes** with clear messages:
   ```bash
   git add .
   git commit -m "feat: add new package analysis feature"
   ```

7. **Push to your fork** and create a pull request:
   ```bash
   git push origin feature/your-feature-name
   ```

### Pull Request Guidelines

- **Title**: Use conventional commit format (feat:, fix:, docs:, etc.)
- **Description**: Explain what the PR does and why
- **Tests**: Include tests for new functionality
- **Documentation**: Update docs for user-facing changes
- **Changelog**: Add entry to CHANGELOG.md if applicable

## 🏷️ Commit Message Convention

We use conventional commits:

- `feat:` - New features
- `fix:` - Bug fixes
- `docs:` - Documentation changes
- `style:` - Code style changes (formatting, etc.)
- `refactor:` - Code refactoring
- `test:` - Adding or updating tests
- `chore:` - Build process or auxiliary tool changes

Examples:
```
feat: add support for class method analysis
fix: handle missing docstrings gracefully
docs: update installation instructions
test: add tests for package structure analysis
```

## 🎯 Areas for Contribution

We especially welcome contributions in these areas:

### Core Features
- **Performance improvements**: Caching, optimization
- **Error handling**: Better error messages and recovery
- **Package support**: Support for more package types
- **Documentation parsing**: Additional docstring formats

### Security & Safety
- **Input validation**: Enhanced security controls and sanitization
- **Resource protection**: Memory and execution time limits
- **Audit logging**: Security event tracking and monitoring
- **Safe imports**: Package import safety mechanisms

### MCP Integration
- **Protocol compliance**: Ensure full MCP compatibility
- **Transport options**: WebSocket, HTTP transports
- **Tool enhancements**: New MCP tools and capabilities

### Developer Experience
- **Testing**: More comprehensive test coverage
- **Documentation**: Better docs and examples
- **Tooling**: Development workflow improvements
- **CI/CD**: GitHub Actions, automation

### Community
- **Examples**: Usage examples and tutorials
- **Integrations**: Plugins for other tools
- **Performance**: Benchmarks and optimizations

## 📚 Resources

- **Model Context Protocol**: [MCP Specification](https://spec.modelcontextprotocol.io/)
- **Python Packaging**: [PyPA Guide](https://packaging.python.org/)
- **Type Hints**: [PEP 484](https://peps.python.org/pep-0484/)
- **Docstring Conventions**: [PEP 257](https://peps.python.org/pep-0257/)

## 🤝 Code of Conduct

This project follows the [Contributor Covenant](https://www.contributor-covenant.org/) Code of Conduct. Please be respectful and inclusive in all interactions.

## ❓ Questions?

- **GitHub Issues**: For bugs and feature requests
- **GitHub Discussions**: For questions and general discussion
- **Documentation**: Check the README and code comments

Thank you for contributing to MCPyDoc! 🎉
