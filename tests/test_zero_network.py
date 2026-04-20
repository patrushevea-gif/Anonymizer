import importlib
import pkgutil
import socket
from pathlib import Path

import pytest

SRC_ROOT = Path(__file__).resolve().parent.parent / "src" / "anonymizer"

FORBIDDEN_MODULES = (
    "requests",
    "httpx",
    "aiohttp",
    "urllib3",
    "urllib.request",
    "urllib.error",
    "http.client",
    "xmlrpc.client",
    "ftplib",
    "telnetlib",
    "smtplib",
    "poplib",
    "imaplib",
)


def _imports_module(source: str, module: str) -> bool:
    patterns = (
        f"import {module}\n",
        f"import {module} ",
        f"import {module}.",
        f"from {module} import",
        f"from {module}.",
    )
    return any(pat in source for pat in patterns)


def test_no_forbidden_network_imports_in_source():
    offenders: list[tuple[str, str]] = []
    for path in SRC_ROOT.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for module in FORBIDDEN_MODULES:
            if _imports_module(text, module):
                offenders.append((str(path.relative_to(SRC_ROOT)), module))
    assert not offenders, (
        "Network libraries are forbidden in runtime code. Offenders: " + repr(offenders)
    )


@pytest.fixture
def trace_connections(monkeypatch):
    calls: list[tuple] = []
    original = socket.create_connection

    def traced(address, *args, **kwargs):
        calls.append(address)
        return original(address, *args, **kwargs)

    monkeypatch.setattr(socket, "create_connection", traced)
    return calls


def test_core_imports_do_not_touch_network(trace_connections):
    import anonymizer

    for info in pkgutil.walk_packages(anonymizer.__path__, prefix="anonymizer."):
        if info.name.startswith("anonymizer.gui"):
            continue
        importlib.import_module(info.name)

    assert trace_connections == [], (
        f"Unexpected network activity during imports: {trace_connections}"
    )


def test_core_operations_do_not_touch_network(trace_connections):
    from anonymizer.core.entities import EntityKind, EntitySpan
    from anonymizer.core.mapping import MappingStore
    from anonymizer.core.masking import apply_mask
    from anonymizer.core.pipeline import anonymize
    from anonymizer.core.reverse import restore

    store = MappingStore()
    result = anonymize("Иванов Иван +7 999 111 22 33", store)
    spans = [EntitySpan(EntityKind.PHONE, 0, 3, "foo")]
    apply_mask("foo bar", spans, store)
    restore(result.masked_text, store)

    assert trace_connections == []
