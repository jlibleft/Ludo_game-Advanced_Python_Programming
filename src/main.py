"""Application entry point, separate from window construction."""

import sys
from collections.abc import Sequence

from src.application import create_application
from src.gui.main_window import MainWindow


def main(argv: Sequence[str] | None = None) -> int:
    """Show the main window and return Qt's event-loop exit code."""
    application = create_application(sys.argv if argv is None else argv)
    window = MainWindow()
    window.show()
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())
