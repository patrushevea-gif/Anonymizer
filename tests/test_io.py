from pathlib import Path

import pytest


def test_txt_round_trip(tmp_path: Path) -> None:
    from anonymizer.io import read_text, write_text

    src = tmp_path / "sample.txt"
    src.write_text("Привет, мир!\nВторая строка.", encoding="utf-8")
    assert read_text(src).startswith("Привет, мир!")

    dst = tmp_path / "out.txt"
    write_text(dst, "Сохранено.")
    assert dst.read_text(encoding="utf-8") == "Сохранено."


def test_txt_cp1251_fallback(tmp_path: Path) -> None:
    from anonymizer.io import read_text

    src = tmp_path / "legacy.txt"
    src.write_bytes("Привет".encode("cp1251"))
    assert "Привет" in read_text(src)


def test_unsupported_suffix_raises(tmp_path: Path) -> None:
    from anonymizer.io import read_text, write_text
    from anonymizer.io.readers import UnsupportedFormatError as ReadErr
    from anonymizer.io.writers import UnsupportedFormatError as WriteErr

    bogus = tmp_path / "file.bin"
    bogus.write_bytes(b"\x00")
    with pytest.raises(ReadErr):
        read_text(bogus)
    with pytest.raises(WriteErr):
        write_text(bogus, "x")


def test_docx_round_trip(tmp_path: Path) -> None:
    pytest.importorskip("docx")
    from anonymizer.io import read_text, write_text

    dst = tmp_path / "out.docx"
    write_text(dst, "Первая строка\nВторая строка")
    text = read_text(dst)
    assert "Первая строка" in text
    assert "Вторая строка" in text


def test_xlsx_read(tmp_path: Path) -> None:
    openpyxl = pytest.importorskip("openpyxl")
    from anonymizer.io import read_text

    src = tmp_path / "data.xlsx"
    wb = openpyxl.Workbook()
    sheet = wb.active
    sheet.title = "Данные"
    sheet.append(["Имя", "Телефон"])
    sheet.append(["Иван", "+7 999 111 22 33"])
    wb.save(str(src))

    text = read_text(src)
    assert "Данные" in text
    assert "Иван" in text
    assert "+7 999 111 22 33" in text
