"""Organisations with an explicit legal form: ООО «…», АО "…", ИП Фамилия И.О.

NER often cuts a quoted company name before the closing quote or misses it
entirely when the name is made of ordinary words («Лаборатория Тестовых
Решений»). A legal-form prefix followed by a quoted name is unambiguous, so
it is matched by rule and always masked together with its quotes.
"""
from __future__ import annotations

import re

from anonymizer.core.entities import EntityKind, EntitySpan

ORG_PRIORITY = 30

_FORMS = (
    r"Общество\s+с\s+ограниченной\s+ответственностью|Публичное\s+акционерное\s+общество"
    r"|Непубличное\s+акционерное\s+общество|Закрытое\s+акционерное\s+общество"
    r"|Открытое\s+акционерное\s+общество|Акционерное\s+общество"
    r"|Индивидуальный\s+предприниматель|Федеральное\s+государственное\s+[а-яё]+\s+учреждение"
    r"|Государственное\s+[а-яё]+\s+учреждение|Автономная\s+некоммерческая\s+организация"
    r"|ООО|ОАО|ЗАО|ПАО|НПАО|НАО|АО|ГУП|МУП|ФГУП|ФГБУ|ФГБОУ|ФГАОУ|ГБУ|ГАУ|ГБОУ|МБОУ|МАОУ|МБУ"
    r"|НКО|АНО|ТОО|ОДО|ЧУП|НПО|НПП|НПФ|АКБ|КБ|ТД|СРО|LLC|Ltd\.?|Inc\.?|GmbH|JSC|PJSC|LLP"
)
_QUOTED = re.compile(
    rf"(?<![А-ЯЁа-яёA-Za-z])(?:{_FORMS})\s*"
    r"(?:«[^«»\n]{1,150}»|\"[^\"\n]{1,150}\"|“[^“”\n]{1,150}”|„[^„“\n]{1,150}“)"
)
_SOLE_TRADER = re.compile(
    r"(?<![А-ЯЁа-яёA-Za-z])(?:ИП|Индивидуальный\s+предприниматель)\s+"
    r"[А-ЯЁ][а-яё]+(?:-[А-ЯЁ][а-яё]+)?"
    r"(?:\s+[А-ЯЁ]\.\s?[А-ЯЁ]\.|\s+[А-ЯЁ][а-яё]+(?:\s+[А-ЯЁ][а-яё]+)?)"
)


class OrgDetector:
    def find(self, text: str) -> list[EntitySpan]:
        spans: list[EntitySpan] = []
        for pattern in (_QUOTED, _SOLE_TRADER):
            for m in pattern.finditer(text):
                surface = m.group()
                spans.append(
                    EntitySpan(
                        kind=EntityKind.ORG,
                        start=m.start(),
                        end=m.end(),
                        text=surface,
                        normalized_key="org:" + " ".join(surface.lower().split()),
                        priority=ORG_PRIORITY,
                    )
                )
        return spans
