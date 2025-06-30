"""Data models for MCPyDoc."""

from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class PackageInfo(BaseModel):
    """Information about a Python package."""

    model_config = ConfigDict(frozen=True)

    name: str = Field(..., description="Package name")
    version: str = Field(..., description="Package version")
    summary: Optional[str] = Field(None, description="Package summary")
    author: Optional[str] = Field(None, description="Package author")
    license: Optional[str] = Field(None, description="Package license")
    location: Optional[Path] = Field(None, description="Package installation location")


class SymbolInfo(BaseModel):
    """Information about a Python symbol (function, class, etc.)."""

    model_config = ConfigDict(frozen=True)

    name: str = Field(..., description="Symbol name")
    qualname: str = Field(..., description="Qualified name")
    kind: str = Field(..., description="Symbol kind (class, function, module, etc.)")
    module: str = Field(..., description="Module containing the symbol")
    docstring: Optional[str] = Field(None, description="Symbol docstring")
    signature: Optional[str] = Field(None, description="Symbol signature")
    source: Optional[str] = Field(None, description="Source code")


class DocumentationInfo(BaseModel):
    """Structured documentation information."""

    model_config = ConfigDict(frozen=True)

    description: Optional[str] = Field(None, description="Short description")
    long_description: Optional[str] = Field(None, description="Long description")
    params: List[Dict[str, Any]] = Field(default_factory=list, description="Parameters")
    returns: Optional[Dict[str, Any]] = Field(None, description="Return information")
    raises: List[Dict[str, Any]] = Field(
        default_factory=list, description="Exceptions raised"
    )
    examples: List[str] = Field(default_factory=list, description="Usage examples")
    notes: List[str] = Field(default_factory=list, description="Additional notes")
    references: List[str] = Field(default_factory=list, description="References")


class SymbolSearchResult(BaseModel):
    """Result of a symbol search operation."""

    model_config = ConfigDict(frozen=True)

    symbol: SymbolInfo = Field(..., description="Symbol information")
    documentation: DocumentationInfo = Field(..., description="Parsed documentation")
    type_hints: Dict[str, str] = Field(default_factory=dict, description="Type hints")


class PackageStructure(BaseModel):
    """Package structure analysis result."""

    model_config = ConfigDict(frozen=True)

    package: PackageInfo = Field(..., description="Package information")
    documentation: DocumentationInfo = Field(..., description="Package documentation")
    modules: List[SymbolSearchResult] = Field(
        default_factory=list, description="Modules"
    )
    classes: List[SymbolSearchResult] = Field(
        default_factory=list, description="Classes"
    )
    functions: List[SymbolSearchResult] = Field(
        default_factory=list, description="Functions"
    )
    other: List[SymbolSearchResult] = Field(
        default_factory=list, description="Other symbols"
    )


class SourceCodeResult(BaseModel):
    """Result of source code retrieval."""

    model_config = ConfigDict(frozen=True)

    name: str = Field(..., description="Symbol name")
    kind: str = Field(..., description="Symbol kind")
    source: str = Field(..., description="Source code")
    documentation: DocumentationInfo = Field(..., description="Parsed documentation")
    type_hints: Dict[str, str] = Field(default_factory=dict, description="Type hints")


class ModuleDocumentationResult(BaseModel):
    """Result of module documentation retrieval."""

    model_config = ConfigDict(frozen=True)

    package: PackageInfo = Field(..., description="Package information")
    symbol: Optional[SymbolSearchResult] = Field(None, description="Symbol information")
    documentation: Optional[DocumentationInfo] = Field(
        None, description="Module documentation"
    )
