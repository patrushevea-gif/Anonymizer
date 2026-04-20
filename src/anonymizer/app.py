import logging
import sys

from PySide6.QtWidgets import QApplication

from anonymizer.gui.main_window import MainWindow
from anonymizer.logging_setup import setup_logging


def main() -> int:
    log_file = setup_logging()
    logging.getLogger(__name__).info("Anonymizer starting, log file: %s", log_file)

    app = QApplication(sys.argv)
    app.setApplicationName("Anonymizer")
    app.setOrganizationName("Anonymizer")
    window = MainWindow(log_file=log_file)
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
