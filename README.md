# Ludo (Chińczyk) desktop

A Python desktop project for the Advanced Python Programming course.
Provides a styled, resizable Qt window and a QPainter surface reserved
for the game board. Implements the game engine independently
of the GUI.

## Requirements and installation

Use **Python 3.11 or newer** and [uv](https://docs.astral.sh/uv/getting-started/installation/).
The runtime uses PySide6 (Qt 6); development tools are pytest and Ruff.
Dependencies and tool settings are declared in `pyproject.toml`. The committed
`uv.lock` records exact dependency versions for reproducible environments.

From the repository root, on Linux, macOS, or Windows:

```bash
uv sync --locked
uv run --locked python tools/configure_cache.py
uv run --locked ludo
```

`uv sync` creates `.venv`, installs the project in editable mode, and includes
the `dev` dependency group containing pytest and Ruff. `uv run` runs a command
in that environment, so manual activation is unnecessary. The alternative
application entry point is `uv run --locked python -m Ludo.main`.

The `--locked` flag rejects outdated lockfiles instead of silently changing
them. After intentionally changing dependencies, run `uv lock` and
`uv sync --locked`, then commit both `pyproject.toml` and `uv.lock`.

## Development commands

```bash
uv run --locked pytest
uv run --locked ruff check .
uv run --locked ruff format --check .
```

[Ruff](https://docs.astral.sh/ruff/configuration/) checks more than formatting.
The selected rule families are:

| Rules | What they check |
| --- | --- |
| `E4`, `E7`, `E9`, `F` | Essential style, invalid syntax, undefined and unused names |
| `I` | Import ordering |
| `B` | Common bugs and suspicious constructs |
| `UP` | Modern syntax supported by Python 3.11 |
| `SIM`, `C4`, `RET` | Simplifications, comprehensions, and return statements |
| `N`, `A` | Naming conventions and shadowing Python builtins |
| `SLF` | Access to another object's private members |
| `D`, `ANN` | Google-style docstrings and function type annotations |
| `PT` | Consistent pytest usage |
| `RUF` | Additional Ruff-specific checks |

The formatter uses double quotes, spaces, and a 79-character line length.
Generated files under `.cache` are excluded. Narrow naming exceptions preserve
the existing `Ludo` package path and Qt's required `sizeHint`/`paintEvent` names.
Empty package markers do not require package docstrings.

Ruff checks naming conventions, but meaningful names still need human review.
Use descriptive names such as `lower_bound`, `upper_bound`, and `pawn_id`
rather than single letters.

Apply supported lint fixes and formatting with:

```bash
uv run --locked ruff check --fix .
uv run --locked ruff format .
```

Review automatic changes before committing. To add dependencies:

```bash
uv add package-name
uv add --dev development-tool-name
```

These commands update the project configuration, lockfile, and environment.
Use the Ruff extension in your editor if you want lint feedback and formatting
on save, and select this project's `.venv` as the Python interpreter.

## Generated files

Generated files have one ignored home: `.cache/`.

```text
.cache/
├── python/       # Python bytecode, with source-path subdirectories
├── pytest/       # pytest cache
├── pip/          # Cache for optional direct pip usage
├── uv/           # uv download and build cache
├── dist/         # Source archives and wheels built with the command below
├── coverage/     # Coverage data and reports, if coverage is used
└── ruff/         # Ruff cache
```

Run `uv run --locked python tools/configure_cache.py` after creating the project's
virtual environment. It installs a small startup configuration inside it
so subsequent Python processes automatically write bytecode to `.cache/python`.
It also configures that environment's pip cache. It can be run again safely;
repeat it if the environment is recreated or the checkout is moved. Restart
any already-running Python console or debug session to pick up the setting.

Select this project's `.venv` interpreter in the IDE so editor runs use the
same configuration. A different interpreter needs its own configuration, or
the `PYTHONPYCACHEPREFIX` environment variable pointing to `.cache/python`.

The pytest, Ruff, uv, and optional coverage paths are configured in
`pyproject.toml`. Package builds use the
[uv build backend](https://docs.astral.sh/uv/concepts/build-backend/), declared
in `[build-system]`; there is no `setup.py` or setuptools customization.
The backend's module configuration preserves the `src/Ludo` layout.
Choose an output directory explicitly for tools that accept one, for example:

```bash
uv build --out-dir .cache/dist
```

This builds a Python source archive and wheel, not a standalone desktop
executable. uv keeps build work in its cache. Source distributions include
tests, the cache configuration helper, and the lockfile; generated cache and
environment directories are excluded. Old `.cache/packaging` or `.cache/build`
folders from earlier setuptools builds can be deleted.

The entire `.cache` directory is disposable; tools recreate what they need.
The virtual environment remains in `.venv`, and Git/editor settings retain
their normal locations. These are environment and project settings rather
than disposable tool caches.

## Project structure

```text
.
├── pyproject.toml        # Metadata, dependencies, packaging, pytest config
├── uv.lock               # Exact dependency versions; commit this file
├── tools/
│   └── configure_cache.py # One-time cache configuration for the project venv
├── .cache/               # Generated files; ignored by Git
├── README.md
├── .gitignore
├── src/
│   └── Ludo/               # Main module
│       ├── __init__.py         # Empty package marker
│       ├── main.py             # Startup, window lifetime, Qt event loop
│       ├── application.py      # QApplication creation and application styling
│       ├── config.py           # Qt-independent application configuration
│       ├── core/
│       │   ├── __init__.py     # Empty package marker
│       │   ├── board.py        # Logical routes, safe squares, move destinations
│       │   ├── dice.py         # Dice with an injectable random source
│       │   ├── exceptions.py   # Domain errors for invalid operations
│       │   ├── game.py         # GameEngine and legacy Game alias
│       │   ├── pawn.py         # Immutable pawn identity and logical progress
│       │   ├── player.py       # Colors, starting offsets, and pawn ownership
│       │   └── state.py        # Validated immutable game snapshot
│       ├── gui/
│       │   ├── __init__.py     # Empty package marker
│       │   ├── main_window.py  # Window and layout
│       │   ├── board_widget.py # QPainter board surface
│       │   └── styles.py       # Shared Qt stylesheet
│       └── ai/
│           └── __init__.py     # Empty marker; opponents are a future stage
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
```

## Game engine

- Package `__init__.py` files are empty. Import directly from the module
  defining a class, for example `from Ludo.core.game import GameEngine` or
  `from Ludo.core.player import PlayerColor`. Importing `Ludo.core` by itself
  does not load the engine or Qt.
- `GameEngine` owns the current snapshot and orchestrates rolls, legal moves,
  captures, automatic turn changes, bonus rolls, victory, and reset.
- `GameState`, `Player`, and `Pawn` are frozen dataclasses. Rosters and pawn
  collections are tuples, so callers cannot change live state through them.
  Each successful action replaces the snapshot; previous snapshots remain valid.
- `Board` centralizes logical destinations and shared-track coordinate mapping.
  It contains no graphical geometry. Legal-move discovery and actual moves
  use the same destination calculation.
- `Dice` accepts a `RandomSource` with
  `randint(lower_bound, upper_bound, /)`. The `/` declares positional-only
  bounds, allowing generators such as `random.Random` to use their own
  parameter names. By default Dice creates its own random generator; tests
  can inject one with `Dice(random_source=source)`.
- `exceptions.py` defines `GameError` and specific errors for invalid setup,
  moves, rolls, turn phases, and actions after victory.

### Public and internal names

Each implementation module declares a tuple named `__all__` listing its
intended public names. For example, `Ludo.core.dice` exposes `Dice` and
`RandomSource`. Use explicit imports instead of wildcard imports.

A single leading underscore marks an internal detail: `GameEngine._state`,
`Dice._random_source`, validation helpers, and test-only helpers. External
callers should use `engine.state`, `engine.active_player`, and the public
roll/move methods. Internal winner-validation data is private; the public
`winner` field/property reports the actual winner.

These conventions are not enforced access permissions: `__all__` controls
wildcard exports, and `_name` asks callers to treat a name as internal.
Frozen dataclasses, tuple collections, and read-only engine properties prevent
ordinary direct mutation of the live game snapshot. Double-leading-underscore
name mangling is unnecessary here. Player colors use Python 3.11's `StrEnum`,
whose string values are the lowercase color names.

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
uv run --locked pytest
```

## Linux environment troubleshooting

Qt's X11 backend needs native libraries in addition to the Python wheels.
If startup reports that the `xcb` plugin cannot load and
`libxcb-cursor.so.0` is missing, install the distribution's cursor library.
On Debian/Ubuntu:

```bash
sudo apt install libxcb-cursor0
```
