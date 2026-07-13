import json
import pathlib

import pytest

from gpu_agent.cli import main
from gpu_agent.gathering.assemble import GatherBlob, assemble


def _write_blob(blob_dir: pathlib.Path, name: str, **fields) -> pathlib.Path:
    p = blob_dir / name
    p.write_text(json.dumps(fields), encoding="utf-8")
    return p


def _blob_fields(url="https://example.com/a", entity="nvidia", source="Example Wire",
                  date="2026-07", content="DC revenue grew 8% QoQ."):
    return {"url": url, "entity": entity, "source": source, "date": date, "content": content}


# --- (a) valid dir -> envelope with correct blobs, rounds from rounds.txt, empty skipped ---

def test_valid_dir_assembles_envelope_with_rounds_and_blobs(tmp_path):
    blob_dir = tmp_path / "blobs"
    blob_dir.mkdir()
    _write_blob(blob_dir, "1-a.json", **_blob_fields(url="https://example.com/a"))
    _write_blob(blob_dir, "2-b.json", **_blob_fields(url="https://example.com/b", entity="amd"))
    _write_blob(blob_dir, "3-c.json", **_blob_fields(url="https://example.com/c", entity="intel"))
    (blob_dir / "rounds.txt").write_text("2", encoding="utf-8")

    envelope = assemble(blob_dir)

    assert envelope["rounds"] == 2
    assert envelope["skipped"] == []
    assert len(envelope["blobs"]) == 3
    urls = [b["url"] for b in envelope["blobs"]]
    assert urls == sorted(urls)  # ordered by normalized url
    assert {b["entity"] for b in envelope["blobs"]} == {"nvidia", "amd", "intel"}
    # optional keys that were never set must not appear (model_dump(exclude_none=True))
    for b in envelope["blobs"]:
        assert "chase" not in b
        assert "originatingPublisher" not in b


def test_rounds_defaults_to_1_when_rounds_txt_absent(tmp_path):
    blob_dir = tmp_path / "blobs"
    blob_dir.mkdir()
    _write_blob(blob_dir, "1-a.json", **_blob_fields())
    envelope = assemble(blob_dir)
    assert envelope["rounds"] == 1


def test_optional_fields_pass_through_when_present(tmp_path):
    blob_dir = tmp_path / "blobs"
    blob_dir.mkdir()
    chase = {"attempted": True, "primaryFound": "https://sec.gov/x", "corroborators": []}
    _write_blob(blob_dir, "1-a.json", chase=chase, originatingPublisher="Business Wire",
                **_blob_fields())
    envelope = assemble(blob_dir)
    assert len(envelope["blobs"]) == 1
    assert envelope["blobs"][0]["chase"] == chase
    assert envelope["blobs"][0]["originatingPublisher"] == "Business Wire"


def test_empty_dir_is_empty_envelope(tmp_path):
    blob_dir = tmp_path / "blobs"
    blob_dir.mkdir()
    envelope = assemble(blob_dir)
    assert envelope == {"rounds": 1, "skipped": [], "blobs": []}


# --- live round-trip: envelope assembles straight into `ingest --blobs` ---

def test_envelope_round_trips_through_ingest_cli(tmp_path):
    blob_dir = tmp_path / "blobs"
    blob_dir.mkdir()
    _write_blob(blob_dir, "1-a.json", **_blob_fields(url="https://example.com/a"))
    _write_blob(blob_dir, "2-b.json", **_blob_fields(url="https://example.com/b", entity="amd"))

    envelope = assemble(blob_dir)
    envelope_path = tmp_path / "blobs.json"
    envelope_path.write_text(json.dumps(envelope, indent=2), encoding="utf-8")

    out_dir = tmp_path / "docs"
    rc = main(["ingest", "--blobs", str(envelope_path), "--out", str(out_dir), "--as-of", "2026-07"])
    assert rc == 0
    doc_files = [p for p in out_dir.glob("*.json") if p.name != "gather-log.json"]
    assert len(doc_files) == 2


# --- (b) malformed JSON / schema-invalid files become skipped rows, not fatal ---

def test_malformed_json_file_is_skipped_with_reason(tmp_path):
    blob_dir = tmp_path / "blobs"
    blob_dir.mkdir()
    (blob_dir / "1-bad.json").write_text("{not valid json", encoding="utf-8")
    _write_blob(blob_dir, "2-good.json", **_blob_fields())

    envelope = assemble(blob_dir)

    assert len(envelope["blobs"]) == 1
    assert len(envelope["skipped"]) == 1
    assert envelope["skipped"][0]["path"] == "1-bad.json"
    assert envelope["skipped"][0]["reason"]  # non-empty, short reason


def test_schema_invalid_missing_entity_is_skipped_with_reason(tmp_path):
    blob_dir = tmp_path / "blobs"
    blob_dir.mkdir()
    bad = _blob_fields()
    del bad["entity"]
    _write_blob(blob_dir, "1-bad.json", **bad)
    _write_blob(blob_dir, "2-good.json", **_blob_fields())

    envelope = assemble(blob_dir)

    assert len(envelope["blobs"]) == 1
    assert len(envelope["skipped"]) == 1
    assert envelope["skipped"][0]["path"] == "1-bad.json"
    assert "entity" in envelope["skipped"][0]["reason"]


