from gpu_agent.wiki.log import WikiLog, LogEvent


def test_append_assigns_monotonic_seq(tmp_path):
    log = WikiLog(tmp_path / "log.jsonl")
    e0 = log.append(asOf="2026-06-26", kind="create-page", pageId="theme:x")
    e1 = log.append(asOf="2026-06-26", kind="append-observation", pageId="theme:x", findingId="f-1")
    assert e0.seq == 0 and e1.seq == 1


def test_read_returns_all_events_in_order(tmp_path):
    log = WikiLog(tmp_path / "log.jsonl")
    log.append(asOf="2026-06-26", kind="create-page", pageId="theme:x")
    log.append(asOf="2026-06-27", kind="state-change", pageId="theme:x",
               state="slipping", trajectory="t", salience=0.5)
    evs = log.read()
    assert [e.kind for e in evs] == ["create-page", "state-change"]
    assert evs[1].salience == 0.5


def test_read_missing_file_is_empty(tmp_path):
    assert WikiLog(tmp_path / "none.jsonl").read() == []


def test_append_event_restamps_seq(tmp_path):
    log = WikiLog(tmp_path / "log.jsonl")
    log.append(asOf="2026-06-26", kind="create-page", pageId="p")
    log.append_event(LogEvent(seq=999, asOf="2026-06-27", kind="ingest", detail="brain"))
    evs = log.read()
    assert evs[-1].seq == 1 and evs[-1].kind == "ingest" and evs[-1].detail == "brain"
