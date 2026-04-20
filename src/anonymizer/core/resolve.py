from anonymizer.core.entities import EntitySpan


def _overlaps(a: EntitySpan, b: EntitySpan) -> bool:
    return a.start < b.end and b.start < a.end


def resolve_overlaps(spans: list[EntitySpan]) -> list[EntitySpan]:
    ranked = sorted(
        spans,
        key=lambda s: (-s.priority, -(s.end - s.start), s.start),
    )
    accepted: list[EntitySpan] = []
    for span in ranked:
        if any(_overlaps(span, kept) for kept in accepted):
            continue
        accepted.append(span)
    return sorted(accepted, key=lambda s: s.start)
