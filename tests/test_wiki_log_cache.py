from gpu_agent.wiki.log import WikiLog


def test_second_read_parses_no_new_lines(tmp_path):
    log = WikiLog(tmp_path / "log.jsonl")
    for i in range(5):
        log.append(asOf="2026-06-01", kind="append-observation", pageId="p", findingId=f"f{i}")
    log.parsed_lines = 0            # zero the counter after the writes
    log.read()
    first = log.parsed_lines
    log.read()                      # no append in between
    assert log.parsed_lines == first  # zero additional parses -> cache served it


def test_fresh_instance_reads_once_then_caches(tmp_path):
    w = WikiLog(tmp_path / "log.jsonl")
    for i in range(4):
        w.append(asOf="2026-06-01", kind="append-observation", pageId="p", findingId=f"f{i}")
    r = WikiLog(tmp_path / "log.jsonl")           # cold instance on existing file
    assert r.parsed_lines == 0
    assert len(r.read()) == 4
    assert r.parsed_lines == 4                     # one pass
    r.read()
    assert r.parsed_lines == 4                     # no re-parse


def test_external_append_is_picked_up(tmp_path):
    a = WikiLog(tmp_path / "log.jsonl")
    a.append(asOf="2026-06-01", kind="create-page", pageId="p")
    b = WikiLog(tmp_path / "log.jsonl")
    b.read()
    a.append(asOf="2026-06-02", kind="append-observation", pageId="p", findingId="f1")
    assert [e.kind for e in b.read()] == ["create-page", "append-observation"]


def test_events_for_page_filters(tmp_path):
    log = WikiLog(tmp_path / "log.jsonl")
    log.append(asOf="2026-06-01", kind="create-page", pageId="p")
    log.append(asOf="2026-06-01", kind="create-page", pageId="q")
    log.append(asOf="2026-06-02", kind="append-observation", pageId="p", findingId="f1")
    assert [e.kind for e in log.events_for_page("p")] == ["create-page", "append-observation"]
    assert [e.pageId for e in log.events_for_page("q")] == ["q"]


def test_partial_trailing_line_ignored(tmp_path):
    path = tmp_path / "log.jsonl"
    path.write_text('{"seq":0,"asOf":"2026-06-01","kind":"create-page","pageId":"p"}\n{"seq":1,"asOf"',
                    encoding="utf-8")   # second line has no newline / is truncated
    log = WikiLog(path)
    assert len(log.read()) == 1          # only the complete line is consumed
