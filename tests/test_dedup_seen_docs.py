from gpu_agent.schema.raw_document import RawDocument
from gpu_agent.gathering.dedup import (
    content_hash, SeenDocIndex, filter_seen_documents, record_documents)


def _doc(did, url, content="body text here", entity="NVDA"):
    return RawDocument(id=did, source="src", url=url, date="2026-07", tier="secondary",
                       entity=entity, content=content)


def test_content_hash_folds_whitespace():
    assert content_hash("a  b\n c") == content_hash("a b c")
    assert content_hash("a b c") != content_hash("a b d")


# ── SeenDocIndex.contains — content-hash-first (F12) ───────────────────────────

def test_index_persists_and_reloads(tmp_path):
    p = tmp_path / "seen_docs.jsonl"
    idx = SeenDocIndex(p)
    assert idx.contains("http://x/a", "h1") is None
    idx.record("http://x/a", "h1", "2026-06")
    # a fresh instance reads the persisted file
    idx2 = SeenDocIndex(p)
    # same URL, DIFFERENT content hash: content is what's known, not the URL —
    # a stable URL whose content changed is a NEW document (F12: price pages survive).
    assert idx2.contains("http://x/a", "hZZ") is None
    # same content hash, new URL: known via content, reason "seen-content-hash"
    hit2 = idx2.contains("http://other/z", "h1")
    assert hit2 == ("seen-content-hash", "2026-06")


def test_index_contains_same_url_and_hash_reports_seen_url(tmp_path):
    idx = SeenDocIndex(tmp_path / "seen_docs.jsonl")
    idx.record("http://x/a", "h1", "2026-06")
    # both the URL and the content hash match the recorded doc -> "seen-url"
    assert idx.contains("http://x/a", "h1") == ("seen-url", "2026-06")


def test_index_contains_same_url_changed_content_is_none(tmp_path):
    """F12 case 1: record(url, hash1); contains(url, hash2) is None — the price page lives."""
    idx = SeenDocIndex(tmp_path / "seen_docs.jsonl")
    idx.record("http://x/price", "hash1", "2026-06")
    assert idx.contains("http://x/price", "hash2") is None


def test_index_contains_same_content_new_url_is_seen_content_hash(tmp_path):
    """F12 case 2: same content, new URL -> known via content hash."""
    idx = SeenDocIndex(tmp_path / "seen_docs.jsonl")
    idx.record("http://x/a", "hash1", "2026-06")
    assert idx.contains("http://y/b", "hash1") == ("seen-content-hash", "2026-06")


# ── filter_seen_documents — pure read, no recording (F12) ─────────────────────

def test_filter_drops_doc_with_known_url_and_content(tmp_path):
    idx = SeenDocIndex(tmp_path / "seen_docs.jsonl")
    known = _doc("d0", "http://x/a", content="known content")
    record_documents([known], idx, as_of="2026-06")
    survivors, dropped = filter_seen_documents(
        [_doc("d1", "http://x/a", content="known content"),
         _doc("d2", "http://x/b", content="fresh new content")],
        idx, as_of="2026-07")
    assert [d.id for d in survivors] == ["d2"]
    assert [(dd.url, dd.reason) for dd in dropped] == [("http://x/a", "seen-url")]


def test_filter_same_url_changed_content_survives(tmp_path):
    """F12: a stable URL (e.g. a price page) whose content changed is NOT dropped."""
    idx = SeenDocIndex(tmp_path / "seen_docs.jsonl")
    old = _doc("d0", "http://x/price", content="price: $10")
    record_documents([old], idx, as_of="2026-06")
    fresh = _doc("d1", "http://x/price", content="price: $12")  # same URL, new content
    survivors, dropped = filter_seen_documents([fresh], idx, as_of="2026-07")
    assert [d.id for d in survivors] == ["d1"]
    assert dropped == []


def test_filter_catches_same_content_new_url(tmp_path):
    idx = SeenDocIndex(tmp_path / "seen_docs.jsonl")
    survivors, dropped = filter_seen_documents(
        [_doc("d1", "http://x/a", content="identical body"),
         _doc("d2", "http://y/b", content="identical  body")],  # same content, new url
        idx, as_of="2026-07")
    assert [d.id for d in survivors] == ["d1"]
    assert dropped[0].reason == "seen-content-hash"


def test_filter_does_not_write_to_index(tmp_path):
    """F12: filter_seen_documents is a PURE read — recording is the caller's job,
    done only after the filtered docs' snapshots are durably written."""
    p = tmp_path / "seen_docs.jsonl"
    idx = SeenDocIndex(p)
    filter_seen_documents([_doc("d1", "http://x/a")], idx, as_of="2026-07")
    assert not p.exists()


def test_filter_dedups_within_batch_by_content(tmp_path):
    idx = SeenDocIndex(tmp_path / "seen_docs.jsonl")
    survivors, dropped = filter_seen_documents(
        [_doc("d1", "http://x/a"), _doc("d2", "http://x/a")],  # same url+content twice in one batch
        idx, as_of="2026-07")
    assert [d.id for d in survivors] == ["d1"]
    assert dropped[0].reason == "seen-content-hash"


# ── record_documents — recording is a separate, explicit step (F12) ───────────

def test_record_documents_writes_and_next_filter_drops(tmp_path):
    idx = SeenDocIndex(tmp_path / "seen_docs.jsonl")
    docs = [_doc("d1", "http://x/a")]
    survivors, dropped = filter_seen_documents(docs, idx, as_of="2026-07")
    assert survivors == docs and dropped == []
    record_documents(survivors, idx, as_of="2026-07")

    # a fresh index instance (simulating the next run) sees the recorded doc
    idx2 = SeenDocIndex(idx.path)
    survivors2, dropped2 = filter_seen_documents([_doc("d1", "http://x/a")], idx2, as_of="2026-08")
    assert survivors2 == [] and dropped2[0].reason == "seen-url"
    assert dropped2[0].firstSeenAsOf == "2026-07"  # first-seen, not the re-run cycle
