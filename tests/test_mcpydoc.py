"""Tests for the MCPyDoc MCP server."""

from importlib import metadata

import pytest

from mcpydoc import MCPyDoc, PackageInfo, SymbolInfo
from mcpydoc.exceptions import PackageNotFoundError, SymbolNotFoundError


@pytest.fixture
def server():
    """Create a MCPyDoc server instance."""
    return MCPyDoc()


@pytest.mark.asyncio
async def test_get_package_info(server):
    """Test retrieving package metadata."""
    # Using pytest as it's guaranteed to be installed
    info = server.analyzer.get_package_info("pytest")
    assert isinstance(info, PackageInfo)
    assert info.name == "pytest"
    assert info.version is not None


@pytest.mark.asyncio
async def test_get_package_info_version_matches_installed(server):
    """Ensure retrieved version matches installed package version."""
    info = server.analyzer.get_package_info("pytest")
    installed_version = metadata.version("pytest")
    assert info.version == installed_version


@pytest.mark.asyncio
async def test_get_module_documentation(server):
    """Test retrieving module documentation."""
    docs = await server.get_module_documentation("pytest")
    assert docs.package.name == "pytest"
    assert docs.documentation is not None


@pytest.mark.asyncio
async def test_search_package_symbols(server):
    """Test searching for symbols in a package."""
    # Search for any public symbols in pytest
    results = await server.search_package_symbols("pytest")
    assert len(results) > 0
    # Verify we found some public symbols (not starting with _)
    assert any(
        not r.symbol.name.startswith("_") for r in results
    ), "No public symbols found in pytest"


@pytest.mark.asyncio
async def test_get_source_code(server):
    """Test retrieving source code for a symbol."""
    # Get source code for a function that's likely to have source available
    result = await server.get_source_code("pytest", "main")
    assert result.name == "main"
    assert result.source is not None
    assert "def main" in result.source or "main" in result.source


@pytest.mark.asyncio
async def test_analyze_package_structure(server):
    """Test analyzing package structure."""
    structure = await server.analyze_package_structure("pytest")
    assert structure.package.name == "pytest"
    assert len(structure.modules) >= 0
    assert len(structure.classes) >= 0
    assert len(structure.functions) >= 0


@pytest.mark.asyncio
async def test_package_not_found_error(server):
    """Test handling of non-existent packages."""
    with pytest.raises(PackageNotFoundError):
        server.analyzer.get_package_info("non_existent_package_12345")


@pytest.mark.asyncio
async def test_symbol_not_found_error(server):
    """Test handling of non-existent symbols."""
    with pytest.raises(SymbolNotFoundError):
        server.analyzer.get_symbol_info("pytest", "non_existent_symbol_12345")


@pytest.mark.asyncio
async def test_documentation_parsing(server):
    """Test documentation parsing functionality."""
    # Test with a known function that has documentation
    results = await server.search_package_symbols("pytest", "main")
    if results:
        result = results[0]
        assert result.documentation is not None
        # Should have some documentation fields populated
        assert hasattr(result.documentation, "description")
        assert hasattr(result.documentation, "params")


@pytest.mark.asyncio
async def test_type_hints_extraction(server):
    """Test type hints extraction."""
    # Test with a function that likely has type hints
    results = await server.search_package_symbols("pytest")

    # Find a result with type hints
    typed_result = None
    for result in results:
        if result.type_hints:
            typed_result = result
            break

    # If we found one, verify the structure
    if typed_result:
        assert isinstance(typed_result.type_hints, dict)
        assert all(
            isinstance(k, str) and isinstance(v, str)
            for k, v in typed_result.type_hints.items()
        )


@pytest.mark.asyncio
async def test_version_handling(server):
    """Test version-specific package handling."""
    # Test that we can get package info without specifying version
    info = server.analyzer.get_package_info("pytest")
    assert info.version is not None

    # Test with specific version (should work with current version)
    info_versioned = server.analyzer.get_package_info("pytest", info.version)
    assert info_versioned.version == info.version


@pytest.mark.asyncio
async def test_symbol_kinds(server):
    """Test that different symbol kinds are properly identified."""
    structure = await server.analyze_package_structure("pytest")

    # Check that we're categorizing symbols correctly
    all_symbols = (
        structure.modules + structure.classes + structure.functions + structure.other
    )

    assert len(all_symbols) > 0

    # Verify symbol kinds are properly set
    for symbol_result in all_symbols:
        assert symbol_result.symbol.kind in [
            "module",
            "class",
            "function",
            "method",
            "builtin",
            "property",
            "other",
        ]


@pytest.mark.asyncio
async def test_caching_behavior(server):
    """Test that caching works correctly."""
    # First call should populate cache
    info1 = server.analyzer.get_package_info("pytest")

    # Second call should use cache (should be fast and identical)
    info2 = server.analyzer.get_package_info("pytest")

    assert info1.name == info2.name
    assert info1.version == info2.version

    # Verify cache is actually being used by checking internal state
    assert "pytest" in server.analyzer._version_cache
