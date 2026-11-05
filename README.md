# Ludo (Chińczyk) desktop

A Python desktop project for the Advanced Python Programming course.
Stage 1 provides the application foundation: a styled, resizable Qt window
and a QPainter surface reserved for the game board. Game rules, dice rolls,
playable pawns, AI, networking, and saved games are not implemented yet.

## Requirements and installation

Use **Python 3.11 or newer** with pip and virtual environment support.
The runtime uses PySide6 (Qt 6); tests use pytest. Dependencies and Python
constraints are declared in `pyproject.toml`. `requirements.txt` installs the
project in editable mode with its development dependencies from that source.

On Linux/macOS, from the repository root:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python main.py
```

On Windows (PowerShell):

```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python main.py
```

## Project structure

```text
.
├── main.py                 # Repository launcher
├── pyproject.toml          # Metadata, dependencies, packaging, pytest config
├── requirements.txt        # Editable install with development dependencies
├── README.md
├── .gitignore
├── src/
│   ├── __init__.py
│   ├── main.py             # Startup, window lifetime, Qt event loop
│   ├── application.py      # QApplication creation and application styling
│   ├── config.py           # Qt-independent application configuration
│   ├── core/
│   │   ├── __init__.py
│   │   ├── board.py        # Board model placeholder
│   │   ├── dice.py         # Dice placeholder
│   │   ├── game.py         # Engine placeholder
│   │   ├── pawn.py         # Pawn model placeholder
│   │   ├── player.py       # Player model placeholder
│   │   └── state.py        # Game state placeholder
│   ├── gui/
│   │   ├── __init__.py
│   │   ├── main_window.py  # Window and layout
│   │   ├── board_widget.py # QPainter board surface
│   │   └── styles.py       # Shared Qt stylesheet
│   └── ai/
│       └── __init__.py     # Reserved for future opponents
├── assets/
│   ├── images/.gitkeep
│   ├── sounds/.gitkeep
│   └── icons/.gitkeep
├── tests/
│   ├── conftest.py
│   └── test_application.py
├── Dockerfile             
├── docker-compose.yml      
└── .dockerignore           
```

## Tests

```bash
python -m pytest
```

## Linux environment troubleshooting

Qt's X11 backend needs native libraries in addition to the Python wheels.
If startup reports that the `xcb` plugin cannot load and
`libxcb-cursor.so.0` is missing, install the distribution's cursor library.
On Debian/Ubuntu:

```bash
sudo apt install libxcb-cursor0
```
