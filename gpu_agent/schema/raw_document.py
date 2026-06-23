from __future__ import annotations
from typing import Literal
from pydantic import BaseModel

class RawDocument(BaseModel):
    id: str
    source: str
    url: str
    date: str
    tier: Literal["primary", "secondary"]
    entity: str
    content: str
