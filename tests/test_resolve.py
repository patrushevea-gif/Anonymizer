from anonymizer.core.entities import EntityKind, EntitySpan
from anonymizer.core.resolve import resolve_overlaps


def test_higher_priority_wins() -> None:
    low = EntitySpan(EntityKind.INN, 0, 10, "0000000000", priority=50)
    high = EntitySpan(EntityKind.PHONE, 0, 10, "0000000000", priority=80)
    kept = resolve_overlaps([low, high])
    assert kept == [high]


def test_non_overlapping_all_kept() -> None:
    a = EntitySpan(EntityKind.PHONE, 0, 5, "xxxxx", priority=80)
    b = EntitySpan(EntityKind.EMAIL, 10, 20, "y@z.ru", priority=90)
    kept = resolve_overlaps([a, b])
    assert len(kept) == 2
    assert kept[0].start < kept[1].start


def test_longer_span_wins_on_tie() -> None:
    short = EntitySpan(EntityKind.PHONE, 2, 6, "aaaa", priority=50)
    long = EntitySpan(EntityKind.PHONE, 0, 10, "aaaaaaaaaa", priority=50)
    kept = resolve_overlaps([short, long])
    assert kept == [long]