def test_malformed_and_schema_invalid_together_do_not_abort_assembly(tmp_path):
    blob_dir = tmp_path / "blobs"
    blob_dir.mkdir()
    (blob_dir / "1-malformed.json").write_text("not json at all {{{", encoding="utf-8")
    bad = _blob_fields()
    del bad["entity"]
    _write_blob(blob_dir, "2-invalid.json", **bad)
    _write_blob(blob_dir, "3-good.json", **_blob_fields())

    envelope = assemble(blob_dir)

    assert len(envelope["blobs"]) == 1
    assert len(envelope["skipped"]) == 2
    paths = {row["path"] for row in envelope["skipped"]}
    assert paths == {"1-malformed.json", "2-invalid.json"}
    for row in envelope["skipped"]:
        assert row["reason"]


# --- (c) duplicate normalized URL across two files -> later-sorted file skipped ---

def test_duplicate_normalized_url_skips_the_later_sorted_file(tmp_path):
    blob_dir = tmp_path / "blobs"
    blob_dir.mkdir()
    # same page: differing only by case + trailing slash -> same normalized url
    _write_blob(blob_dir, "1-first.json", **_blob_fields(url="https://Example.com/Path/"))
    _write_blob(blob_dir, "2-second.json", **_blob_fields(url="https://example.com/Path"))

    envelope = assemble(blob_dir)

    assert len(envelope["blobs"]) == 1
    assert envelope["blobs"][0]["url"] == "https://Example.com/Path/"  # the kept (earlier) file
    assert len(envelope["skipped"]) == 1
    assert envelope["skipped"][0]["path"] == "2-second.json"
    assert envelope["skipped"][0]["reason"] == "duplicate-url"


# --- (d) determinism: same dir assembled twice -> byte-identical serialized output ---

def test_assembling_the_same_dir_twice_is_byte_identical(tmp_path):
    blob_dir = tmp_path / "blobs"
    blob_dir.mkdir()
    _write_blob(blob_dir, "2-b.json", **_blob_fields(url="https://example.com/b", entity="amd"))
    _write_blob(blob_dir, "1-a.json", **_blob_fields(url="https://example.com/a"))
    (blob_dir / "rounds.txt").write_text("3", encoding="utf-8")

    first = json.dumps(assemble(blob_dir), indent=2)
    second = json.dumps(assemble(blob_dir), indent=2)

    assert first == second


# --- GatherBlob model itself ---

def test_gatherblob_requires_the_five_core_fields():
    with pytest.raises(Exception):
        GatherBlob.model_validate({"url": "https://x.example/a"})


def test_gatherblob_optional_fields_default_none():
    blob = GatherBlob.model_validate(_blob_fields())
    assert blob.chase is None
    assert blob.originatingPublisher is None


# --- (e) CLI: exit 2 on missing --blob-dir; exit 0 with all-skipped envelope otherwise ---

def test_cli_exit_2_on_missing_blob_dir(tmp_path):
    missing = tmp_path / "does-not-exist"
    out = tmp_path / "blobs.json"
    rc = main(["gather-assemble", "--blob-dir", str(missing), "--out", str(out)])
    assert rc == 2
    assert not out.exists()


def test_cli_exit_2_when_blob_dir_is_a_file_not_a_directory(tmp_path):
    not_a_dir = tmp_path / "not-a-dir.txt"
    not_a_dir.write_text("x", encoding="utf-8")
    out = tmp_path / "blobs.json"
    rc = main(["gather-assemble", "--blob-dir", str(not_a_dir), "--out", str(out)])
    assert rc == 2


def test_cli_exit_0_with_all_skipped_envelope_on_dir_of_only_bad_files(tmp_path):
    blob_dir = tmp_path / "blobs"
    blob_dir.mkdir()
    (blob_dir / "1-malformed.json").write_text("{{{not json", encoding="utf-8")
    bad = _blob_fields()
    del bad["entity"]
    _write_blob(blob_dir, "2-invalid.json", **bad)
    out = tmp_path / "blobs.json"

    rc = main(["gather-assemble", "--blob-dir", str(blob_dir), "--out", str(out)])

    assert rc == 0
    assert out.exists()
    envelope = json.loads(out.read_text(encoding="utf-8"))
    assert envelope["blobs"] == []
    assert len(envelope["skipped"]) == 2


def test_cli_writes_valid_envelope_with_lf_newlines(tmp_path):
    blob_dir = tmp_path / "blobs"
    blob_dir.mkdir()
    _write_blob(blob_dir, "1-a.json", **_blob_fields())
    out = tmp_path / "blobs.json"

    rc = main(["gather-assemble", "--blob-dir", str(blob_dir), "--out", str(out)])

    assert rc == 0
    raw = out.read_bytes()
    assert b"\r\n" not in raw
    envelope = json.loads(raw.decode("utf-8"))
    assert len(envelope["blobs"]) == 1
    assert envelope["rounds"] == 1
