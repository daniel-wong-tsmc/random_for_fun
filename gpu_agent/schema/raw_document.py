from __future__ import annotations
from typing import Literal, Optional
from pydantic import BaseModel

class RawDocument(BaseModel):
    id: str
    source: str
    url: str
    date: str
    tier: Literal["primary", "secondary"]
    entity: str
    content: str
    # F72 (contract v1.4): the gatherer's chase/corroboration result gets a structured home —
    # the ORIGINATING publisher behind a syndicated/aggregated blob — instead of free text in
    # `content` (closes F69's handoff note). Optional + additive: this is gather-blob metadata,
    # NOT the Finding schema, so Finding.schemaVersion stays 1.2 (spec §3, D3). Old blobs and
    # any code that never sets it read None; nothing in the frozen scoring path consumes it.
    originatingPublisher: Optional[str] = None
