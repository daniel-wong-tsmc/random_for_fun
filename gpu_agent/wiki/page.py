from __future__ import annotations
import json
from typing import Literal, Optional
from pydantic import BaseModel, Field


class WikiFormatError(ValueError):
    """Raised when a wiki page file cannot be parsed (fail loud, never half-parse)."""


class WikiPage(BaseModel):
    """The code-owned frontmatter header of a wiki thread (the body is stored separately)."""
    id: str
    type: Literal["entity", "theme"]
    title: str
    category: Optional[str] = None
    status: Literal["provisional", "registered"] = "provisional"
    state: str = ""
    trajectory: str = ""
    salience: float = 0.0
    crossRefs: list[str] = Field(default_factory=list)
    createdAsOf: str
    lastUpdatedAsOf: str


def dump_page(page: WikiPage, body: str) -> str:
    """Serialize to '---\\n<key: json-value lines>\\n---\\n<body>'. JSON is a YAML-flow subset."""
    lines = ["---"]
    for key, value in page.model_dump().items():
        lines.append(f"{key}: {json.dumps(value)}")
    lines.append("---")
    return "\n".join(lines) + "\n" + body


def load_page(text: str) -> tuple[WikiPage, str]:
    if not text.startswith("---\n"):
        raise WikiFormatError("missing opening frontmatter fence")
    parts = text.split("---\n", 2)  # first two fences only; a body '---' survives
    if len(parts) < 3:
        raise WikiFormatError("missing closing frontmatter fence")
    _, frontmatter, body = parts
    header: dict = {}
    for line in frontmatter.splitlines():
        if not line.strip():
            continue
        key, sep, rest = line.partition(": ")
        if not sep:
            raise WikiFormatError(f"malformed frontmatter line: {line!r}")
        try:
            header[key] = json.loads(rest)
        except json.JSONDecodeError as exc:
            raise WikiFormatError(f"non-JSON frontmatter value for {key!r}: {rest!r}") from exc
    try:
        return WikiPage(**header), body
    except Exception as exc:  # pydantic ValidationError → uniform WikiFormatError
        raise WikiFormatError(f"invalid page header: {exc}") from exc
