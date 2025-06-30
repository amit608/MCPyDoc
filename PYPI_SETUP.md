# PyPI Publication Setup Guide

This guide explains how to set up PyPI publication for MCPyDoc using GitHub Actions.

## Prerequisites

1. **PyPI Account**: Create accounts on both:
   - [PyPI](https://pypi.org/account/register/) (production)
   - [Test PyPI](https://test.pypi.org/account/register/) (testing)

2. **API Tokens**: Generate API tokens for both platforms:
   - PyPI: Go to Account Settings → API tokens → "Add API token"
   - Test PyPI: Go to Account Settings → API tokens → "Add API token"

## GitHub Repository Setup

### 1. Add Repository Secrets

Go to your GitHub repository → Settings → Secrets and variables → Actions → New repository secret:

- `PYPI_API_TOKEN`: Your PyPI API token (starts with `pypi-`)
- `TEST_PYPI_API_TOKEN`: Your Test PyPI API token (starts with `pypi-`)

### 2. Create Environments (Optional but Recommended)

Go to Settings → Environments and create:
- `pypi` environment for production releases
- `test-pypi` environment for test releases

Add the respective API tokens as environment secrets for additional security.

## Publication Workflows

### Automated Release (Recommended)

1. **Create a Release**:
   ```bash
   git tag v0.1.0
   git push origin v0.1.0
   ```

2. **Create GitHub Release**:
   - Go to GitHub → Releases → "Create a new release"
   - Choose the tag `v0.1.0`
   - Fill in release notes
   - Click "Publish release"

3. **Automatic Publication**:
   - The GitHub Action will automatically build and publish to PyPI
   - Check the Actions tab for progress

### Manual Test Publication

1. **Test on Test PyPI**:
   - Go to GitHub → Actions → "Publish to PyPI"
   - Click "Run workflow"
   - Check "Publish to Test PyPI"
   - Click "Run workflow"

2. **Verify Test Installation**:
   ```bash
   pip install -i https://test.pypi.org/simple/ mcpydoc
   ```

### Manual Production Publication

```bash
# Build locally
python -m build

# Check the build
twine check dist/*

# Upload to Test PyPI first
twine upload --repository-url https://test.pypi.org/legacy/ dist/*

# Upload to PyPI (production)
twine upload dist/*
```

## Release Checklist

Before creating a release:

- [ ] All tests pass (`pytest tests/ -v`)
- [ ] Code is properly formatted (`black mcpydoc tests`)
- [ ] Imports are sorted (`isort mcpydoc tests`)
- [ ] Type checking passes (`mypy mcpydoc`)
- [ ] Version number updated in `pyproject.toml`
- [ ] `CHANGELOG.md` updated with release notes
- [ ] Documentation is up to date

## Version Management

MCPyDoc follows [Semantic Versioning](https://semver.org/):

- **MAJOR** version for incompatible API changes
- **MINOR** version for backwards-compatible functionality additions
- **PATCH** version for backwards-compatible bug fixes

### Version Update Process

1. Update version in `pyproject.toml`:
   ```toml
   version = "0.2.0"
   ```

2. Update version in `mcpydoc/__init__.py`:
   ```python
   __version__ = "0.2.0"
   ```

3. Update `CHANGELOG.md` with release notes

4. Commit and tag:
   ```bash
   git add .
   git commit -m "bump: version 0.2.0"
   git tag v0.2.0
   git push origin main --tags
   ```

## Troubleshooting

### Common Issues

1. **Build Failures**:
   - Check that all dependencies are properly specified
   - Ensure tests pass on all supported Python versions

2. **Upload Failures**:
   - Verify API tokens are correct and have sufficient permissions
   - Check that the package name isn't already taken

3. **Installation Issues**:
   - Test installation in a clean virtual environment
   - Verify all dependencies are available on PyPI

### Security Best Practices

- Never commit API tokens to the repository
- Use environment secrets for production tokens
- Regularly rotate API tokens
- Monitor package downloads for unusual activity

## Post-Publication

After successful publication:

1. **Verify Installation**:
   ```bash
   pip install mcpydoc
   python -c "import mcpydoc; print(mcpydoc.__version__)"
   ```

2. **Update Documentation**:
   - Update installation instructions
   - Add release announcement

3. **Monitor**:
   - Check PyPI analytics
   - Monitor for issues or bug reports
   - Update documentation as needed

## Resources

- [PyPI Documentation](https://packaging.python.org/)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Semantic Versioning](https://semver.org/)
- [Keep a Changelog](https://keepachangelog.com/)
