"""Deterministic Aho-Corasick multi-substring matcher (F25). Exact `pattern in text`
semantics - no word boundaries. Build once, scan each text once: O(sum|pattern| +
|text| + matches) instead of the per-pair O(pages^2 * |body|) substring scan."""
from __future__ import annotations
from collections import deque
from typing import Iterable


class MultiSubstringMatcher:
    def __init__(self, patterns: Iterable[str]):
        # de-dupe (preserve order), drop empties (an empty pattern would "match" everywhere)
        self._patterns = [p for p in dict.fromkeys(patterns) if p]
        self._goto = [{}]        # node -> {char: node}
        self._fail = [0]
        self._out = [set()]      # node -> set of pattern indices ending here (incl. suffix links)
        self._build()

    def _build(self) -> None:
        for pid, pat in enumerate(self._patterns):
            node = 0
            for ch in pat:
                nxt = self._goto[node].get(ch)
                if nxt is None:
                    nxt = len(self._goto)
                    self._goto.append({})
                    self._fail.append(0)
                    self._out.append(set())
                    self._goto[node][ch] = nxt
                node = nxt
            self._out[node].add(pid)
        q = deque()
        for _, u in self._goto[0].items():
            self._fail[u] = 0
            q.append(u)
        while q:
            r = q.popleft()
            for ch, u in self._goto[r].items():
                q.append(u)
                v = self._fail[r]
                while v and ch not in self._goto[v]:
                    v = self._fail[v]
                self._fail[u] = self._goto[v].get(ch, 0)
                self._out[u] |= self._out[self._fail[u]]

    def matches(self, text: str) -> set:
        found = set()
        node = 0
        for ch in text:
            while node and ch not in self._goto[node]:
                node = self._fail[node]
            node = self._goto[node].get(ch, 0)
            for pid in self._out[node]:
                found.add(self._patterns[pid])
        return found
