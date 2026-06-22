from __future__ import annotations
import statistics
from gpu_agent.schema.finding import Finding

def zscore(value: float, history: list[float]) -> float:
    if len(history) < 2:
        return 0.0
    sigma = statistics.pstdev(history)
    if sigma == 0:
        return 0.0
    return (value - statistics.mean(history)) / sigma

def dmi_smi_contribution(findings: list[Finding], weights: dict[str, float]) -> tuple[float, float]:
    dmi = sum(weights.get(f.indicatorId, 0.0) * f.polarityDemand * f.magnitude / 3 for f in findings)
    smi = sum(weights.get(f.indicatorId, 0.0) * f.polaritySupply * f.magnitude / 3 for f in findings)
    return dmi, smi
