from pathlib import Path

def _gitignore():
    return Path(".gitignore").read_text(encoding="utf-8", errors="replace")

def test_voice_samples_and_profile_are_gitignored():
    gi = _gitignore()
    assert ".claude/agents/plain-language-writer/voice-samples/" in gi
    assert ".claude/agents/plain-language-writer/voice-profile.md" in gi

def test_agent_definition_exists_and_declares_separate_output_file():
    txt = Path(".claude/agents/plain-language-writer.md").read_text(encoding="utf-8", errors="replace")
    assert "store/chips.merchant-gpu/plain-language/" in txt
    assert "voice-profile.md" in txt
    assert "style, never content" in txt.lower()
