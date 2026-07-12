from gpu_agent.wiki import bench
from gpu_agent.wiki.store import WikiStore
from gpu_agent.store import FindingStore
from gpu_agent.wiki.lint import health_report, DEFAULT_LINT_CONFIG
from gpu_agent.registry.horizon import IndicatorHorizons

_HZ = IndicatorHorizons.load("registry/indicators.json")


def test_warm_index_and_health_do_not_reparse_log(tmp_path):
    bench.build_synthetic(tmp_path / "wiki", tmp_path / "findings", pages=40, obs_per_page=4)
    store = WikiStore(tmp_path / "wiki", FindingStore(tmp_path / "findings"))  # cold instance
    total = store.log.count()               # one warm-up pass
    base = store.log.parsed_lines
    assert base == total                    # exactly one pass to warm the cache
    store.index()
    store.index()
    health_report(store, as_of="2026-06-01", contradictions={}, horizons=_HZ,
                  config=DEFAULT_LINT_CONFIG)
    assert store.log.parsed_lines == base   # ZERO additional parses -> no full-log re-read per op


def test_cold_health_parses_log_at_most_once(tmp_path):
    bench.build_synthetic(tmp_path / "wiki", tmp_path / "findings", pages=40, obs_per_page=4)
    store = WikiStore(tmp_path / "wiki", FindingStore(tmp_path / "findings"))  # cold
    assert store.log.parsed_lines == 0
    health_report(store, as_of="2026-06-01", contradictions={}, horizons=_HZ,
                  config=DEFAULT_LINT_CONFIG)
    # a single full pass, NOT O(pages) passes: parsed lines <= total event count
    assert store.log.parsed_lines <= store.log.count()
