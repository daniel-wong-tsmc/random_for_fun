from __future__ import annotations
from gpu_agent.schema.finding import Finding, Kind

def check_finding(f: Finding) -> list[str]:
    errors: list[str] = []
    if f.kind == Kind.measured:
        if f.value is None:
            errors.append(f"{f.id}: measured finding missing value")
        if not f.evidence:
            errors.append(f"{f.id}: measured finding missing evidence")
    else:
        if f.value is not None:
            errors.append(f"{f.id}: non-measured finding has invented value")
    if not f.why.strip():
        errors.append(f"{f.id}: missing why")
    if f.kind == Kind.hypothesis:
        if not f.reasoning:
            errors.append(f"{f.id}: hypothesis missing reasoning")
        if f.confidence.level == "high":
            errors.append(f"{f.id}: hypothesis confidence capped at medium")
    if f.polarityDemand == 0 and f.polaritySupply == 0:
        errors.append(f"{f.id}: finding affects neither demand nor supply track")
    return errors
