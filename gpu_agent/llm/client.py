from __future__ import annotations
import json
from typing import Callable, Protocol
from pydantic import BaseModel, ValidationError

class LLMError(Exception):
    pass

def parse_and_validate(text: str, schema: type[BaseModel]) -> BaseModel:
    data = json.loads(text)
    return schema.model_validate(data)

def complete_with_retry(
    raw_complete: Callable[[str, str, str], str],
    prompt: str, system: str, schema: type[BaseModel], model: str, retries: int = 2,
) -> BaseModel:
    last_error: Exception | None = None
    current = prompt
    for _ in range(retries + 1):
        text = raw_complete(current, system, model)
        try:
            return parse_and_validate(text, schema)
        except (json.JSONDecodeError, ValidationError) as e:
            last_error = e
            current = (f"{prompt}\n\nYour previous response was invalid: {e}\n"
                       "Return ONLY valid JSON matching the schema, no prose.")
    raise LLMError(f"no valid output after {retries + 1} attempts: {last_error}")

class LLMClient(Protocol):
    def complete_json(self, prompt: str, system: str,
                      schema: type[BaseModel], model: str) -> BaseModel: ...
