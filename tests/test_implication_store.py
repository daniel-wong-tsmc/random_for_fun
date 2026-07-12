"""F65 Task 4 (acceptance 4, storage): the implication carve-out round-trips and the
gitignore whitelist keeps store/implications/ tracked."""
from __future__ import annotations
from pathlib import Path
import pytest
from gpu_agent.implication import (
    ImplicationStore, ImplicationArtifact, ImplicationLine, ImplicationError)


def test_write_then_load_roundtrips(tmp_path):
    root = tmp_path / "store" / "implications" / "chips.merchant-gpu"
    store = ImplicationStore(root)
    assert not store.exists()
    art = ImplicationArtifact(categoryId="chips.merchant-gpu", asOf="2026-07-08",
                              lines=[ImplicationLine(watchItem="w", dimensions=["moat"])])
    p = store.write(art)
    assert p == root / "2026-07-08.json"
    assert store.exists()
    loaded = store.load("2026-07-08")
    assert loaded.model_dump() == art.model_dump()


def test_load_missing_raises(tmp_path):
    store = ImplicationStore(tmp_path / "implications" / "c")
    with pytest.raises(ImplicationError):
        store.load("2026-07-08")


def test_gitignore_whitelists_implications():
    assert "!store/implications/" in Path(".gitignore").read_text("utf-8")
