"""Application entry point, separate from window construction."""

import sys
from collections.abc import Sequence

from Ludo.application import create_application
from Ludo.core.game import GameEngine
from Ludo.gui.main_window import MainWindow

__all__ = ("main",)


def main(argv: Sequence[str] | None = None) -> int:
    """Show the desktop window and run the Qt event loop.

    Args:
        argv: Command-line arguments, including the program name. Uses
            sys.argv when None.

    Returns:
        The Qt event-loop exit code, normally 0 on successful shutdown.
    """
    application = create_application(sys.argv if argv is None else argv)
    engine = GameEngine()
    window = MainWindow(engine=engine)
    window.show()
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())
