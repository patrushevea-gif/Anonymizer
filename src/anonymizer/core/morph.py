"""Shared, lazily-loaded Russian morphological analyzer.

Natasha's ``MorphVocab`` is a thin wrapper over pymorphy2 that ships with the
OpenCorpora dictionary. That dictionary tags given names (``Name``),
surnames (``Surn``) and patronymics (``Patr``), which is exactly what the
rule-based person detector and the person linker need.

The analyzer is optional: when Natasha / pymorphy2 are not installed the
helpers here return ``None`` and callers fall back to suffix heuristics.
"""
from __future__ import annotations

import logging
import threading
from functools import lru_cache

_log = logging.getLogger(__name__)

_lock = threading.Lock()
_analyzer = None
_failed = False


def get_analyzer():
    """Return the shared analyzer or ``None`` if it can't be loaded."""
    global _analyzer, _failed
    if _analyzer is not None or _failed:
        return _analyzer
    with _lock:
        if _analyzer is not None or _failed:
            return _analyzer
        try:
            from natasha import MorphVocab

            _analyzer = MorphVocab()
        except Exception:  # pragma: no cover - depends on optional deps
            _log.warning("Morphological dictionary unavailable; using heuristics")
            _failed = True
    return _analyzer


@lru_cache(maxsize=65536)
def parses(word: str) -> tuple[tuple[frozenset[str], str, float], ...]:
    """Return ``(grammemes, normal_form, score)`` for every parse of *word*."""
    analyzer = get_analyzer()
    if analyzer is None:
        return ()
    out = []
    for p in analyzer.parse(word.lower()):
        out.append((frozenset(p.tag.grammemes), p.normal_form, float(p.score)))
    return tuple(out)


def role_score(word: str, grammeme: str) -> float:
    """Summed probability that *word* carries *grammeme* (Name/Surn/Patr/…)."""
    return sum(score for tags, _, score in parses(word) if grammeme in tags)


def lemma_for(word: str, grammeme: str) -> str | None:
    """Best normal form of *word* among parses tagged with *grammeme*."""
    best: tuple[float, str] | None = None
    for tags, normal, score in parses(word):
        if grammeme in tags and (best is None or score > best[0]):
            best = (score, normal)
    return best[1] if best else None


def is_known(word: str) -> bool:
    analyzer = get_analyzer()
    if analyzer is None:
        return False
    return bool(analyzer.word_is_known(word.lower()))


def best_tags(word: str) -> frozenset[str]:
    p = parses(word)
    return p[0][0] if p else frozenset()


def is_nominative(word: str) -> bool:
    p = parses(word)
    if not p:
        return True
    return any("nomn" in tags for tags, _, _ in p)
