#!/usr/bin/env python3
"""status_reconcile.py -- is F-item <N> actually merged, regardless of what its
docs/fix-backlog.md checkbox says?

Why this exists: this repo's backlog checkboxes go stale (fixed forward, box never
ticked) far more often than they go wrong the other way. Reconciling by hand means
reading prose and guessing; this script instead asks git the only question that
matters -- "is a commit that plausibly closes F<N> an ancestor of HEAD?" -- and
prints a verdict you can act on.

STDLIB ONLY. Read-only: never writes, never mutates git state (no add/commit/checkout).
Shells out to `git` (must be on PATH) via subprocess; nothing else external.

Usage (from repo root, or pass --repo):
    .venv/Scripts/python .claude/skills/desk-diagnostics-and-tooling/scripts/status_reconcile.py F74
    .venv/Scripts/python ...\\status_reconcile.py F71 F73 F63          # multiple at once
    .venv/Scripts/python ...\\status_reconcile.py --all                # every F-item in the backlog
    .venv/Scripts/python ...\\status_reconcile.py F63 --repo C:\\path\\to\\random_for_fun

Exit codes:
    0 = every requested item's checkbox agrees with git reality
    1 = at least one item is STALE_CHECKBOX or CHECKBOX_AHEAD (a real disagreement)
    2 = operator error (bad F-number, backlog file not found, git not found, etc.)

See the INTERPRETATION table in this repo's desk-diagnostics-and-tooling SKILL.md for
what each verdict means and which sibling skill/action it routes to.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

# Windows' default console codepage (cp1252) chokes on the em-dashes/arrows this repo's
# docs are full of. Force UTF-8 on stdout/stderr so a HANDOFF.md quote never crashes the
# script (verified crash while building this: F31's HANDOFF line containing an arrow).
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

BACKLOG_REL = "docs/fix-backlog.md"
HASH_RE = re.compile(r"\b[0-9a-f]{7,40}\b")
# An F-item's checkbox line, e.g. "- [x] **F74 — post-run writer clobbers ..."
ITEM_START_RE = re.compile(r"^-\s*\[( |x|X)\]\s*\*\*F(\d+)\b")
# Any top-level bullet (the next item, or a feature/backlog bullet) ends the current block.
NEXT_BULLET_RE = re.compile(r"^-\s*\[")


def run(repo: Path, *args: str) -> tuple[int, str, str]:
    proc = subprocess.run(["git", "-C", str(repo), *args], capture_output=True,
                           encoding="utf-8", errors="replace")
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def find_repo_root(start: Path) -> Path | None:
    code, out, _ = run(start, "rev-parse", "--show-toplevel")
    if code != 0:
        return None
    return Path(out)


def load_backlog_blocks(repo: Path) -> dict[int, tuple[bool, str, int]]:
    """Return {F-number: (checked, block_text, line_no)} for every top-level F-item
    bullet in docs/fix-backlog.md. block_text runs from the bullet's own line up to
    (not including) the next top-level bullet, `##`/`###` heading, or EOF."""
    path = repo / BACKLOG_REL
    if not path.exists():
        print(f"error: {BACKLOG_REL} not found under {repo}", file=sys.stderr)
        sys.exit(2)
    lines = path.read_text(encoding="utf-8").splitlines()
    items: dict[int, tuple[bool, str, int]] = {}
    i = 0
    while i < len(lines):
        m = ITEM_START_RE.match(lines[i])
        if not m:
            i += 1
            continue
        checked = m.group(1).lower() == "x"
        num = int(m.group(2))
        start = i
        j = i + 1
        while j < len(lines):
            if NEXT_BULLET_RE.match(lines[j]) or lines[j].startswith("#"):
                break
            j += 1
        items[num] = (checked, "\n".join(lines[start:j]), start + 1)
        i = j
    return items


## Matches this repo's own DONE-note convention: the hash follows the word "merge(d)"
## within a short span, e.g. "merged to main `257cf1b`", "merged `e167c6b`", "merged 7197226".
## DIRECTIONAL on purpose: a hash that PRECEDES "merged" in the sentence is being discussed,
## not cited as the fix (F76's prose quotes `da58b94` as *"title da58b94 says F63 merged"* --
## an example of a bug, not F76's own closing commit; a symmetric before-or-after proximity
## check was tried first and produced exactly this false positive while building the script).
_MERGE_HASH_RE = re.compile(
    r"merged?(?:\s+(?:to|on|into)\s+\S+)?\s*[:,]?\s*`?([0-9a-f]{7,40})`?", re.IGNORECASE)


def candidate_hashes_from_text(repo: Path, text: str) -> list[str]:
    """Hex tokens that git recognizes as real commits AND that this repo's own prose cites
    as the actual merge (hash follows "merge(d)", not merely near it in either direction)."""
    seen: list[str] = []
    for m in _MERGE_HASH_RE.finditer(text):
        tok = m.group(1)
        if tok in seen:
            continue
        code, _, _ = run(repo, "cat-file", "-e", f"{tok}^{{commit}}")
        if code == 0:
            seen.append(tok)
    return seen


def grep_commits(repo: Path, fnum: int, merges_only: bool = False) -> list[str]:
    """Commits (all branches/tags) whose message mentions F<n> as a whole word, i.e.
    F74 but not F740 or F7. --all so a merged-then-deleted-remote branch still counts
    (this repo's history has exactly that shape at least once, F62)."""
    args = ["log", "--all", "--oneline", f"--grep=F{fnum}\\b", "-E"]
    if merges_only:
        args.append("--merges")
    code, out, _ = run(repo, *args)
    if code != 0 or not out:
        return []
    return [line.split(" ", 1)[0] for line in out.splitlines()]


def subject_line_hits(repo: Path, fnum: int) -> list[str]:
    """Commits whose SUBJECT line (not body) names F<n> and whose type is not `docs(...)`.
    This is real signal in this repo's convention: fix(F74)/feat(...)  (F9)-suffixed
    subjects are the change itself; docs(backlog)/docs(handoff) subjects only discuss or
    announce an item (opening it, cross-referencing it from an unrelated run-note) and
    must not count as closure evidence on their own -- verified against F71/F73/F75/F76
    (all open; their only F<n>-bearing commits are docs(backlog)/docs(handoff)) and F9
    (closed pre-lane era with no "merged <hash>" phrase at all; its only tell is the
    feat(v1.2)...(F9) subject line -- this tier exists so items like it aren't misread
    as CHECKBOX_AHEAD)."""
    code, out, _ = run(repo, "log", "--all", "--format=%H\x01%s")
    if code != 0:
        return []
    pat = re.compile(rf"\bF{fnum}\b")
    hits = []
    for line in out.splitlines():
        h, _, subject = line.partition("\x01")
        if pat.search(subject) and not subject.lower().startswith("docs("):
            hits.append(h)
    return hits


def is_ancestor(repo: Path, commit: str, of: str = "HEAD") -> bool:
    code, _, _ = run(repo, "merge-base", "--is-ancestor", commit, of)
    return code == 0


def handoff_mentions(repo: Path, fnum: int) -> list[str]:
    """Lines in docs/superpowers/HANDOFF.md mentioning F<n> -- informational only. Some
    closures (e.g. F61 'DONE (subsumed by F67)') are recorded ONLY as HANDOFF prose with no
    dedicated commit of their own, so git ancestry alone cannot see them; surface the line
    and let the human/model read it, never fold it into the verdict."""
    path = repo / "docs/superpowers/HANDOFF.md"
    if not path.exists():
        return []
    pat = re.compile(rf"\bF{fnum}\b(?!\d)")
    return [ln.strip() for ln in path.read_text(encoding="utf-8").splitlines() if pat.search(ln)]


def reconcile_one(repo: Path, fnum: int, backlog: dict) -> tuple[str, str]:
    """Returns (verdict, explanation)."""
    if fnum not in backlog:
        return "NOT_IN_BACKLOG", f"F{fnum} has no top-level checkbox bullet in {BACKLOG_REL}."

    checked, block, line_no = backlog[fnum]
    text_hashes = candidate_hashes_from_text(repo, block)
    grep_all = grep_commits(repo, fnum)
    grep_merges = grep_commits(repo, fnum, merges_only=True)
    subject_hits = subject_line_hits(repo, fnum)

    # STRONG evidence only: a hash the backlog prose itself cites next to "merged", an actual
    # `Merge branch ...` commit mentioning F<n>, or a non-docs commit with F<n> in its own
    # SUBJECT line. A commit that merely DISCUSSES an open item ("F71 remains OPEN", a
    # docs(backlog) entry, an unrelated commit's footnote in its BODY) is real, findable
    # history but NOT evidence of a fix -- and because merge-base --is-ancestor is trivially
    # true for anything already on mainline, counting plain --grep body hits as "merged"
    # produces false MERGED verdicts for items that are genuinely still open (verified
    # false-positive on F71/F73/F76 while building this script).
    strong: list[str] = []
    for h in dict.fromkeys(text_hashes + grep_merges + subject_hits):
        if is_ancestor(repo, h):
            strong.append(h)
    merged_via = strong

    any_evidence = bool(text_hashes or grep_all)
    is_merged = bool(merged_via)

    loc = f"{BACKLOG_REL}:{line_no}"
    if is_merged and checked:
        return "MERGED", (f"checkbox=[x] agrees with git ({loc}); ancestor commit(s): "
                           f"{', '.join(merged_via[:3])}")
    if is_merged and not checked:
        return "STALE_CHECKBOX", (f"checkbox=[ ] but git proves it merged ({loc}); "
                                   f"ancestor commit(s): {', '.join(merged_via[:3])} -- "
                                   f"trust git, treat as DONE, and consider fixing the checkbox.")
    if checked and not is_merged and any_evidence:
        return "CHECKBOX_AHEAD", (f"checkbox=[x] ({loc}) but no candidate commit for F{fnum} "
                                   f"is an ancestor of HEAD (candidates seen: "
                                   f"{', '.join((text_hashes + grep_all)[:5]) or 'none'}). "
                                   f"Possibly checked from a branch/worktree that never merged, "
                                   f"or the DONE record touched other files only (the F44/"
                                   f"START-HERE.md precedent) -- verify by hand before trusting.")
    if checked and not any_evidence:
        return "CHECKBOX_AHEAD", (f"checkbox=[x] ({loc}) but no commit anywhere mentions F{fnum} "
                                   f"-- unusual; verify by hand.")
    if not checked and any_evidence and not is_merged:
        return "OPEN_WITH_ACTIVITY", (f"checkbox=[ ] ({loc}), matches git: commits reference "
                                       f"F{fnum} ({', '.join(grep_all[:3])}) but none are merged "
                                       f"to HEAD yet -- work in progress or abandoned, not done.")
    return "OPEN", f"checkbox=[ ] ({loc}), no commit anywhere mentions F{fnum} -- genuinely untouched."


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("items", nargs="*", help="F-numbers to check, e.g. F74 71 F73")
    ap.add_argument("--all", action="store_true", help="check every F-item in the backlog")
    ap.add_argument("--repo", default=".", help="repo root (default: cwd, auto-detected via git)")
    args = ap.parse_args()

    repo = find_repo_root(Path(args.repo))
    if repo is None:
        print(f"error: {args.repo} is not inside a git repo (is `git` on PATH? "
              f"are you in random_for_fun?)", file=sys.stderr)
        return 2

    backlog = load_backlog_blocks(repo)

    if args.all:
        nums = sorted(backlog)
    else:
        nums = []
        for tok in args.items:
            m = re.search(r"\d+", tok)
            if not m:
                print(f"error: not an F-number: {tok!r}", file=sys.stderr)
                return 2
            nums.append(int(m.group()))
        if not nums:
            ap.print_help()
            return 2

    disagreement = False
    for n in nums:
        verdict, explanation = reconcile_one(repo, n, backlog)
        if verdict in ("STALE_CHECKBOX", "CHECKBOX_AHEAD"):
            disagreement = True
        print(f"F{n}: {verdict}")
        print(f"  {explanation}")
        for hl in handoff_mentions(repo, n)[:3]:
            print(f"  HANDOFF.md says: {hl}")

    return 1 if disagreement else 0


if __name__ == "__main__":
    sys.exit(main())
