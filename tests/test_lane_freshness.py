"""F59 — vendor official posts count as primary (manifest-driven allowlist).

Charter primary = "filings, official posts", but ingest previously stamped primary only for
the hardcoded pair sec.gov / investor.nvidia.com, so a vendor's OWN official newsroom/IR posts
(nvidianews.nvidia.com, blogs.nvidia.com, ir.amd.com, intc.com) landed secondary and got
confidence-capped. This test drives the ingest CLI with --primary-sources built from the
manifest's top-level primaryDomains allowlist and asserts an nvidianews.nvidia.com blob is
stamped tier == "primary".
"""
import json
import pathlib
import subprocess
import sys
from gpu_agent.cli import main
from gpu_agent.schema.raw_document import RawDocument

PY = sys.executable

MANIFEST_PATH = pathlib.Path("manifests/chips.merchant-gpu.json")

EXPECTED_PRIMARY_DOMAINS = (
    "sec.gov", "investor.nvidia.com", "nvidianews.nvidia.com", "blogs.nvidia.com",
    "ir.amd.com", "intc.com", "bis.doc.gov", "federalregister.gov",
)


def _blob(url, entity="nvidia", source="NVIDIA newsroom",
          content="NVIDIA announces a vendor-financing arrangement with a cloud customer."):
    return {"url": url, "entity": entity, "source": source, "date": "2026-07-01", "content": content}


def test_vendor_official_post_counts_as_primary_via_manifest_allowlist(tmp_path):
    # Read the manifest's raw JSON directly (NOT via load_manifest/CoverageManifest — that
    # model is extra="ignore" and does not surface this new top-level field; F59 wires the
    # gather skill to read primaryDomains straight off the manifest JSON).
    manifest = json.loads(MANIFEST_PATH.read_text("utf-8"))
    primary_domains = manifest.get("primaryDomains", [])

    blobs = tmp_path / "blobs.json"
    blobs.write_text(json.dumps([
        _blob("https://nvidianews.nvidia.com/news/nvidia-vendor-financing-update"),
    ]), "utf-8")
    out = tmp_path / "docs"
    rc = main(["ingest", "--blobs", str(blobs), "--out", str(out),
               "--primary-sources", ",".join(primary_domains), "--as-of", "2026-07-01"])
    assert rc == 0

    doc_files = [p for p in out.glob("*.json") if p.name != "gather-log.json"]
    assert len(doc_files) == 1
    doc = RawDocument.model_validate(json.loads(doc_files[0].read_text("utf-8")))
    assert doc.tier == "primary", (
        "vendor official newsroom post (nvidianews.nvidia.com) must be stamped primary via the "
        "manifest's primaryDomains allowlist (F59, charter: filings + official posts)"
    )

    log = json.loads((out / "gather-log.json").read_text("utf-8"))
    assert log["primary"] == 1 and log["secondary"] == 0

    # the manifest allowlist itself must cover the official filing + IR/newsroom domains
    for domain in EXPECTED_PRIMARY_DOMAINS:
        assert domain in primary_domains, f"{domain} missing from manifest primaryDomains (F59)"


# --- F56-core: --as-of shape validated at the CLI seam --------------------
#
# F52 embeds --as-of verbatim in snapshot/FindingStore doc ids, so a fat-fingered
# "2026/07/03" (slashes instead of dashes) would mint a path-unsafe id downstream.
# Defense-in-depth: reject non-ISO shapes once, at the argparse seam, for every
# REQUIRED --as-of argument. Driven via subprocess (real CLI entry point) so we
# see the actual argparse exit code + stderr, not an in-process SystemExit.

def _run_cli(*args):
    return subprocess.run([PY, "-m", "gpu_agent.cli", *args], capture_output=True, text=True)


def test_as_of_rejects_non_iso_shape(tmp_path):
    blobs = tmp_path / "blobs.json"
    blobs.write_text("[]", encoding="utf-8")
    out = tmp_path / "docs"
    proc = _run_cli("ingest", "--blobs", str(blobs), "--out", str(out),
                     "--primary-sources", "sec.gov", "--as-of", "2026/07/03")
    assert proc.returncode == 2, (
        f"expected argparse to reject '2026/07/03' (slashes) as an --as-of shape; "
        f"stdout={proc.stdout!r} stderr={proc.stderr!r}"
    )
    assert "--as-of" in proc.stderr


def test_as_of_accepts_year_month(tmp_path):
    blobs = tmp_path / "blobs.json"
    blobs.write_text("[]", encoding="utf-8")
    out = tmp_path / "docs"
    proc = _run_cli("ingest", "--blobs", str(blobs), "--out", str(out),
                     "--primary-sources", "sec.gov", "--as-of", "2026-07")
    assert proc.returncode == 0, f"stdout={proc.stdout!r} stderr={proc.stderr!r}"


def test_as_of_accepts_year_month_day(tmp_path):
    blobs = tmp_path / "blobs.json"
    blobs.write_text("[]", encoding="utf-8")
    out = tmp_path / "docs"
    proc = _run_cli("ingest", "--blobs", str(blobs), "--out", str(out),
                     "--primary-sources", "sec.gov", "--as-of", "2026-07-03")
    assert proc.returncode == 0, f"stdout={proc.stdout!r} stderr={proc.stderr!r}"
