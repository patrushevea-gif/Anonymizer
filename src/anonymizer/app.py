import logging
import multiprocessing
import os
import platform
import sys
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from anonymizer import __version__
from anonymizer.core.config import load_config
from anonymizer.gui.main_window import MainWindow
from anonymizer.gui.theme import apply_theme
from anonymizer.logging_setup import setup_logging

_COPYRIGHT_BANNER = (
    "ANONYMIZER ROSSILBER v{version} — © Patrushev E. All rights reserved. "
    "Proprietary software; unauthorized reproduction, modification, or "
    "redistribution is prohibited."
)


def _find_icon() -> Path | None:
    """Return the path to icon.ico whether we're frozen or running from source."""
    candidates: list[Path] = []
    if getattr(sys, "frozen", False):
        meipass = Path(getattr(sys, "_MEIPASS", "."))
        candidates.append(meipass / "assets" / "icon.ico")
        candidates.append(meipass / "icon.ico")
    here = Path(__file__).resolve().parent.parent.parent
    candidates.append(here / "assets" / "icon.ico")
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def _log_environment(log: logging.Logger) -> None:
    log.info("Anonymizer %s", __version__)
    log.info("Python %s on %s %s", sys.version.split()[0], platform.system(), platform.release())
    log.info("Frozen (PyInstaller): %s", getattr(sys, "frozen", False))
    if getattr(sys, "frozen", False):
        log.info("_MEIPASS: %s", getattr(sys, "_MEIPASS", "?"))
    for name in ("natasha", "pymorphy2", "pymorphy2_dicts_ru", "slovnet", "navec", "yargy"):
        try:
            module = __import__(name)
            path = getattr(module, "__file__", "<no file>")
            log.info("  %s -> %s", name, os.path.dirname(path) if path else "?")
        except ImportError as exc:
            log.warning("  %s NOT IMPORTABLE: %s", name, exc)


def _warmup_natasha(log: logging.Logger) -> None:
    """Pre-import natasha packages in the main thread.

    PyInstaller uses a custom importer with module-level locks. When the same
    package is first imported inside a worker thread, that thread can deadlock
    against Python's own import lock. Importing here — in the main thread,
    before any QThreads are created — populates sys.modules so worker-thread
    imports become instant cache hits with no lock contention.
    """
    for name in ("natasha", "navec", "slovnet", "pymorphy2", "razdel", "yargy",
                 "pymorphy2_dicts_ru", "dawg_python"):
        try:
            __import__(name)
            log.info("warmup import OK: %s", name)
        except ImportError as exc:
            log.warning("warmup import SKIP: %s — %s", name, exc)
        except Exception as exc:
            log.error("warmup import ERROR: %s — %s", name, exc)


def main() -> int:
    # Required for PyInstaller one-folder bundles that might spawn subprocesses
    multiprocessing.freeze_support()

    log_file = setup_logging()
    log = logging.getLogger(__name__)
    log.info("=" * 70)
    log.info(_COPYRIGHT_BANNER.format(version=__version__))
    log.info("=" * 70)
    log.info("=== Anonymizer starting, log file: %s ===", log_file)
    _log_environment(log)
    _warmup_natasha(log)

    config = load_config()

    app = QApplication(sys.argv)
    app.setApplicationName("Anonymizer ROSSILBER")
    app.setOrganizationName("Rossilber")
    app.setApplicationDisplayName("ANONYMIZER ROSSILBER")

    icon_path = _find_icon()
    if icon_path is not None:
        app.setWindowIcon(QIcon(str(icon_path)))
        log.info("App icon: %s", icon_path)

    apply_theme(app, config.theme)
    window = MainWindow(log_file=log_file)
    if icon_path is not None:
        window.setWindowIcon(QIcon(str(icon_path)))
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
