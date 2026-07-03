"""F6 eval harness: the golden-set case model. A case stores RAW seam inputs (not a frozen
prompt string) so a prompt change re-emits a different prompt for the same case — the whole
point of the regression gate. recordedAnswer is the frozen brain answer as captured:
extract = one ExtractionResult JSON string for the single doc; judge = ONE serialized
JudgmentResult string (single sample — eval grades reasoning depth, not aggregation);
thesis = one ThesisAnswer JSON string."""
from __future__ import annotations
import json
import pathlib
from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from gpu_agent.schema.finding import Finding
from gpu_agent.schema.raw_document import RawDocument
from gpu_agent.thesis import ThesisBook


class CaseError(Exception):
    pass


class ExtractInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    doc: RawDocument
    asOf: str


class JudgeInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    findings: list[Finding]
    category: str
    memoryText: Optional[str] = None


class ThesisInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    book: ThesisBook
    findings: list[Finding]
    memoryText: Optional[str] = None


_SEAM_INPUT = {"extract": ExtractInput, "judge": JudgeInput, "thesis": ThesisInput}


class CaseChecks(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mustMention: list[str] = Field(default_factory=list)
    citationsResolve: bool = True
    gateOutcome: Literal["pass", "reject"] = "pass"


class EvalCase(BaseModel):
    model_config = ConfigDict(extra="forbid")
    caseId: str
    seam: Literal["extract", "judge", "thesis"]
    kind: Literal["positive", "negative"]
    source: str
    input: dict
    recordedAnswer: str
    checks: CaseChecks = CaseChecks()
    notes: str

    def seam_input(self):
        try:
            return _SEAM_INPUT[self.seam].model_validate(self.input)
        except ValidationError as e:
            raise CaseError(f"case {self.caseId}: input does not match seam '{self.seam}': {e}") from e


def load_cases(cases_dir: pathlib.Path) -> list[EvalCase]:
    cases: list[EvalCase] = []
    for path in sorted(pathlib.Path(cases_dir).glob("*.json")):
        try:
            cases.append(EvalCase.model_validate(json.loads(path.read_text("utf-8"))))
        except (ValidationError, json.JSONDecodeError) as e:
            raise CaseError(f"{path.name}: {e}") from e
    cases.sort(key=lambda c: c.caseId)
    seen: set[str] = set()
    for c in cases:
        if c.caseId in seen:
            raise CaseError(f"duplicate caseId '{c.caseId}'")
        seen.add(c.caseId)
    return cases
