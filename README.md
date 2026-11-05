# Ludo (Chińczyk) desktop

A Python desktop project for the Advanced Python Programming course.
Provides a styled, resizable Qt window and a QPainter surface reserved
for the game board. Implements the game engine independently
of the GUI.

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
│   │   ├── board.py        # Logical routes, safe squares, move destinations
│   │   ├── dice.py         # Dice with an injectable random source
│   │   ├── exceptions.py   # Domain errors for invalid operations
│   │   ├── game.py         # GameEngine and legacy Game alias
│   │   ├── pawn.py         # Immutable pawn identity and logical progress
│   │   ├── player.py       # Colors, starting offsets, and pawn ownership
│   │   └── state.py        # Validated immutable game snapshot
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
│   ├── test_application.py
│   ├── test_dice.py
│   ├── test_engine.py
│   └── test_models.py
├── Dockerfile            
├── docker-compose.yml     
└── .dockerignore          
```

## Game engine

- `GameEngine` owns the current snapshot and orchestrates rolls, legal moves,
  captures, automatic turn changes, bonus rolls, victory, and reset.
- `GameState`, `Player`, and `Pawn` are frozen dataclasses. Rosters and pawn
  collections are tuples, so callers cannot change live state through them.
  Each successful action replaces the snapshot; previous snapshots remain valid.
- `Board` centralizes logical destinations and shared-track coordinate mapping.
  It contains no graphical geometry. Legal-move discovery and actual moves
  use the same destination calculation.
- `Dice` accepts a `RandomSource` with `randint(a, b)`. By default it uses its
  own `random.Random`; tests can inject a seeded or scripted source.
- `exceptions.py` defines `GameError` and specific errors for invalid setup,
  moves, rolls, turn phases, and actions after victory.

### Coordinates and rules

Every pawn has a zero-based ID (0–3) within its owner and a `progress` value:

| Progress | Meaning |
| --- | --- |
| -1 | In the player's base |
| 0–51 | Moving on the shared track |
| 52–56 | In the player's private home stretch |
| 57 | Finished; cannot move again |

Games have 2–4 distinct colors and four pawns per player, initially in base.
The first listed color starts. A 6 releases a base pawn to progress 0; otherwise
an unfinished pawn advances by the rolled number. Progress 51 leads into the
private home stretch. Reaching 57 requires an exact roll; overshoots are illegal.

Landing on an unsafe square sends **all opposing pawns on that square** back
to base. Passing over pawns does not capture them. Safe squares allow opposing
pawns to coexist, friendly pawns may stack anywhere, and stacks never block
movement. Captures and finishing individual pawns do not give bonus rolls.

Rolling a 6 gives another roll after the chosen move, with no penalty for
repeated sixes. An unplayable non-six automatically passes the turn; an
unplayable six leaves the same player ready to roll again. A pending playable
roll must be used before rolling again. The first player to finish all four
pawns wins, immediately ending the game even if the winning roll was a 6.


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
