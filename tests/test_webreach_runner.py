import json
import subprocess
import sys
import pathlib
import pytest

from gpu_agent.gathering.webreach import run_requests, MAX_RESULT_BYTES
from gpu_agent import cli


def _fake_registry():
    """In-process fake tools: no network, no real installed CLI. `read` prints a
    marker line to stdout so we can assert on saved bytes; `fail` exits nonzero
    with a stderr message; `healthCmd` prints a fake version string."""
    version_cmd = (f'"{sys.executable}" -c "import sys; '
                   f'sys.stdout.write(\'v9.9.9 fake-tool\\n\')"')
    return {"tools": [{
        "id": "fake-fetch",
        "enabled": True,
        "role": "fetch",
        "healthCmd": {"windows": version_cmd, "macos": version_cmd, "linux": version_cmd},
        "fetchVerbs": {
            "read": {
                "argv": [sys.executable, "-c",
                         "import sys; print('FETCHED ' + sys.argv[1])", "{target}"],
                "kind": "url",
            },
            "fail": {
                "argv": [sys.executable, "-c",
                         "import sys; sys.stderr.write('boom: bad thing happened\\n'); "
                         "sys.exit(3)", "{target}"],
                "kind": "url",
            },
        },
    }]}


LICENSED = {"trendforce.com", "semianalysis.com"}


def _write_requests(tmp_path, reqs):
    p = tmp_path / "requests.json"
    p.write_text(json.dumps(reqs), encoding="utf-8")
    return p


def test_happy_path_writes_result_file_and_manifest_row(tmp_path):
    reqs = [{"toolId": "fake-fetch", "verb": "read", "target": "https://example.com/a"}]
    req_path = _write_requests(tmp_path, reqs)
    out_dir = tmp_path / "out"

    manifest = run_requests(req_path, out_dir, _fake_registry(), LICENSED)

    assert len(manifest["results"]) == 1
    row = manifest["results"][0]
    assert row["toolId"] == "fake-fetch"
    assert row["verb"] == "read"
    assert row["target"] == "https://example.com/a"
    assert row["refused"] is None
    assert row["error"] is None
    assert row["exitCode"] == 0
    assert row["licensedSource"] is None  # clean host, executed, not a licensed source
    expected_stdout = "FETCHED https://example.com/a\n"
    assert row["bytes"] == len(expected_stdout)
    assert row["path"] is not None
    result_path = pathlib.Path(row["path"])
    assert result_path.exists()
    assert result_path.read_text(encoding="utf-8") == expected_stdout
    # result file must live inside out_dir
    assert result_path.resolve().parent == out_dir.resolve()

    # manifest written to disk too
    manifest_path = out_dir / "fetch-manifest.json"
    assert manifest_path.exists()
    on_disk = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert on_disk == manifest

    # tool version captured once for the one distinct tool actually used
    assert manifest["toolVersions"] == {"fake-fetch": "v9.9.9 fake-tool"}


def test_licensed_domain_request_is_executed_and_flagged_not_refused(tmp_path):
    # D6: licensed/inventoried domains are fetched like any other page and flagged
    # in the manifest row, not refused.
    reqs = [{"toolId": "fake-fetch", "verb": "read", "target": "https://trendforce.com/report"}]
    req_path = _write_requests(tmp_path, reqs)
    out_dir = tmp_path / "out"

    manifest = run_requests(req_path, out_dir, _fake_registry(), LICENSED)

    assert len(manifest["results"]) == 1
    row = manifest["results"][0]
    assert row["refused"] is None
    assert row["licensedSource"] == "trendforce.com"
    expected_stdout = "FETCHED https://trendforce.com/report\n"
    assert row["exitCode"] == 0
    assert row["bytes"] == len(expected_stdout)
    assert row["error"] is None
    assert row["path"] is not None
    result_path = pathlib.Path(row["path"])
    assert result_path.exists()
    assert result_path.read_text(encoding="utf-8") == expected_stdout
    # the request WAS executed (unlike the old hard-block) -> the tool was used
    assert manifest["toolVersions"] == {"fake-fetch": "v9.9.9 fake-tool"}


def test_nonzero_exit_records_exit_code_and_stderr_tail(tmp_path):
    reqs = [{"toolId": "fake-fetch", "verb": "fail", "target": "https://example.com/b"}]
    req_path = _write_requests(tmp_path, reqs)
    out_dir = tmp_path / "out"

    manifest = run_requests(req_path, out_dir, _fake_registry(), LICENSED)

    row = manifest["results"][0]
    assert row["refused"] is None
    assert row["exitCode"] == 3
    assert row["error"] is not None
    assert "boom: bad thing happened" in row["error"]
    # stdout (empty here) was still saved
    assert row["path"] is not None
    assert pathlib.Path(row["path"]).exists()


