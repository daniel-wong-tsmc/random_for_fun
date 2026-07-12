"""The ONE emit path for eval: rebuilds each seam's canonical prompt bundle from raw case
inputs using the SAME builders the live CLI uses (cli.py _emit_extract_prompt /
_emit_judge_prompt / _thesis --emit-prompt). Used by the harness (fresh brain prompts) and by
prompt_hash (the regression pin) so both always agree on what 'the prompt' is.
Eval deviations from live, both deliberate:
- judge memory comes from the case's frozen memoryText (no store dependency);
- judge emits for ONE sample (eval grades reasoning depth, not aggregation)."""
from __future__ import annotations
import json
import pathlib
from gpu_agent.evals.cases import ExtractInput, JudgeInput, ThesisInput, ImplicationInput
from gpu_agent.extraction.extractor import ExtractionResult
from gpu_agent.extraction.prompt import (
    build_system as build_extract_system, build_user_prompt as build_extract_user_prompt)
from gpu_agent.judgment.briefing import build_briefing
from gpu_agent.judgment.judge import JudgmentResult
from gpu_agent.judgment.prompt import (
    SYSTEM as JUDGE_SYSTEM, build_user_prompt as build_judge_user_prompt)
from gpu_agent.thesis import THESIS_SYSTEM, ThesisAnswer, build_thesis_user_prompt
from gpu_agent.implication import (
    IMPLICATION_SYSTEM, ImplicationAnswer, ImplicationRegistry, build_implication_user_prompt)
from gpu_agent.config import IMPLICATIONS_REGISTRY_PATH


def _extract_vocab(registry, taxonomy) -> dict:
    # Mirrors cli._emit_extract_prompt (F55/F53, completing F55 for ALL non-price indicator
    # ids — structural and unsided included): the id vocabularies the gate enforces.
    valid_targets = sorted(taxonomy.categories)
    scoring_indicators = [
        {"id": ind_id, "label": spec.label, "side": spec.side, "unit": spec.unit}
        for ind_id, spec in ((i, registry.resolve(i)) for i in sorted(registry.indicators))
        if spec.side != "price"
    ]
    price_indicators = [
        {"id": ind_id, "label": spec.label, "unit": spec.unit,
         "comparability": spec.comparability}
        for ind_id, spec in ((i, registry.resolve(i)) for i in sorted(registry.indicators))
        if spec.side == "price"
    ]
    return {"valid_targets": valid_targets, "scoring_indicators": scoring_indicators,
            "price_indicators": price_indicators}


def emit_brain_bundle(seam: str, seam_input, registry, taxonomy) -> dict:
    if seam == "extract":
        assert isinstance(seam_input, ExtractInput)
        return {
            "system": build_extract_system(**_extract_vocab(registry, taxonomy)),
            "schema": ExtractionResult.model_json_schema(),
            "user": build_extract_user_prompt(seam_input.doc),
        }
    if seam == "judge":
        assert isinstance(seam_input, JudgeInput)
        briefing = build_briefing(seam_input.findings, registry, seam_input.category)
        return {
            "system": JUDGE_SYSTEM,
            "schema": JudgmentResult.model_json_schema(),
            "user": build_judge_user_prompt(briefing, memory_text=seam_input.memoryText,
                                            include_groups=True, include_dates=True),
        }
    if seam == "thesis":
        assert isinstance(seam_input, ThesisInput)
        return {
            "system": THESIS_SYSTEM,
            "schema": ThesisAnswer.model_json_schema(),
            "user": build_thesis_user_prompt(seam_input.book, seam_input.findings,
                                             seam_input.memoryText),
        }
    if seam == "implication":
        assert isinstance(seam_input, ImplicationInput)
        # Registry-driven, exactly like the live CLI: variables come from the committed
        # implications registry by category, so a registry edit re-emits a different prompt.
        variables = ImplicationRegistry.load(IMPLICATIONS_REGISTRY_PATH).variables_for(
            seam_input.category)
        return {
            "system": IMPLICATION_SYSTEM,
            "schema": ImplicationAnswer.model_json_schema(),
            "user": build_implication_user_prompt(variables, seam_input.scorecard,
                                                  seam_input.book, seam_input.memoryText),
        }
    raise ValueError(f"unknown seam '{seam}'")


def load_hash_input(path: pathlib.Path) -> dict:
    raw = json.loads(pathlib.Path(path).read_text("utf-8"))
    return {
        "extract": ExtractInput.model_validate(raw["extract"]),
        "judge": JudgeInput.model_validate(raw["judge"]),
        "thesis": ThesisInput.model_validate(raw["thesis"]),
    }
