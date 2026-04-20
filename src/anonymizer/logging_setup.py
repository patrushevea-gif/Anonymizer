import logging
import os
import sys
from pathlib import Path


def log_dir() -> Path:
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or str(Path.home())
        return Path(base) / "Anonymizer" / "logs"
    return Path.home() / ".local" / "share" / "anonymizer" / "logs"


def setup_logging() -> Path:
    directory = log_dir()
    directory.mkdir(parents=True, exist_ok=True)
    log_file = directory / "anonymizer.log"

    root = logging.getLogger()
    if any(
        isinstance(h, logging.FileHandler)
        and Path(getattr(h, "baseFilename", "")) == log_file
        for h in root.handlers
    ):
        return log_file

    handler = logging.FileHandler(log_file, mode="a", encoding="utf-8")
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    )
    root.addHandler(handler)
    root.setLevel(logging.INFO)
    return log_file