def test_one_bad_request_does_not_abort_the_batch(tmp_path):
    reqs = [
        {"toolId": "fake-fetch", "verb": "fail", "target": "https://example.com/bad"},
        {"toolId": "fake-fetch", "verb": "read", "target": "https://example.com/good"},
    ]
    req_path = _write_requests(tmp_path, reqs)
    out_dir = tmp_path / "out"

    manifest = run_requests(req_path, out_dir, _fake_registry(), LICENSED)

    assert len(manifest["results"]) == 2
    assert manifest["results"][0]["exitCode"] == 3
    assert manifest["results"][1]["exitCode"] == 0
    assert manifest["results"][1]["bytes"] > 0


def test_timeout_is_recorded_and_does_not_raise(tmp_path):
    sleepy_registry = {"tools": [{
        "id": "fake-fetch", "enabled": True, "role": "fetch",
        "healthCmd": {"windows": "x", "macos": "x", "linux": "x"},
        "fetchVerbs": {
            "read": {
                "argv": [sys.executable, "-c",
                         "import time; time.sleep(5)", "{target}"],
                "kind": "url",
            },
        },
    }]}
    reqs = [{"toolId": "fake-fetch", "verb": "read", "target": "https://example.com/slow"}]
    req_path = _write_requests(tmp_path, reqs)
    out_dir = tmp_path / "out"

    manifest = run_requests(req_path, out_dir, sleepy_registry, LICENSED, timeout=1)

    row = manifest["results"][0]
    assert row["path"] is None
    assert row["exitCode"] is None
    assert row["error"] is not None


def _huge_output_registry():
    """A fake tool whose `huge` verb prints a string well past MAX_RESULT_BYTES so we can
    prove the runner caps what it writes to disk (defense against a hostile/oversized
    response) rather than writing an unbounded amount of captured stdout."""
    return {"tools": [{
        "id": "fake-fetch", "enabled": True, "role": "fetch",
        "healthCmd": {"windows": "x", "macos": "x", "linux": "x"},
        "fetchVerbs": {
            "huge": {
                "argv": [sys.executable, "-c", "print('A' * 6_000_000)", "{target}"],
                "kind": "url",
            },
        },
    }]}


def test_large_result_is_capped_at_max_result_bytes_and_flagged_truncated(tmp_path):
    reqs = [{"toolId": "fake-fetch", "verb": "huge", "target": "https://example.com/big"}]
    req_path = _write_requests(tmp_path, reqs)
    out_dir = tmp_path / "out"

    manifest = run_requests(req_path, out_dir, _huge_output_registry(), LICENSED)

    row = manifest["results"][0]
    assert row["exitCode"] == 0
    assert row["path"] is not None
    result_path = pathlib.Path(row["path"])
    assert result_path.exists()
    on_disk = result_path.read_text(encoding="utf-8")
    assert len(on_disk) == MAX_RESULT_BYTES
    assert row["bytes"] == MAX_RESULT_BYTES
    assert row["error"] is not None
    assert "truncat" in row["error"].lower()


