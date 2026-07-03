"""F6 rubric as DATA. 4 criteria per seam, each 0/1/2 with ANCHORED descriptions (variance
control for the LLM grader). Derived from the Depth Rubric (docs/action-items.md Action Item 1)
+ the research report's five criteria. Case score = sum over 4 criteria, max 8."""
from __future__ import annotations
from pydantic import BaseModel, ConfigDict, Field

MAX_CRITERION = 2


class Criterion(BaseModel):
    model_config = ConfigDict(extra="forbid")
    key: str
    title: str
    anchors: dict[str, str]


def _c(key: str, title: str, a0: str, a1: str, a2: str) -> Criterion:
    return Criterion(key=key, title=title, anchors={"0": a0, "1": a1, "2": a2})


RUBRICS: dict[str, list[Criterion]] = {
    "extract": [
        _c("fidelity", "Values, units, periods and attributions match the source document",
           "Any number, unit, period or attribution contradicts the document.",
           "All values match but a period/entity attribution is imprecise or a unit is sloppy.",
           "Every value, unit, period and attribution is exactly what the document supports."),
        _c("completeness", "Material claims in the document are captured as findings",
           "A clearly material, indicator-relevant claim in the document has no finding.",
           "Coverage is adequate but a secondary-yet-material claim was skipped.",
           "Every indicator-relevant material claim is captured; nothing important left behind."),
        _c("provenance-honesty", "Nothing invented; polarity/side/trend justified by the document",
           "A finding asserts something the document does not say, or invents a source/number.",
           "All claims sourced but a polarity/trend stretches beyond what the excerpt supports.",
           "Every field is directly defensible from the quoted evidence."),
        _c("signal-selection", "Findings are material signal, not boilerplate",
           "Findings are dominated by boilerplate, marketing fluff, or weight-0 trivia.",
           "Mostly signal but at least one finding is filler that dilutes the set.",
           "Every finding would matter to a category judge; no filler."),
    ],
    "judge": [
        _c("crux", "Names the 1-2 questions that actually decide the call",
           "No crux: ten balanced considerations, no position on what decides the category.",
           "A crux is implied but buried or mixed with secondary considerations.",
           "The 1-2 deciding questions are named explicitly and the rating follows from them."),
        _c("mechanism", "Explicit causal chain; each link evidenced by cited findings",
           "Narrative assertions with no causal chain or citations that don't support the links.",
           "A causal chain exists but at least one link is asserted without a cited finding.",
           "Every link in the chain is explicit and carried by specific cited findings."),
        _c("sensitivity-differentiation", "States what flips the call and where it departs consensus",
           "Neither a flip condition nor any differentiation from the obvious consensus read.",
           "One of the two present (flip condition OR consensus departure), not both.",
           "States which assumption, if ~2x wrong, flips the rating AND where/why this read departs from consensus."),
        _c("evidence-discipline", "Rationale strictly grounded in the cited findings",
           "Rationale leans on facts outside the briefing or misuses cited findings.",
           "Grounded overall but one claim outruns its citation.",
           "Every rationale claim traces to a cited finding used correctly."),
    ],
    "thesis": [
        _c("trigger-quality", "Falsifiable trigger is observable, dated, and decisive",
           "Trigger is vague, unobservable, or would not actually falsify the thesis.",
           "Observable but fuzzy on timing or threshold; falsification is arguable.",
           "Names an observable with threshold and window; hitting it decisively falsifies/confirms."),
        _c("mechanism", "Explicit causal chain; each link separately evidenced",
           "Narrative without a chain, or links unsupported by the cited findings.",
           "Chain present; one link asserted without evidence.",
           "Every link explicit and evidenced."),
        _c("steelman", "Strongest counter-case stated and answered",
           "No counter-case, or a strawman.",
           "A real objection is stated but answered thinly.",
           "The strongest objection is stated fairly and answered with evidence."),
        _c("delta-discipline", "Conviction move matches evidence weight (anti-whipsaw spirit)",
           "Verdict/conviction move is disproportionate to the cycle's evidence.",
           "Direction right but the size of the move is under-argued.",
           "The move (or hold) is exactly what the cited evidence supports, no more."),
    ],
}


def max_score(seam: str) -> int:
    return MAX_CRITERION * len(RUBRICS[seam])


class CriterionGrade(BaseModel):
    model_config = ConfigDict(extra="forbid")
    score: int = Field(ge=0, le=MAX_CRITERION)
    evidence: str


class GradeResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    caseId: str
    grades: dict[str, CriterionGrade]


def gate_grade(grade: GradeResult, seam: str) -> list[str]:
    violations: list[str] = []
    expected = [c.key for c in RUBRICS[seam]]
    for key in expected:
        if key not in grade.grades:
            violations.append(f"missing criterion '{key}'")
    for key in grade.grades:
        if key not in expected:
            violations.append(f"unknown criterion '{key}'")
    for key, cg in grade.grades.items():
        if key in expected and not cg.evidence.strip():
            violations.append(f"criterion '{key}': evidence must be a non-empty quote/paraphrase")
    return violations


def case_score(grade: GradeResult) -> int:
    return sum(cg.score for cg in grade.grades.values())


def render_rubric(seam: str) -> str:
    lines = [f"RUBRIC ({seam}) — score each criterion 0, 1, or 2:"]
    for c in RUBRICS[seam]:
        lines.append(f"- {c.key}: {c.title}")
        for level in ("0", "1", "2"):
            lines.append(f"    {level}: {c.anchors[level]}")
    return "\n".join(lines)
