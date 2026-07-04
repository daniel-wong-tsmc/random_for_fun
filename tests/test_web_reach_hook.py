import json
import pathlib

SETTINGS = pathlib.Path(".claude/settings.json")


def test_settings_parses():
    data = json.loads(SETTINGS.read_text(encoding="utf-8"))
    assert isinstance(data, dict)


def test_sessionstart_hook_runs_the_launcher():
    data = json.loads(SETTINGS.read_text(encoding="utf-8"))
    hooks = data.get("hooks", {})
    ss = hooks.get("SessionStart")
    assert ss, "no SessionStart hook configured"
    blob = json.dumps(ss)
    assert "web-reach-ensure" in blob, "SessionStart hook must call the ensure launcher"