def test_unexpected_exception_during_one_request_is_recorded_and_batch_continues(tmp_path, monkeypatch):
    """A per-request exception that is neither TimeoutExpired nor OSError (simulated here
    by monkeypatching subprocess.run to raise ValueError on the first call) must still be
    recorded as a failed manifest row -- not raised out of run_requests -- and a later,
    otherwise-valid request in the same batch must still execute and appear in the
    manifest with its own result file."""
    reqs = [
        {"toolId": "fake-fetch", "verb": "read", "target": "https://example.com/willraise"},
        {"toolId": "fake-fetch", "verb": "read", "target": "https://example.com/good"},
    ]
    req_path = _write_requests(tmp_path, reqs)
    out_dir = tmp_path / "out"

    real_run = subprocess.run
    calls = {"n": 0}

    def flaky_run(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            raise ValueError("simulated unexpected failure")
        return real_run(*args, **kwargs)

    monkeypatch.setattr(subprocess, "run", flaky_run)

    manifest = run_requests(req_path, out_dir, _fake_registry(), LICENSED)

    assert len(manifest["results"]) == 2
    bad_row, good_row = manifest["results"]
    assert bad_row["path"] is None
    assert bad_row["exitCode"] is None
    assert bad_row["error"] is not None
    assert "ValueError" in bad_row["error"]

    assert good_row["exitCode"] == 0
    assert good_row["path"] is not None
    assert pathlib.Path(good_row["path"]).exists()
    assert good_row["bytes"] > 0

    # the manifest itself was still written to disk covering both rows -- the batch
    # was not aborted and the manifest was not dropped
    manifest_path = out_dir / "fetch-manifest.json"
    assert manifest_path.exists()
    on_disk = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert on_disk == manifest


def test_malformed_requests_file_is_rejected_before_execution(tmp_path):
    req_path = tmp_path / "requests.json"
    req_path.write_text("{ not json !!!", encoding="utf-8")
    out_dir = tmp_path / "out"
    with pytest.raises((ValueError, json.JSONDecodeError)):
        run_requests(req_path, out_dir, _fake_registry(), LICENSED)


def test_requests_file_must_be_a_json_array(tmp_path):
    req_path = tmp_path / "requests.json"
    req_path.write_text(json.dumps({"toolId": "x"}), encoding="utf-8")
    out_dir = tmp_path / "out"
    with pytest.raises(ValueError):
        run_requests(req_path, out_dir, _fake_registry(), LICENSED)


# --- SECURITY: path-traversal / metacharacter sanitization of the result filename ---

@pytest.mark.parametrize("hostile_target", [
    "https://example.com/../../evil",
    "https://example.com/a\\..\\..\\windows\\system32\\evil",
    "https://example.com/" + "x" * 500,  # absurdly long slug must still be sane
])
def test_hostile_target_produces_file_safely_inside_out_dir(tmp_path, hostile_target):
    reqs = [{"toolId": "fake-fetch", "verb": "read", "target": hostile_target}]
    req_path = _write_requests(tmp_path, reqs)
    out_dir = tmp_path / "out"

    manifest = run_requests(req_path, out_dir, _fake_registry(), LICENSED)

    row = manifest["results"][0]
    assert row["refused"] is None  # not a refusal case; this is a raw sanitization test
    assert row["path"] is not None
    result_path = pathlib.Path(row["path"]).resolve()
    out_resolved = out_dir.resolve()
    assert result_path.parent == out_resolved
    assert result_path.is_relative_to(out_resolved)
    # no path separators or ".." survived into the actual filename on disk
    assert result_path.exists()


def test_outname_field_is_never_used_for_the_result_path(tmp_path):
    reqs = [{"toolId": "fake-fetch", "verb": "read", "target": "https://example.com/a",
             "outName": "../../../../etc/passwd"}]
    req_path = _write_requests(tmp_path, reqs)
    out_dir = tmp_path / "out"

    manifest = run_requests(req_path, out_dir, _fake_registry(), LICENSED)

    row = manifest["results"][0]
    result_path = pathlib.Path(row["path"]).resolve()
    assert result_path.parent == out_dir.resolve()
    assert "passwd" not in result_path.name


# --- CLI wiring ---

def test_cli_webreach_fetch_happy_path(tmp_path, monkeypatch):
    reg_path = tmp_path / "registry.json"
    reg_path.write_text(json.dumps(_fake_registry()), encoding="utf-8")
    licensed_path = tmp_path / "licensed.json"
    licensed_path.write_text(json.dumps({"version": 1, "domains": sorted(LICENSED)}),
                             encoding="utf-8")
    reqs = [{"toolId": "fake-fetch", "verb": "read", "target": "https://example.com/a"}]
    req_path = _write_requests(tmp_path, reqs)
    out_dir = tmp_path / "out"

    rc = cli.main(["webreach-fetch",
                   "--requests", str(req_path),
                   "--out-dir", str(out_dir),
                   "--registry", str(reg_path),
                   "--licensed", str(licensed_path)])
    assert rc == 0
    manifest = json.loads((out_dir / "fetch-manifest.json").read_text(encoding="utf-8"))
    assert manifest["results"][0]["exitCode"] == 0


def test_cli_webreach_fetch_exit_2_on_missing_requests_file(tmp_path):
    reg_path = tmp_path / "registry.json"
    reg_path.write_text(json.dumps(_fake_registry()), encoding="utf-8")
    licensed_path = tmp_path / "licensed.json"
    licensed_path.write_text(json.dumps({"version": 1, "domains": sorted(LICENSED)}),
                             encoding="utf-8")
    out_dir = tmp_path / "out"
    missing_path = tmp_path / "does-not-exist.json"

    rc = cli.main(["webreach-fetch",
                   "--requests", str(missing_path),
                   "--out-dir", str(out_dir),
                   "--registry", str(reg_path),
                   "--licensed", str(licensed_path)])
    assert rc == 2


def test_cli_webreach_fetch_exit_2_on_malformed_json(tmp_path):
    reg_path = tmp_path / "registry.json"
    reg_path.write_text(json.dumps(_fake_registry()), encoding="utf-8")
    licensed_path = tmp_path / "licensed.json"
    licensed_path.write_text(json.dumps({"version": 1, "domains": sorted(LICENSED)}),
                             encoding="utf-8")
    bad_path = tmp_path / "requests.json"
    bad_path.write_text("{ not json !!!", encoding="utf-8")
    out_dir = tmp_path / "out"

    rc = cli.main(["webreach-fetch",
                   "--requests", str(bad_path),
                   "--out-dir", str(out_dir),
                   "--registry", str(reg_path),
                   "--licensed", str(licensed_path)])
    assert rc == 2


def test_cli_webreach_fetch_exit_2_on_malformed_registry_keyerror(tmp_path):
    """A registry file that is valid JSON but structurally malformed (missing the
    "tools" key any real registry has) must surface as a clean exit 2, not an
    uncaught KeyError traceback."""
    reg_path = tmp_path / "registry.json"
    reg_path.write_text("{}", encoding="utf-8")
    licensed_path = tmp_path / "licensed.json"
    licensed_path.write_text(json.dumps({"version": 1, "domains": sorted(LICENSED)}),
                             encoding="utf-8")
    reqs = [{"toolId": "fake-fetch", "verb": "read", "target": "https://example.com/a"}]
    req_path = _write_requests(tmp_path, reqs)
    out_dir = tmp_path / "out"

    rc = cli.main(["webreach-fetch",
                   "--requests", str(req_path),
                   "--out-dir", str(out_dir),
                   "--registry", str(reg_path),
                   "--licensed", str(licensed_path)])
    assert rc == 2


def test_cli_webreach_fetch_exit_2_on_malformed_licensed_domains_keyerror(tmp_path):
    """Same as above but for a structurally malformed --licensed file (valid JSON,
    missing the "domains" key)."""
    reg_path = tmp_path / "registry.json"
    reg_path.write_text(json.dumps(_fake_registry()), encoding="utf-8")
    licensed_path = tmp_path / "licensed.json"
    licensed_path.write_text("{}", encoding="utf-8")
    reqs = [{"toolId": "fake-fetch", "verb": "read", "target": "https://example.com/a"}]
    req_path = _write_requests(tmp_path, reqs)
    out_dir = tmp_path / "out"

    rc = cli.main(["webreach-fetch",
                   "--requests", str(req_path),
                   "--out-dir", str(out_dir),
                   "--registry", str(reg_path),
                   "--licensed", str(licensed_path)])
    assert rc == 2


def test_cli_webreach_fetch_exit_2_on_schema_invalid_request(tmp_path):
    """A requests file that is a valid JSON array containing an object missing a
    required field (here: "verb") must exit 2 via the pydantic ValidationError path,
    not raise out of cli.main."""
    reg_path = tmp_path / "registry.json"
    reg_path.write_text(json.dumps(_fake_registry()), encoding="utf-8")
    licensed_path = tmp_path / "licensed.json"
    licensed_path.write_text(json.dumps({"version": 1, "domains": sorted(LICENSED)}),
                             encoding="utf-8")
    bad_path = tmp_path / "requests.json"
    bad_path.write_text(json.dumps([{"toolId": "fake-fetch",
                                     "target": "https://example.com/a"}]),
                        encoding="utf-8")  # missing required "verb"
    out_dir = tmp_path / "out"

    rc = cli.main(["webreach-fetch",
                   "--requests", str(bad_path),
                   "--out-dir", str(out_dir),
                   "--registry", str(reg_path),
                   "--licensed", str(licensed_path)])
    assert rc == 2


def test_cli_webreach_fetch_exit_2_on_non_list_json(tmp_path):
    reg_path = tmp_path / "registry.json"
    reg_path.write_text(json.dumps(_fake_registry()), encoding="utf-8")
    licensed_path = tmp_path / "licensed.json"
    licensed_path.write_text(json.dumps({"version": 1, "domains": sorted(LICENSED)}),
                             encoding="utf-8")
    bad_path = tmp_path / "requests.json"
    bad_path.write_text(json.dumps({"toolId": "x"}), encoding="utf-8")
    out_dir = tmp_path / "out"

    rc = cli.main(["webreach-fetch",
                   "--requests", str(bad_path),
                   "--out-dir", str(out_dir),
                   "--registry", str(reg_path),
                   "--licensed", str(licensed_path)])
    assert rc == 2
