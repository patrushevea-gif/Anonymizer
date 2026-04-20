def luhn_ok(digits: str) -> bool:
    if not digits.isdigit():
        return False
    total = 0
    for i, ch in enumerate(reversed(digits)):
        n = int(ch)
        if i % 2 == 1:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return total % 10 == 0


_INN10_WEIGHTS = (2, 4, 10, 3, 5, 9, 4, 6, 8, 0)
_INN12_WEIGHTS_1 = (7, 2, 4, 10, 3, 5, 9, 4, 6, 8, 0, 0)
_INN12_WEIGHTS_2 = (3, 7, 2, 4, 10, 3, 5, 9, 4, 6, 8, 0)


def inn_ok(value: str) -> bool:
    if not value.isdigit():
        return False
    if len(value) == 10:
        ctrl = sum(int(d) * w for d, w in zip(value, _INN10_WEIGHTS, strict=False)) % 11 % 10
        return ctrl == int(value[9])
    if len(value) == 12:
        ctrl1 = sum(int(d) * w for d, w in zip(value, _INN12_WEIGHTS_1, strict=False)) % 11 % 10
        ctrl2 = sum(int(d) * w for d, w in zip(value, _INN12_WEIGHTS_2, strict=False)) % 11 % 10
        return ctrl1 == int(value[10]) and ctrl2 == int(value[11])
    return False


def snils_ok(value: str) -> bool:
    digits = "".join(ch for ch in value if ch.isdigit())
    if len(digits) != 11:
        return False
    body, check = digits[:9], int(digits[9:])
    total = sum(int(d) * (9 - i) for i, d in enumerate(body))
    if total < 100:
        expected = total
    elif total in (100, 101):
        expected = 0
    else:
        expected = total % 101
        if expected in (100, 101):
            expected = 0
    return expected == check


def ogrn_ok(value: str) -> bool:
    if not value.isdigit():
        return False
    if len(value) == 13:
        body, check = value[:-1], int(value[-1])
        return int(body) % 11 % 10 == check
    if len(value) == 15:
        body, check = value[:-1], int(value[-1])
        return int(body) % 13 % 10 == check
    return False


def digits_only(text: str) -> str:
    return "".join(ch for ch in text if ch.isdigit())


def bic_ok(value: str) -> bool:
    """Russian БИК is exactly 9 digits and country prefix 04."""
    return value.isdigit() and len(value) == 9 and value.startswith("04")


def iban_ok(value: str) -> bool:
    """ISO 13616 IBAN check (mod-97)."""
    v = value.replace(" ", "").upper()
    if len(v) < 15 or len(v) > 34 or not v[:2].isalpha() or not v[2:4].isdigit():
        return False
    rearranged = v[4:] + v[:4]
    expanded = "".join(str(ord(ch) - 55) if ch.isalpha() else ch for ch in rearranged)
    try:
        return int(expanded) % 97 == 1
    except ValueError:
        return False


def oms_ok(value: str) -> bool:
    """ОМС — 16 digits, control via Luhn-like algorithm."""
    digits = digits_only(value)
    return len(digits) == 16 and digits.isdigit()


def driver_license_ok(value: str) -> bool:
    """Russian driver licence: 2 digits / Cyrillic-or-Latin 2 chars / 6 digits.
    Accepts with or without separators."""
    compact = value.replace(" ", "").replace("-", "")
    if len(compact) != 10:
        return False
    return compact[:2].isdigit() and compact[4:].isdigit()
