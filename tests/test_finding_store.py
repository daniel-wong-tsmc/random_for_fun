import pytest
from gpu_agent.store import FindingStore, FindingNotFound
from gpu_agent.schema.finding import Finding, Kind, Impact, Confidence


def _finding(fid="f-2026-06-26-001", statement="CoWoS capacity tight"):
    return Finding(
        id=fid, statement=statement, kind=Kind.observed, trend="flat",
        why="capacity constraint",
        impact=Impact(targets=["nvidia"], direction="negative", mechanism="supply limit"),
        confidence=Confidence(level="medium", basis="single secondary source"),
        asOf="2026-06-26", indicatorId="cowosCapacity", side="supply",
        polarityDemand=0, polaritySupply=-1, magnitude=2, entity="tsmc",
        observedAt="2026-06-26", capturedAt="2026-06-26",
    )


def test_append_then_get_roundtrips(tmp_path):
    store = FindingStore(tmp_path)
    store.append(_finding())
    got = store.get("f-2026-06-26-001")
    assert got.statement == "CoWoS capacity tight"
    assert got.polaritySupply == -1


def test_exists(tmp_path):
    store = FindingStore(tmp_path)
    assert not store.exists("f-x")
    store.append(_finding(fid="f-x"))
    assert store.exists("f-x")


def test_get_missing_raises(tmp_path):
    store = FindingStore(tmp_path)
    with pytest.raises(FindingNotFound):
        store.get("nope")


def test_append_is_idempotent_for_identical(tmp_path):
    store = FindingStore(tmp_path)
    p1 = store.append(_finding())
    p2 = store.append(_finding())  # identical → no-op
    assert p1 == p2


def test_append_collision_with_different_content_raises(tmp_path):
    store = FindingStore(tmp_path)
    store.append(_finding(statement="A"))
    with pytest.raises(ValueError):
        store.append(_finding(statement="B"))  # same id, different content


def test_unsafe_id_rejected(tmp_path):
    store = FindingStore(tmp_path)
    with pytest.raises(ValueError):
        store.get("../etc/passwd")
