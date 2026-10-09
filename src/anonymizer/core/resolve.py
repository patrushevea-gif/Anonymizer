import bisect

from anonymizer.core.entities import EntitySpan


class IntervalSet:
    """Non-overlapping half-open intervals with O(log n) overlap queries."""

    def __init__(self) -> None:
        self._starts: list[int] = []
        self._ends: list[int] = []

    def overlaps(self, start: int, end: int) -> bool:
        i = bisect.bisect_left(self._ends, start + 1)  # first interval ending after start
        return i < len(self._starts) and self._starts[i] < end

    def add(self, start: int, end: int) -> None:
        i = bisect.bisect_left(self._starts, start)
        self._starts.insert(i, start)
        self._ends.insert(i, end)


def resolve_overlaps(spans: list[EntitySpan]) -> list[EntitySpan]:
    ranked = sorted(
        spans,
        key=lambda s: (-s.priority, -(s.end - s.start), s.start),
    )
    taken = IntervalSet()
    accepted: list[EntitySpan] = []
    for span in ranked:
        if taken.overlaps(span.start, span.end):
            continue
        taken.add(span.start, span.end)
        accepted.append(span)
    return sorted(accepted, key=lambda s: s.start)
