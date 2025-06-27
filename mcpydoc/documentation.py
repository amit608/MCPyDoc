"""Documentation parsing and formatting functionality."""

from typing import Optional

from docstring_parser import parse
from docstring_parser.common import ParseError

from .models import DocumentationInfo

class DocumentationParser:
    """Parses and formats Python docstrings."""

    def parse_docstring(self, docstring: Optional[str]) -> DocumentationInfo:
        """Parse a docstring into structured documentation.

        Args:
            docstring: The docstring to parse

        Returns:
            DocumentationInfo object containing structured documentation
        """
        if not docstring:
            return DocumentationInfo()

        try:
            parsed = parse(docstring)
            return self._build_documentation_info(parsed)
        except (ParseError, Exception):
            # Fall back to basic parsing if structured parsing fails
            return self._parse_basic_docstring(docstring)

    def _build_documentation_info(self, parsed) -> DocumentationInfo:
        """Build DocumentationInfo from parsed docstring."""
        params = []
        for param in parsed.params:
            param_info = {
                "name": param.arg_name,
                "description": param.description,
                "type": param.type_name,
                "default": param.default,
                "is_optional": param.is_optional,
            }
            params.append(param_info)

        returns = None
        if parsed.returns:
            returns = {
                "description": parsed.returns.description,
                "type": parsed.returns.type_name,
            }

        raises = []
        for raise_info in parsed.raises:
            raises.append({
                "type": raise_info.type_name,
                "description": raise_info.description,
            })

        # Extract examples and other sections
        examples = []
        notes = []
        references = []

        for meta in parsed.meta:
            content = meta.description or ""
            if meta.args:
                args_lower = " ".join(meta.args).lower()
                if "example" in args_lower:
                    examples.append(content)
                elif "note" in args_lower:
                    notes.append(content)
                elif any(keyword in args_lower for keyword in ["see", "ref", "reference"]):
                    references.append(content)

        return DocumentationInfo(
            description=parsed.short_description,
            long_description=parsed.long_description,
            params=params,
            returns=returns,
            raises=raises,
            examples=examples,
            notes=notes,
            references=references,
        )

    def _parse_basic_docstring(self, docstring: str) -> DocumentationInfo:
        """Parse docstring with basic text processing as fallback."""
        lines = docstring.strip().split("\n")
        if not lines:
            return DocumentationInfo()

        # First non-empty line is the description
        description = lines[0].strip()
        
        # Look for additional content
        long_description_lines = []
        examples = []
        notes = []
        
        current_section = None
        for line in lines[1:]:
            line = line.strip()
            if not line:
                continue
                
            line_lower = line.lower()
            if any(keyword in line_lower for keyword in ["example:", "examples:"]):
                current_section = "examples"
                continue
            elif any(keyword in line_lower for keyword in ["note:", "notes:"]):
                current_section = "notes"
                continue
            elif line.startswith(">>>") or line.startswith("..."):
                # Code example
                if current_section != "examples":
                    examples.append(line)
                continue
                
            if current_section == "examples":
                examples.append(line)
            elif current_section == "notes":
                notes.append(line)
            else:
                long_description_lines.append(line)

        long_description = "\n".join(long_description_lines) if long_description_lines else None

        return DocumentationInfo(
            description=description,
            long_description=long_description,
            examples=examples,
            notes=notes,
        )

    def format_documentation(self, doc_info: DocumentationInfo) -> str:
        """Format documentation info into a readable string.

        Args:
            doc_info: DocumentationInfo to format

        Returns:
            Formatted documentation string
        """
        parts = []

        if doc_info.description:
            parts.append(doc_info.description)

        if doc_info.long_description:
            parts.append("")
            parts.append(doc_info.long_description)

        if doc_info.params:
            parts.append("")
            parts.append("Parameters:")
            for param in doc_info.params:
                param_line = f"  {param['name']}"
                if param.get("type"):
                    param_line += f" ({param['type']})"
                if param.get("description"):
                    param_line += f": {param['description']}"
                if param.get("default"):
                    param_line += f" (default: {param['default']})"
                parts.append(param_line)

        if doc_info.returns:
            parts.append("")
            parts.append("Returns:")
            return_line = "  "
            if doc_info.returns.get("type"):
                return_line += f"{doc_info.returns['type']}: "
            if doc_info.returns.get("description"):
                return_line += doc_info.returns["description"]
            parts.append(return_line)

        if doc_info.raises:
            parts.append("")
            parts.append("Raises:")
            for raise_info in doc_info.raises:
                raise_line = f"  {raise_info.get('type', 'Exception')}"
                if raise_info.get("description"):
                    raise_line += f": {raise_info['description']}"
                parts.append(raise_line)

        if doc_info.examples:
            parts.append("")
            parts.append("Examples:")
            for example in doc_info.examples:
                parts.append(f"  {example}")

        if doc_info.notes:
            parts.append("")
            parts.append("Notes:")
            for note in doc_info.notes:
                parts.append(f"  {note}")

        if doc_info.references:
            parts.append("")
            parts.append("References:")
            for ref in doc_info.references:
                parts.append(f"  {ref}")

        return "\n".join(parts)
