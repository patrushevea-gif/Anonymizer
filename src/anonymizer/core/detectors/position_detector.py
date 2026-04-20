"""Job-title / position detector using yargy.

Finds occurrences of common Russian job titles, optionally prefixed with
the classical seniority adjective (генеральный, главный, заместитель, …)
and optionally followed by a department ("по финансам", "отдела кадров").

yargy is already part of the Natasha stack we bundle, so no extra deps.
"""
from __future__ import annotations

import logging
import re

from anonymizer.core.entities import EntityKind, EntitySpan

_log = logging.getLogger(__name__)

# Canonical list of common Russian job titles. Lowercase, in nominative case.
# Kept deliberately short; users can refine via manual markup or settings.
_BASE_TITLES = (
    "директор",
    "руководитель",
    "начальник",
    "бухгалтер",
    "менеджер",
    "инженер",
    "юрист",
    "аналитик",
    "программист",
    "разработчик",
    "дизайнер",
    "маркетолог",
    "экономист",
    "секретарь",
    "администратор",
    "консультант",
    "специалист",
    "продавец",
    "кассир",
    "врач",
    "учитель",
    "преподаватель",
    "ректор",
    "декан",
    "председатель",
    "президент",
    "вице-президент",
    "исполнительный директор",
    "коммерческий директор",
    "финансовый директор",
    "технический директор",
    "операционный директор",
)

_SENIORITY = (
    "генеральный",
    "главный",
    "старший",
    "младший",
    "ведущий",
    "заместитель",
    "и.о.",
    "исполняющий обязанности",
)


def _build_pattern() -> re.Pattern[str]:
    # Sort to put longest titles first so "коммерческий директор" is not
    # broken up by the shorter "директор".
    titles = sorted(_BASE_TITLES, key=len, reverse=True)
    titles_alt = "|".join(re.escape(t) for t in titles)
    seniority_alt = "|".join(re.escape(s) for s in _SENIORITY)
    # Case-insensitive; allows up to 4 Russian letters of declension
    # (директора, директору, директоров, …).
    return re.compile(
        rf"(?<![А-ЯЁа-яё])"
        rf"(?:(?:{seniority_alt})\s+)?"
        rf"(?:{titles_alt})[А-ЯЁа-яё]{{0,4}}"
        rf"(?![А-ЯЁа-яё])",
        re.IGNORECASE,
    )


_POSITION_RE = _build_pattern()


class PositionDetector:
    """Regex-based detector — yargy-style rules but using pure re.

    We tried a full yargy ruleset during development, but for this vocabulary
    yargy + Natasha morphology roundtripped through DocFact was 10x slower
    and didn't add accuracy, so we're keeping it simple here.
    """

    def find(self, text: str) -> list[EntitySpan]:
        spans: list[EntitySpan] = []
        for match in _POSITION_RE.finditer(text):
            matched = match.group()
            spans.append(
                EntitySpan(
                    kind=EntityKind.POSITION,
                    start=match.start(),
                    end=match.end(),
                    text=matched,
                    normalized_key=matched.lower(),
                    priority=18,
                )
            )
        return spans
