"""Rule-based detector of Russian postal addresses.

Finds address components (index, region, settlement, street, house,
building, flat/office) and merges neighbouring components into a single
АДРЕС span: «г. Примерск, ул. Тестовая, д. 12, офис 34» becomes one entity
rather than leaking the house number or office next to a masked city.
"""
from __future__ import annotations

import re

from anonymizer.core.entities import EntityKind, EntitySpan

ADDRESS_PRIORITY = 28

_CAP = r"[А-ЯЁ][А-ЯЁа-яё]*(?:-(?:на-|он-)?[А-ЯЁа-яё]+)*"
_CAP_SEQ = rf"{_CAP}(?:\s+{_CAP}){{0,2}}"
_NUM_NAME = rf"(?:\d{{1,3}}(?:-?(?:я|й|го|ая|ий|ой))?\s+)?{_CAP_SEQ}"

_CITY_TYPES = (
    r"г\.|гор\.|город|пос\.|посёлок|поселок|пгт\.?|р\.\s?п\.|рп\.|с\.|село|дер\.|деревня"
    r"|ст-ца|станица|х\.|хутор|аул|нп\.?"
)
_STREET_TYPES = (
    r"ул\.|улица|пр-т|пр-кт|просп\.|проспект|пр\.|пер\.|переулок|ш\.|шоссе|наб\.|набережная"
    r"|б-р|бул\.|бульвар|пл\.|площадь|проезд|пр-д|туп\.|тупик|аллея|линия|мкр\.?|мкрн\.?"
    r"|микрорайон|кв-л|квартал|тракт|тер\.|территория|снт|СНТ"
)
_REGION_TYPES = r"обл\.|область|край|р-н|район|респ\.|республика|Республика|автономный\s+округ"

_COMPONENTS = [
    # Postal index: only meaningful as part of an address chain.
    ("index", re.compile(r"(?<!\d)\d{6}(?!\d)")),
    ("region", re.compile(
        rf"(?<![А-ЯЁа-яё])(?:(?:{_REGION_TYPES})\s+{_CAP_SEQ}|{_CAP}\s+(?:{_REGION_TYPES}))(?![А-ЯЁа-яё])"
    )),
    ("city", re.compile(
        rf"(?<![А-ЯЁа-яё\d])(?<!\d\s)(?:{_CITY_TYPES})\s*{_CAP_SEQ}(?![А-ЯЁа-яё])"
    )),
    ("street", re.compile(
        rf"(?<![А-ЯЁа-яё])(?:(?:{_STREET_TYPES})\s*{_NUM_NAME}|{_CAP_SEQ}\s+(?:{_STREET_TYPES}))(?![А-ЯЁа-яё])"
    )),
    ("house", re.compile(
        r"(?<![А-ЯЁа-яё])(?:д\.|дом|вл\.|владение|зд\.|здание)\s*№?\s*\d+[А-Яа-яA-Za-z]?(?:\s?/\s?\d+[А-Яа-я]?)?(?![\d])"
    )),
    ("building", re.compile(
        r"(?<![А-ЯЁа-яё])(?:корп\.|корпус|к\.|стр\.|строение|лит\.|литера|литер)\s*[\dА-ЯA-Z]{1,4}(?![\d])"
    )),
    ("flat", re.compile(
        r"(?<![А-ЯЁа-яё])(?:кв\.|квартира|оф\.|офис|пом\.|помещение|комн\.|комната|каб\.|кабинет)\s*№?\s*\d+[А-Яа-я]?(?:-\d+)?(?![\d])"
    )),
]

_SEP_RE = re.compile(r"[\s,]{0,4}")
# Kinds that can stand alone as an address without neighbours.
_STANDALONE = {"street", "city", "region"}


class AddressDetector:
    def find(self, text: str) -> list[EntitySpan]:
        comps: list[tuple[int, int, str]] = []
        for kind, pattern in _COMPONENTS:
            for m in pattern.finditer(text):
                comps.append((m.start(), m.end(), kind))
        if not comps:
            return []
        # Keep the longest non-overlapping components.
        comps.sort(key=lambda c: (c[0], -(c[1] - c[0])))
        clean: list[tuple[int, int, str]] = []
        for c in comps:
            if clean and c[0] < clean[-1][1]:
                if c[1] - c[0] > clean[-1][1] - clean[-1][0] and c[0] == clean[-1][0]:
                    clean[-1] = c
                continue
            clean.append(c)

        groups: list[list[tuple[int, int, str]]] = []
        for c in clean:
            if groups:
                prev = groups[-1][-1]
                gap = text[prev[1]:c[0]]
                if "\n" not in gap and _SEP_RE.fullmatch(gap):
                    groups[-1].append(c)
                    continue
            groups.append([c])

        spans: list[EntitySpan] = []
        for g in groups:
            kinds = {c[2] for c in g}
            if len(g) < 2 and not (kinds & _STANDALONE):
                continue
            if kinds <= {"index"}:
                continue
            start, end = g[0][0], g[-1][1]
            surface = text[start:end]
            spans.append(
                EntitySpan(
                    kind=EntityKind.LOCATION,
                    start=start,
                    end=end,
                    text=surface,
                    normalized_key="addr:" + " ".join(surface.lower().replace(",", " ").split()),
                    priority=ADDRESS_PRIORITY,
                )
            )
        return spans
