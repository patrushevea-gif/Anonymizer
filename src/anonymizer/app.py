import sys

from PySide6.QtWidgets import QApplication

from anonymizer.gui.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Anonymizer")
    app.setOrganizationName("Anonymizer")
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
