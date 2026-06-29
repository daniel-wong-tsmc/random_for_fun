import json
import pathlib
from gpu_agent.cli import main


def test_wiki_ingest_phase1_only_populates_entity_pages(tmp_path, capsys):
    rc = main(["wiki-ingest", "--findings", "fixtures/golden/findings.json",
               "--store", str(tmp_path), "--as-of", "2026-06"])
    assert rc == 0
    # golden findings are NVDA/AMD/INTC -> three entity pages with observations
    pages = sorted(p.stem for p in (tmp_path / "wiki" / "entity").glob("*.md"))
    assert pages == ["amd", "intc", "nvda"]


def test_wiki_ingest_emit_prompt_prints_bundle(tmp_path, capsys):
    rc = main(["wiki-ingest", "--findings", "fixtures/golden/findings.json",
               "--store", str(tmp_path), "--as-of", "2026-06", "--emit-prompt"])
    assert rc == 0
    bundle = json.loads(capsys.readouterr().out)
    assert "system" in bundle and "schema" in bundle
    assert {p["pageId"] for p in bundle["pages"]} == {"entity:nvda", "entity:amd", "entity:intc"}


def test_wiki_ingest_recorded_applies_enrichment(tmp_path):
    rc = main(["wiki-ingest", "--findings", "fixtures/golden/findings.json",
               "--store", str(tmp_path), "--as-of", "2026-06",
               "--recorded", "fixtures/recorded/ingest-merchant-gpu.json"])
    assert rc == 0
    page_md = (tmp_path / "wiki" / "entity" / "nvda.md").read_text(encoding="utf-8")
    assert "accelerating" in page_md
    assert "## NVIDIA" in page_md
