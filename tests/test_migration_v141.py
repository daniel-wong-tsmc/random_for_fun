"""Contract v1.4.1 migration note pin (F72 follow-up, spec acceptance #5): the note must
exist, name the version, and carry the read-only shadow-check result."""
import pathlib

NOTE = (pathlib.Path(__file__).resolve().parents[1]
        / "docs" / "migrations" / "2026-07-contract-v1.4.1.md")


def test_migration_note_exists_names_version_and_carries_shadow_check():
    text = NOTE.read_text("utf-8")
    assert "v1.4.1" in text
    assert "sufficiency" in text.lower()
    assert "collapsed_publisher_set" in text
    assert "shadow-check" in text.lower()
