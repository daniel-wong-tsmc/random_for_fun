from gpu_agent.schema.raw_document import RawDocument
from gpu_agent.gathering.dedup import content_hash, SeenDocIndex, filter_seen_documents


def _doc(did, url, content="body text here", entity="NVDA"):
    return RawDocument(id=did, source="src", url=url, date="2026-07", tier="secondary",
                       entity=entity, content=content)


def test_content_hash_folds_whitespace():
    assert content_hash("a  b\n c") == content_hash("a b c")
    assert content_hash("a b c") != content_hash("a b d")


def test_index_persists_and_reloads(tmp_path):
    p = tmp_path / "seen_docs.jsonl"
    idx = SeenDocIndex(p)
    assert idx.contains("http://x/a", "h1") is None
    idx.record("http://x/a", "h1", "2026-06")
    # a fresh instance reads the persisted file
    idx2 = SeenDocIndex(p)
    hit = idx2.contains("http://x/a", "hZZ")
    assert hit == ("seen-url", "2026-06")
    hit2 = idx2.contains("http://other/z", "h1")
    assert hit2 == ("seen-content-hash", "2026-06")


def test_filter_drops_known_url(tmp_path):
    idx = SeenDocIndex(tmp_path / "seen_docs.jsonl")
    idx.record("http://x/a", "hA", "2026-06")
    survivors, dropped = filter_seen_documents(
        [_doc("d1", "http://x/a"), _doc("d2", "http://x/b", content="fresh new content")],
        idx, as_of="2026-07")
    assert [d.id for d in survivors] == ["d2"]
    assert [(dd.url, dd.reason) for dd in dropped] == [("http://x/a", "seen-url")]


def test_filter_catches_same_content_new_url(tmp_path):
    idx = SeenDocIndex(tmp_path / "seen_docs.jsonl")
    survivors, dropped = filter_seen_documents(
        [_doc("d1", "http://x/a", content="identical body"),
         _doc("d2", "http://y/b", content="identical  body")],  # same content, new url
        idx, as_of="2026-07")
    assert [d.id for d in survivors] == ["d1"]
    assert dropped[0].reason == "seen-content-hash"


def test_filter_records_survivors_for_next_run(tmp_path):
    idx = SeenDocIndex(tmp_path / "seen_docs.jsonl")
    filter_seen_documents([_doc("d1", "http://x/a")], idx, as_of="2026-07")
    survivors, dropped = filter_seen_documents([_doc("d1", "http://x/a")], idx, as_of="2026-08")
    assert survivors == [] and dropped[0].reason == "seen-url"
    assert dropped[0].firstSeenAsOf == "2026-07"  # first-seen, not the re-run cycle


def test_filter_dedups_within_batch(tmp_path):
    idx = SeenDocIndex(tmp_path / "seen_docs.jsonl")
    survivors, dropped = filter_seen_documents(
        [_doc("d1", "http://x/a"), _doc("d2", "http://x/a")],  # same url twice in one batch
        idx, as_of="2026-07")
    assert [d.id for d in survivors] == ["d1"]
    assert dropped[0].reason == "seen-url"
