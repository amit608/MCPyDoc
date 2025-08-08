"""Utility functions for MCPyDoc."""

import re
from typing import Any, Dict, List, Optional, Set


def normalize_package_name(name: str) -> str:
    """Normalize a package name for consistent handling.

    Args:
        name: Package name to normalize

    Returns:
        Normalized package name
    """
    return name.lower().replace("-", "_").replace(" ", "_")


def extract_imports_from_docstring(docstring: str) -> Set[str]:
    """Extract import statements mentioned in docstrings.

    Args:
        docstring: Docstring content to analyze

    Returns:
        Set of module names mentioned in imports
    """
    if not docstring:
        return set()

    imports = set()

    # Match patterns like "import module" or "from module import"
    import_patterns = [
        r"import\s+([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*)",
        r"from\s+([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*)\s+import",
    ]

    for pattern in import_patterns:
        matches = re.findall(pattern, docstring)
        imports.update(matches)

    return imports


def filter_private_symbols(symbols: List[str]) -> List[str]:
    """Filter out private symbols (starting with underscore).

    Args:
        symbols: List of symbol names

    Returns:
        List with private symbols removed
    """
    return [symbol for symbol in symbols if not symbol.startswith("_")]


def categorize_symbols_by_type(symbols: Dict[str, Any]) -> Dict[str, List[str]]:
    """Categorize symbols by their type.

    Args:
        symbols: Dictionary mapping symbol names to their info

    Returns:
        Dictionary with symbols categorized by type
    """
    categories: Dict[str, List[str]] = {
        "classes": [],
        "functions": [],
        "methods": [],
        "modules": [],
        "constants": [],
        "other": [],
    }

    for name, info in symbols.items():
        symbol_type = getattr(info, "kind", "other").lower()

        if symbol_type == "class":
            categories["classes"].append(name)
        elif symbol_type == "function":
            categories["functions"].append(name)
        elif symbol_type == "method":
            categories["methods"].append(name)
        elif symbol_type == "module":
            categories["modules"].append(name)
        elif symbol_type in ("constant", "variable"):
            categories["constants"].append(name)
        else:
            categories["other"].append(name)

    return categories


def truncate_source_code(source: str, max_lines: int = 100) -> str:
    """Truncate source code to a maximum number of lines.

    Args:
        source: Source code to truncate
        max_lines: Maximum number of lines to keep

    Returns:
        Truncated source code with ellipsis if truncated
    """
    if not source:
        return source

    lines = source.split("\n")
    if len(lines) <= max_lines:
        return source

    truncated = "\n".join(lines[:max_lines])
    return f"{truncated}\n\n# ... ({len(lines) - max_lines} more lines truncated)"


def safe_eval_type_hint(type_hint: str) -> Optional[str]:
    """Safely evaluate a type hint string representation.

    Args:
        type_hint: Type hint as string

    Returns:
        Cleaned type hint string or None if evaluation fails
    """
    if not type_hint:
        return None

    try:
        # Remove common problematic patterns
        cleaned = type_hint.replace("<class '", "").replace("'>", "")
        cleaned = re.sub(r"__main__\.", "", cleaned)
        cleaned = re.sub(r"typing\.", "", cleaned)

        return cleaned
    except Exception:
        return type_hint


def calculate_documentation_coverage(symbols: List[Any]) -> Dict[str, float]:
    """Calculate documentation coverage statistics.

    Args:
        symbols: List of symbol objects with docstring attributes

    Returns:
        Dictionary with coverage statistics
    """
    if not symbols:
        return {"total": 0, "documented": 0, "coverage": 0.0}

    total = len(symbols)
    documented = sum(1 for symbol in symbols if getattr(symbol, "docstring", None))
    coverage = (documented / total) * 100 if total > 0 else 0.0

    return {
        "total": total,
        "documented": documented,
        "coverage": coverage,
    }


def format_signature_readable(signature: str) -> str:
    """Format a function signature for better readability.

    Args:
        signature: Function signature string

    Returns:
        Formatted signature with better spacing
    """
    if not signature:
        return ""

    # Add spaces around commas and after colons
    formatted = re.sub(r",(?!\s)", ", ", signature)
    formatted = re.sub(r":(?!\s)", ": ", formatted)
    formatted = re.sub(r"\s+", " ", formatted)  # Normalize whitespace

    return formatted


def extract_version_from_module(module: Any) -> Optional[str]:
    """Extract version information from a module.

    Args:
        module: Module object to extract version from

    Returns:
        Version string if found, None otherwise
    """
    version_attrs = ["__version__", "VERSION", "version", "_version"]

    for attr in version_attrs:
        if hasattr(module, attr):
            version = getattr(module, attr)
            if isinstance(version, str):
                return version
            elif hasattr(version, "__str__"):
                return str(version)

    return None


def is_dunder_method(name: str) -> bool:
    """Check if a name is a dunder (double underscore) method.

    Args:
        name: Symbol name to check

    Returns:
        True if it's a dunder method, False otherwise
    """
    return name.startswith("__") and name.endswith("__") and len(name) > 4


def clean_docstring_whitespace(docstring: str) -> str:
    """Clean excessive whitespace from docstrings while preserving structure.

    Args:
        docstring: Docstring to clean

    Returns:
        Cleaned docstring
    """
    if not docstring:
        return ""

    # Split into lines
    lines = docstring.split("\n")

    # Remove leading/trailing empty lines
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()

    if not lines:
        return ""

    # Find minimum indentation (excluding first line and empty lines)
    min_indent = float("inf")
    for line in lines[1:]:
        if line.strip():  # Skip empty lines
            indent = len(line) - len(line.lstrip())
            min_indent = min(min_indent, indent)

    if min_indent == float("inf"):
        min_indent = 0

    # Remove common indentation
    cleaned_lines = [lines[0]]  # First line keeps original indentation
    for line in lines[1:]:
        if line.strip():
            cleaned_lines.append(line[int(min_indent) :])
        else:
            cleaned_lines.append("")

    return "\n".join(cleaned_lines)
