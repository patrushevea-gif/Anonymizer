"""Web wrapper: WSGI API over the same engine, stateless, verified exports."""
import base64
import io
import json
import zipfile
from pathlib import Path

import pytest

from anonymizer.web.app import AnonymizerWebApp
from anonymizer.web.service import AnonymizerService

FIXTURE = Path(__file__).parent / "fixtures" / "acceptance_test_1.docx"


@pytest.fixture(scope="module")
def app():
    return AnonymizerWebApp(AnonymizerService(use_ner=False), max_body=5 * 1024 * 1024)


def call(app, method, path, body=None):
    raw = b"" if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
    environ = {
        "REQUEST_METHOD": method, "PATH_INFO": path, "CONTENT_LENGTH": str(len(raw)),
        "wsgi.input": io.BytesIO(raw),
    }
    captured = {}

    def start_response(status, headers):
        captured["status"] = int(status.split()[0])
        captured["headers"] = dict(headers)

    out = b"".join(app(environ, start_response))
    ctype = captured["headers"]["Content-Type"]
    data = json.loads(out) if ctype.startswith("application/json") else out
    return captured["status"], captured["headers"], data


def test_page_served_with_strict_csp(app) -> None:
    status, headers, page = call(app, "GET", "/")
    assert status == 200 and b"ANONYMIZER ROSSILBER" in page
    csp = headers["Content-Security-Policy"]
    assert "default-src 'none'" in csp and "connect-src 'self'" in csp
    assert headers["Cache-Control"] == "no-store"


def test_health(app) -> None:
    status, _, data = call(app, "GET", "/api/health")
    assert status == 200 and data["status"] == "ok" and "ФИО" in data["kinds"]


def test_text_anonymize_remask_restore(app) -> None:
    text = "Иванов Иван Иванович, тел. +7 916 123-45-67, ИНН 7707083893. Иванов И.И. подписал."
    status, _, res = call(app, "POST", "/api/anonymize", {"text": text, "options": {}})
    assert status == 200
    assert "+7 916 123-45-67" not in res["masked_text"]
    assert "Иванов И.И." not in res["masked_text"]
    phone_alias = next(s["alias"] for s in res["spans"] if s["kind"] == "ТЕЛ")

    status, _, re_res = call(app, "POST", "/api/remask", {
        "text": text, "spans": res["spans"], "mapping": res["mapping"], "disabled": [phone_alias],
    })
    assert status == 200 and "+7 916 123-45-67" in re_res["masked_text"]
    assert "7707083893" not in re_res["masked_text"]

    status, _, back = call(app, "POST", "/api/restore", {"text": res["masked_text"], "mapping": res["mapping"]})
    assert status == 200 and back["text"] == text


def test_manual_marking_masks_every_occurrence(app) -> None:
    text = "Проект «Альтаир» стартует. Бюджет проекта Альтаир утверждён."
    start = text.index("Альтаир")
    status, _, res = call(app, "POST", "/api/anonymize", {
        "text": text, "options": {"manual": [{"start": start, "end": start + 7, "kind": "ОРГ"}]},
    })
    assert status == 200 and "Альтаир" not in res["masked_text"]


def test_options_disable_kinds_and_allowlist(app) -> None:
    text = "Поставщик ООО «Россильбер», тел. +7 916 123-45-67"
    _, _, res = call(app, "POST", "/api/anonymize", {
        "text": text, "options": {"disabled_kinds": ["ТЕЛ"], "allowlist": ["Россильбер"]},
    })
    assert res["masked_text"] == text


def test_docx_full_cycle_matches_desktop_engine(app) -> None:
    pytest.importorskip("natasha")
    b64 = base64.b64encode(FIXTURE.read_bytes()).decode()
    status, _, opened = call(app, "POST", "/api/file/open", {"filename": "test.docx", "file": b64})
    assert status == 200 and opened["format"] == "docx" and "[Верхний колонтитул]" in opened["text"]

    _, _, res = call(app, "POST", "/api/anonymize", {"text": opened["text"], "options": {}})
    status, _, exp = call(app, "POST", "/api/docx/export",
                          {"file": b64, "spans": res["spans"], "mapping": res["mapping"]})
    assert status == 200, exp
    assert exp["report"]["leaks"] == [] and exp["report"]["replaced"] >= 50
    out = base64.b64decode(exp["file"])
    with zipfile.ZipFile(io.BytesIO(out)) as zf:
        everything = "".join(zf.read(n).decode("utf-8", "replace") for n in zf.namelist()
                             if n.endswith(".xml"))
    for secret in ("Павлов Алексей Сергеевич", "header-qa@example.invalid", "Степанов Денис Львович",
                   "metapii@example.invalid", "+7 (999) 120-45-67"):
        assert secret not in everything

    status, _, back = call(app, "POST", "/api/docx/restore", {"file": exp["file"], "mapping": res["mapping"]})
    assert status == 200 and back["restored"] >= 50
    from anonymizer.io.ooxml import DocxDocument

    assert DocxDocument(base64.b64decode(back["file"])).text == opened["text"]


def test_tampered_spans_rejected(app) -> None:
    text = "тел. +7 916 123-45-67"
    _, _, res = call(app, "POST", "/api/anonymize", {"text": text, "options": {}})
    spans = [dict(s, start=s["start"] + 1) for s in res["spans"]]
    status, _, err = call(app, "POST", "/api/remask",
                          {"text": text, "spans": spans, "mapping": res["mapping"], "disabled": []})
    assert status == 400 and "не совпадают" in err["error"]


def test_errors_are_json(app) -> None:
    assert call(app, "POST", "/api/anonymize", {"text": "  "})[0] == 400
    assert call(app, "GET", "/api/anonymize")[0] == 405
    assert call(app, "GET", "/nope")[0] == 404
    assert call(app, "POST", "/api/file/open", {"filename": "x.exe", "file": "AAAA"})[0] == 400
    assert call(app, "POST", "/api/restore", {"text": "x"})[0] == 400


def test_body_limit(app) -> None:
    big = {"text": "a" * (6 * 1024 * 1024)}
    assert call(app, "POST", "/api/anonymize", big)[0] == 413
