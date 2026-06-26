from __future__ import annotations
from gpu_agent.registry.indicators import IndicatorRegistry, RegistryError

def validate_assignment(assignment, registry: IndicatorRegistry, taxonomy) -> list[str]:
    violations: list[str] = []
    if assignment.category not in taxonomy.categories:
        violations.append(f"assignment category '{assignment.category}' not in taxonomy")
    for metric in assignment.metrics:
        try:
            spec = registry.resolve(metric, assignment.category)
        except RegistryError as e:
            violations.extend(e.violations)
            continue
        if spec.scoring and spec.dimension not in taxonomy.dimensions:
            violations.append(f"{metric}: dimension '{spec.dimension}' not in taxonomy")
    return violations
