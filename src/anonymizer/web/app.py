"""WSGI application: JSON API + the single-page web interface.

Standard WSGI, so it runs under any production server (gunicorn, waitress,
uWSGI, mod_wsgi) or the built-in one (``python -m anonymizer.web``).

Routes (all API calls are ``POST`` with a JSON body, files as base64):

    GET  /                    web interface (index.html)
    GET  /api/health          {"status": "ok", "ner": bool, …}
    POST /api/anonymize       {text, options}                → result
    POST /api/remask          {text, spans, mapping, disabled} → result
    POST /api/restore         {text, mapping}                → {text}
    POST /api/file/open       {filename, file}               → {text, format}
    POST /api/docx/export     {file, spans, mapping}         → {file, report}
    POST /api/docx/restore    {file, mapping}                → {file, restored}

The server is stateless and never logs request contents.
"""
from __future__ import annotations

import json
import logging
import os
from importlib import resources

from anonymizer.web.service import AnonymizerService, ServiceError, decode_file

_log = logging.getLogger(__name__)

DEFAULT_MAX_BODY = 60 * 1024 * 1024  # 60 MB: a 40 MB .docx after base64

_SECURITY_HEADERS = [
    ("X-Content-Type-Options", "nosniff"),
    ("Referrer-Policy", "no-referrer"),
    # Personal data must never be cached by browsers or proxies.
    ("Cache-Control", "no-store"),
]
_PAGE_CSP = (
    "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; "
    "connect-src 'self'; img-src data: blob:; base-uri 'none'; form-action 'none'"
)


def _load_page() -> bytes:
    return resources.files("anonymizer.web").joinpath("static/index.html").read_bytes()


class AnonymizerWebApp:
    def __init__(
        self,
        service: AnonymizerService | None = None,
        *,
        max_body: int | None = None,
        cors_origin: str | None = None,
        frame_ancestors: str | None = None,
    ) -> None:
        self.service = service or AnonymizerService()
        self.max_body = max_body or int(os.environ.get("ANONYMIZER_MAX_BODY", DEFAULT_MAX_BODY))
        self.cors_origin = cors_origin or os.environ.get("ANONYMIZER_CORS_ORIGIN") or None
        # Which sites may embed the page in an <iframe>. Default: same origin.
        self.frame_ancestors = (
            frame_ancestors or os.environ.get("ANONYMIZER_FRAME_ANCESTORS") or "'self'"
        )
        self._page = _load_page()
        self._routes = {
            "/api/anonymize": self._anonymize,
            "/api/remask": self._remask,
            "/api/restore": self._restore,
            "/api/file/open": self._open,
            "/api/docx/export": self._docx_export,
            "/api/docx/restore": self._docx_restore,
        }

    # ------------------------------------------------------------ WSGI
    def __call__(self, environ, start_response):
        method = environ.get("REQUEST_METHOD", "GET").upper()
        path = environ.get("PATH_INFO", "/") or "/"
        try:
            if method == "OPTIONS":
                return self._respond(start_response, "204 No Content", b"", "text/plain")
            if method == "GET" and path in ("/", "/index.html"):
                headers = [
                    ("Content-Security-Policy",
                     f"{_PAGE_CSP}; frame-ancestors {self.frame_ancestors}"),
                ]
                return self._respond(
                    start_response, "200 OK", self._page, "text/html; charset=utf-8", headers
                )
            if method == "GET" and path == "/api/health":
                return self._json(start_response, 200, {"status": "ok", **self.service.capabilities()})
            handler = self._routes.get(path)
            if handler is None:
                return self._json(start_response, 404, {"error": "Не найдено"})
            if method != "POST":
                return self._json(start_response, 405, {"error": "Метод не поддерживается"})
            body = self._read_json(environ)
            return self._json(start_response, 200, handler(body))
        except ServiceError as exc:
            return self._json(start_response, exc.status, {"error": str(exc), **exc.payload})
        except Exception:
            # Never include request data in logs: only the traceback.
            _log.exception("Unhandled error on %s %s", method, path)
            return self._json(start_response, 500, {"error": "Внутренняя ошибка сервера"})

    # ------------------------------------------------------------ handlers
    def _anonymize(self, body: dict) -> dict:
        return self.service.anonymize(body.get("text", ""), body.get("options") or {})

    def _remask(self, body: dict) -> dict:
        return self.service.remask(
            body.get("text", ""), body.get("spans") or [], _mapping(body),
            [str(a) for a in body.get("disabled") or []],
        )

    def _restore(self, body: dict) -> dict:
        return self.service.restore_text(str(body.get("text", "")), _mapping(body))

    def _open(self, body: dict) -> dict:
        return self.service.open_file(str(body.get("filename", "")), decode_file(body.get("file", "")))

    def _docx_export(self, body: dict) -> dict:
        return self.service.export_docx(
            decode_file(body.get("file", "")), body.get("spans") or [], _mapping(body)
        )

    def _docx_restore(self, body: dict) -> dict:
        return self.service.restore_docx(decode_file(body.get("file", "")), _mapping(body))

    # ------------------------------------------------------------ plumbing
    def _read_json(self, environ) -> dict:
        try:
            length = int(environ.get("CONTENT_LENGTH") or 0)
        except ValueError:
            length = 0
        if length <= 0:
            raise ServiceError("Пустой запрос")
        if length > self.max_body:
            raise ServiceError(
                f"Слишком большой запрос (лимит {self.max_body // (1024 * 1024)} МБ)", status=413
            )
        raw = environ["wsgi.input"].read(length)
        try:
            data = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ServiceError("Некорректный JSON") from exc
        if not isinstance(data, dict):
            raise ServiceError("Ожидается JSON-объект")
        return data

    def _json(self, start_response, status: int, payload: dict):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        return self._respond(
            start_response, _STATUS.get(status, f"{status} Error"), body,
            "application/json; charset=utf-8",
        )

    def _respond(self, start_response, status: str, body: bytes, ctype: str, extra=None):
        headers = [("Content-Type", ctype), ("Content-Length", str(len(body)))]
        headers += _SECURITY_HEADERS
        if self.cors_origin:
            headers += [
                ("Access-Control-Allow-Origin", self.cors_origin),
                ("Access-Control-Allow-Methods", "GET, POST, OPTIONS"),
                ("Access-Control-Allow-Headers", "Content-Type"),
                ("Vary", "Origin"),
            ]
        headers += extra or []
        start_response(status, headers)
        return [body]


def _mapping(body: dict) -> dict:
    mapping = body.get("mapping")
    if not isinstance(mapping, dict):
        raise ServiceError("Нет таблицы псевдонимов (mapping). Сначала выполните обезличивание.")
    return mapping


_STATUS = {
    200: "200 OK",
    400: "400 Bad Request",
    404: "404 Not Found",
    405: "405 Method Not Allowed",
    413: "413 Payload Too Large",
    422: "422 Unprocessable Entity",
    500: "500 Internal Server Error",
}


def create_app(**kwargs) -> AnonymizerWebApp:
    """Factory for WSGI servers: ``gunicorn 'anonymizer.web.app:create_app()'``."""
    use_ner = os.environ.get("ANONYMIZER_USE_NER", "1") not in ("0", "false", "no")
    service = AnonymizerService(use_ner=use_ner)
    if os.environ.get("ANONYMIZER_PRELOAD", "1") not in ("0", "false", "no"):
        service.preload()
    return AnonymizerWebApp(service, **kwargs)
