import logging
import os
import platform
import sys

from PySide6.QtWidgets import QApplication

from anonymizer import __version__
from anonymizer.gui.main_window import MainWindow
from anonymizer.logging_setup import setup_logging


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


def main() -> int:
    log_file = setup_logging()
    log = logging.getLogger(__name__)
    log.info("=== Anonymizer starting, log file: %s ===", log_file)
    _log_environment(log)

    app = QApplication(sys.argv)
    app.setApplicationName("Anonymizer")
    app.setOrganizationName("Anonymizer")
    window = MainWindow(log_file=log_file)
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
