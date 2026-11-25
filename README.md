# Ludo (Chińczyk) desktop

A Python desktop project for the Advanced Python Programming course.
Stages 1–4 provide a playable local game for 2–4 human players, a complete
GUI-independent game engine, and a resizable QPainter board. Players share
one computer, roll the die, and click highlighted pawns. Animations, AI,
persistence, networking, and executable distribution belong to later stages.

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

## Playing a game

1. The application starts with four players. To play with two or three, select
   the number under **Players for New Game**, then press **New Game**.
2. The right sidebar shows the active player, player colors, finished-pawn
   counts, the last dice result and its owner, and the current action prompt.
3. Press **Roll Dice**, then left-click a pawn with a gold ring. The button
   remains disabled until the required move is completed. Even if only one
   pawn can move, choose it by clicking.
4. The board updates immediately. A dark outline marks the pawn just moved.
   Captures, bonus rolls, and player changes are explained in the status text.
   An unplayable roll automatically passes the turn, or keeps the extra roll
   after a six.
5. The first player to finish four pawns receives a victory notification.
   Dismiss it with **OK**, then use **New Game** to play again. New Game can
   also immediately restart an unfinished game.

Changing the player count takes effect only when New Game is pressed. New
rosters use Red, Blue, Green, Yellow in that order; restarting with the same
count preserves the current colors and order. Smaller windows provide a
scrollable sidebar so all controls remain accessible.

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
├── AGENTS.md             # Architecture, conventions, and stage boundaries
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
│       │   ├── main_window.py  # Layout, signal wiring, victory notification
│       │   ├── game_controller.py # Engine actions and presentation feedback
│       │   ├── game_sidebar.py # Turn information and control intent signals
│       │   ├── board_widget.py # QPainter board and legal pawn hit testing
│       │   ├── board_geometry.py # Grid mapping, transforms, pawn placement
│       │   ├── pawn_renderer.py # Numbered token artwork
│       │   └── styles.py       # Shared palette and Qt stylesheet
│       └── ai/
│           └── __init__.py     # Empty marker; opponents are a future stage
├── assets/
│   ├── images/.gitkeep
│   ├── sounds/.gitkeep
│   └── icons/.gitkeep
├── tests/
│   ├── conftest.py
│   ├── test_application.py
│   ├── test_board_geometry.py
│   ├── test_board_widget.py
│   ├── test_dice.py
│   ├── test_engine.py
│   ├── test_game_interaction.py
│   └── test_models.py        
```

## Graphical board

The board uses a 15 × 15 logical grid. Four 6 × 6 bases surround a three-cell
wide cross containing 52 shared cells, 20 private home-stretch cells, and the
central 3 × 3 finishing area. Colored stars mark the four safe starting cells;
arrows point down each player's home stretch toward the finish.

`board_geometry.py` centralizes coordinates independently of Qt. Grid cells
are `(row, column)` pairs; continuous drawing points are `(column, row)`.
`BoardGeometry(width, height)` computes a centered square viewport and converts
grid coordinates into pixels. Logical progress maps through the engine's
`Board.shared_position()`, so each player's offset and wraparound stay aligned
with the rules.

The zero-based starting cells and private routes are:

| Color | Base | Offset | Start cell | Home stretch, in order |
| --- | --- | --- | --- | --- |
| Red | Upper-left | 0 | `(6, 0)` | `(7, 1)` through `(7, 5)` |
| Blue | Upper-right | 13 | `(0, 8)` | `(1, 7)` through `(5, 7)` |
| Green | Lower-right | 26 | `(8, 14)` | `(7, 13)` through `(7, 9)` |
| Yellow | Lower-left | 39 | `(14, 6)` | `(13, 7)` through `(9, 7)` |

Starts occupy the outer entry corners of the cross. This lets a pawn visit
all 52 shared cells and then enter its five-cell home stretch from an adjacent
cell, preserving the engine's progress range without skipping a shared cell.
Base pawns use four dedicated stations per color. Finished pawns use separate
slots inside their color's central triangle.

`BoardWidget` renders a snapshot with QPainter and anti-aliasing. It draws
rounded bases and cells, safe stars, lane arrows, and the finish; `PawnRenderer`
adds numbered tokens, subtle shadows, and highlights. All player colors and
pastel tints are shared through `styles.py`.

Startup creates a `GameEngine` and passes that engine to
`MainWindow(engine=engine)`. Only participating players' pawns are drawn;
all four board quadrants remain visible.

Co-occupying pawns are laid out as distinct smaller circles inside their cell,
including mixed-color safe-square stacks of up to 16 pawns. Resizing recomputes
the transform and token radii together. `cell_at()` and `PawnPlacement.contains()`
provide the same geometry for painting and mouse hit testing. Only an active
player's engine-approved pawn circles emit clicks. Available pawns have gold
rings and a pointing cursor; the last accepted selection has a dark outline.

## GUI integration

`GameController` owns the engine and routes roll, move, and new-game actions
through its public methods. The engine alone decides legal moves, captures,
extra rolls, turn changes, and winners. The controller compares accepted
snapshots to describe captures, retains the last die result and its owner,
and emits `updated` and `game_won` Qt signals. Rejected actions leave the
snapshot and displayed die unchanged and produce a readable status message.

`GameSidebar` displays controller data and emits control intents.
`BoardWidget` displays an immutable snapshot, highlights the legal IDs supplied
by the controller, and emits `pawn_clicked(color, pawn_id)`. It never moves
pawns itself. `MainWindow` connects these signals and refreshes the board,
sidebar, and input permissions together after every action. A non-blocking,
window-modal Qt message box announces victory, and rolling stays disabled
until a new game is started.

For normal play, use `window.controller.roll_dice()`,
`window.controller.move_pawn("red", pawn_id)`, or
`window.controller.new_game()`. Tests can inject an engine with a scripted die
using `MainWindow(engine=engine)`. The existing `MainWindow(state=snapshot)`
and `window.set_state(snapshot)` APIs load a validated snapshot as the playable
game with a fresh default die; they update controls and board together.
`BoardWidget.set_state()` remains a rendering-only API for standalone boards.

## Game engine

- Package `__init__.py` files are empty. Import directly from the module
  defining a class, for example `from Ludo.core.game import GameEngine` or
  `from Ludo.core.player import PlayerColor`. Importing `Ludo.core` by itself
  does not load the engine or Qt.
- `GameEngine` owns the current snapshot and orchestrates rolls, legal moves,
  captures, automatic turn changes, bonus rolls, victory, and reset.
  Its read-only `can_roll` property exposes the current rolling permission.
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

### Understanding the source files and classes

Start reading with `src/Ludo/main.py`. Its `main()` function creates the Qt
application, creates the engine, shows `MainWindow`, and starts the event loop.
The event loop waits for input and paint requests until the last window closes.

`application.py` contains `create_application(argv)`. It creates the single
`QApplication` and applies the Fusion theme and stylesheet from `gui/styles.py`.
It does not start a game or construct a board. `config.py` contains
`ApplicationConfig`, a small dataclass storing the title and window sizes;
`APP_CONFIG` is the shared instance. These settings do not depend on Qt.

The core files contain the game data and rules:

| File and class | Main data | Responsibility and important methods |
| --- | --- | --- |
| `core/pawn.py`: `Pawn` | `id`, `progress` | Represents one token. `in_base` and `finished` report its position. `Board` validates progress. It does not move itself. |
| `core/player.py`: `PlayerColor` | Red, Blue, Green, Yellow string values | Keeps the four color names and their order consistent across the engine and GUI. |
| `core/player.py`: `Player` | `color`, four `pawns` | Owns a tuple of pawns. `starting_offset` identifies its track entrance; `has_won` checks whether all four pawns finished. Uses `Pawn` and `Board`. |
| `core/state.py`: `GameState` | `players`, `active_player_index`, `pending_roll`, `winner` | Stores one complete game snapshot. `active_player` reads the current player. `__post_init__()` rejects invalid rosters, turn phases, winners, and unsafe opposing stacks using `Board` and the models. |
| `core/board.py`: `Board` | Constants such as `BASE`, `TRACK_LENGTH`, `FINISH`, and `SAFE_SQUARES` | Centralizes movement calculations. `destination()` returns the allowed progress or None; `shared_position()` converts progress to an absolute square. The engine and geometry reuse these calculations. |
| `core/dice.py`: `Dice` | Internal `_random_source` | `roll()` asks the source for an integer from 1 to 6 and validates it through `Board`. Each ordinary die owns a `random.Random` instance. |
| `core/dice.py`: `RandomSource` | No stored data | A `Protocol` describing the one method a dice source must provide: `randint()`. It lets tests supply known results. It is a type description, not another random generator. |
| `core/game.py`: `GameEngine` | Internal `_state` and `_dice` | Owns the current snapshot. `roll_dice()`, `legal_moves()`, and `move_pawn()` handle a turn. `new_game()` changes the roster; `reset()` retains it. `from_state()` starts from a validated scenario. `state`, `active_player`, `winner`, and `can_roll` are read-only properties. |
| `core/exceptions.py`: domain exceptions | Error messages | `GameError` is the common base. `InvalidSetupError`, `InvalidMoveError`, `InvalidRollError`, and `InvalidTurnError` identify rejected operations. `GameOverError` is an `InvalidTurnError` for actions after victory. The controller catches `GameError` to display feedback. |

`Game` in `core/game.py` is an older name for `GameEngine`, not a second
implementation. Keeping the alias preserves the existing public import.

The GUI files turn input into engine calls and snapshots into pictures:

| File and class | Main data | Responsibility and important methods |
| --- | --- | --- |
| `gui/game_controller.py`: `GameController(QObject)` | `_engine`, `_last_roll`, `_last_roller`, `_selected_pawn`, `_message` | Handles `roll_dice()`, `move_pawn()`, `new_game()`, and `load_state()`. Calls the engine and prepares feedback. `updated` tells the window to refresh; `game_won` requests the victory dialog. |
| `gui/main_window.py`: `MainWindow(QMainWindow)` | Controller, `board_widget`, sidebar, victory dialog | Builds the layout and connects signals. `_refresh_view()` updates all views together; `_start_new_game()` applies the selected count; `_announce_winner()` opens the dialog. `set_state()` loads a playable scenario through the controller. |
| `gui/game_sidebar.py`: `GameSidebar(QFrame)` | Labels, buttons, player-count selector | `set_turn()` displays controller data and enables the die button. `selected_player_count` reads the next roster size. Button presses emit `roll_requested` or `new_game_requested`; this widget does not change game data. |
| `gui/board_widget.py`: `BoardWidget(QWidget)` | `_state`, allowed pawn IDs, last selected pawn, renderer | `paintEvent()` paints the board. `mousePressEvent()` checks pawn circles and emits `pawn_clicked`. `mouseMoveEvent()` updates the cursor and tooltip. `set_state()`, `set_available_moves()`, and `set_selected_pawn()` supply display data. |
| `gui/board_geometry.py`: `BoardGeometry` | Viewport `width`, `height`, `padding`; fixed grid coordinates | Converts grid cells to pixels using `point()` and `cell_center()`. `cell_for()` maps logical progress; `pawn_placements()` lays out all tokens, including stacks. `cell_at()` performs the inverse pixel-to-cell conversion. No Qt or move decisions are involved. |
| `gui/board_geometry.py`: `PawnPlacement` | Owner color, pawn ID, center, radius | Records one visible pawn circle. `contains()` checks a mouse point against that same circle, keeping drawing and selection aligned. |
| `gui/pawn_renderer.py`: `PawnRenderer` | No persistent data | `paint()` draws numbered tokens and their move/selection outlines at the supplied placements. It knows how to draw tokens, not how they move. |

`gui/styles.py` contains the shared player palettes and Qt stylesheet. The
board, renderer, sidebar, and application all read those definitions, so they
use the same colors and fonts.

The four `__init__.py` files in `Ludo/`, `core/`, `gui/`, and `ai/` are empty
package markers. They perform no imports or initialization.
The `ai` package contains no opponent implementation.

`tools/configure_cache.py` is a setup script, not part of a game turn.
`configure_cache()` writes a small `.pth` startup file into this project's
virtual environment and configures its pip cache. Python then sends bytecode
to `.cache/python` in subsequent processes. Its `main()` function just runs
that setup and prints the cache location. This mechanism exists because the
project explicitly keeps generated files under one directory.

### Following a complete turn

1. **Start:** the installed `ludo` command calls `main.main()`.
   `application.create_application()` creates Qt before any widgets exist.
2. **Create the game:** `GameEngine.__init__()` calls `new_game()` to create
   `Player` and `Pawn` objects, then a validated `GameState`. Every pawn
   initially has progress -1. The engine retains the chosen die.
3. **Show the board:** `MainWindow` creates its controller, sidebar, and board,
   then calls `_refresh_view()`. Qt calls `BoardWidget.paintEvent()`, which
   paints the board and asks `BoardGeometry` for token positions and
   `PawnRenderer` to paint them. Resizing repeats this calculation at the new
   widget size; it never changes pawn progress.
4. **Roll:** the sidebar's Roll Dice button emits `roll_requested`, connected
   to `GameController.roll_dice()`. That calls `GameEngine.roll_dice()`, which
   checks the turn phase before asking `Dice.roll()` for a value.
5. **Find moves:** the engine's `_movable_pawns()` calls `Board.destination()`
   for each active pawn. A playable roll becomes `pending_roll`; an unplayable
   roll automatically resolves the turn. The controller emits `updated`,
   and `_refresh_view()` displays the result, legal rings, and button state.
6. **Choose a pawn:** `BoardWidget.mousePressEvent()` checks the current pawn
   circles, allowed IDs, and active color. A legal circle emits
   `pawn_clicked(color, pawn_id)`, connected to the controller's `move_pawn()`.
   The controller calls the engine, which independently checks legality.
7. **Apply the move:** `GameEngine.move_pawn()` calculates the destination
   through `Board`, copies the active pawn collection, replaces the selected
   pawn, and calls `_players_after_capture()`. Captured opponents are copied
   back to base. A validated new snapshot replaces `_state` only at the end.
8. **Resolve the turn:** `_next_player_index()` keeps the same player after a
   six; otherwise it advances one position and wraps to the first player.
   The pending roll is consumed. The controller describes the accepted move
   and emits `updated`, so the new snapshot is drawn immediately.
9. **Finish:** if `moved_player.has_won` is true, the engine records the winner
   and ends the turn immediately. The controller emits `game_won`, and
   `MainWindow._announce_winner()` opens the notification. `can_roll` is false
   until New Game creates a fresh snapshot.

### Python features worth recognizing

- `@dataclass` generates ordinary initialization and comparison methods.
  `frozen=True` prevents normal attribute assignment; tuples prevent changes
  to player and pawn collections. `slots=True` limits those data objects to
  their declared fields.
- `replace(old_object, field=new_value)` creates another dataclass object.
  The engine uses it to preserve old snapshots rather than edit them. A local
  list used while building a move is converted back to a tuple before it is
  stored; the live snapshot never contains that mutable list.
- `@property` allows reads such as `engine.state` and `pawn.finished`.
  Without a setter, callers cannot normally assign to those properties.
  Controller properties also let the window read data without reaching into
  the controller's internal engine.
- `@classmethod` supplies `cls`, used by constructors such as `from_state()`
  and board calculations using class constants. `@staticmethod` marks a helper
  that needs neither `self` nor `cls`, such as capture feedback counting.
- A Qt `Signal` announces an event; `.connect(handler)` names the method to
  call for it. `@Slot` marks a Qt handler. These are direct connections between
  the existing objects, with no additional event framework.
- `MappingProxyType` makes the shared coordinate and color dictionaries
  read-only. Board rotations define the repeated quadrants once rather than
  maintaining four independently copied routes.

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

Geometry tests check 52 unique connected shared cells, color offsets, private
home lanes, progress wraparound, adjacent home entry, base/finish slots,
viewport round trips, and distinct non-overlapping stacks of every size.
Offscreen GUI tests check actual route/base pixels at several aspect ratios,
engine-driven state updates, finished pawns, window resizing, and both launch
entry points. Interaction tests use Qt button and mouse events to verify
roll permissions, legal highlights, invalid/opponent clicks, safe stacks,
captures, bonus rolls, automatic passes, exact finishing, victory notification,
and resets for 2–4 players. A seeded end-to-end test plays a complete two-player
game from base to victory through the actual controls. It simulates human
input; it does not add an AI opponent to the application.

Native desktop startup and visual previews are checked separately from the
offscreen tests. Generated previews stay under `.cache/previews/`.

Each test file has one area to explain:

| Python file | What it checks and uses |
| --- | --- |
| `tests/conftest.py` | Provides the shared `application` fixture. It imports Qt only when a GUI test requests that fixture. |
| `tests/test_application.py` | Checks configuration, window layout, resize behavior, and both real launch entry points. |
| `tests/test_dice.py` | Uses seeded or mocked random sources to check `Dice` results, bounds, and invalid values. |
| `tests/test_models.py` | Checks `Board`, `Pawn`, `Player`, and `GameState` validation and immutable snapshots. |
| `tests/test_engine.py` | Checks rules, turns, captures, invalid-action preservation, and complete games for 2–4 players. Its internal `_ScriptedDice` deliberately bypasses Dice validation to test the engine's own guard. |
| `tests/test_board_geometry.py` | Checks track cells, home routes, viewport conversion, and every safe-square stack size from 1 to 16. |
| `tests/test_board_widget.py` | Samples actual QPainter output and checks that snapshots, pawn positions, and resizing agree. |
| `tests/test_game_interaction.py` | Clicks actual buttons and pawn circles through Qt, checks feedback and controls, and completes a seeded two-player game. |

On a ROS-configured shell, clear inherited system packages for the test command:

```bash
env -u PYTHONPATH uv run --locked pytest
```

## Stage 4.5 review and professor feedback

The review used the feedback relayed in the project conversation, this guide,
`AGENTS.md`, the source/tests, and Git history. Commit `b355995` ("improvements
after consultations") records the relevant naming, imports, Ruff, and build
changes. No separate original professor rubric or instruction document was
found in the project; full compliance with an unseen rubric cannot be verified.

| Explicit feedback relayed by the student | Preserved implementation |
| --- | --- |
| Add more Ruff checks | Keep the expanded lint families in `pyproject.toml`; run lint and format checks. |
| Use descriptive names rather than `a` and `b` | Keep names such as `lower_bound`, `upper_bound`, and `pawn_id`; clarify stack dimensions as `column_count`, `row_count`, and `pawns_in_row`. |
| Reconsider `setup.py` with uv | Keep dependencies and build metadata in `pyproject.toml`, the `uv_build` backend, and `uv.lock`. `setup.py` remains absent. |
| Consider empty package markers, underscore names, and access | Keep package markers empty, explicit module imports, internal `_name` attributes/helpers, and read-only public properties. |

The specific choice of `__all__` tuples, a single leading underscore rather
than name mangling, frozen snapshots, Google-style docstrings, selected Ruff
families, and the exact class split are established project conventions.
They are preserved, but are not presented as verbatim professor instructions.
Function `Args` and `Returns` documentation, uv usage, and centralized caches
also follow the student's explicit earlier requests.

The changes are focused on reading the existing implementation:

- `core/game.py`: replace the nested capture expression with an ordinary
  loop, update the selected pawn through a copied list, and reuse
  `Board.MAX_DICE` rather than declaring another value of six.
- `core/state.py`: give the active index a short, descriptive local name so
  its type and range checks are easier to read. Validation is unchanged.
- `gui/game_controller.py`: use `_reset_feedback()` for initialization, reset,
  and scenario loading; count actual captures with explicit loops; combine
  two identical message branches.
- `gui/board_widget.py`: build star vertices and find clicked pawns with
  explicit loops. The drawing and click order are unchanged.
- `gui/board_geometry.py`: name stack dimensions and the occupied part of a
  row separately, without changing coordinates or token sizes.
- `gui/game_sidebar.py`: keep the New Game button as a local variable because
  no later method needs it. Retain the displayed-player-count field: it keeps
  turn refreshes from overwriting a selection for the next game.
- `config.py` and `tests/test_application.py`: correct the existing window
  title to the Stage 1 requirement, `Ludo - Chińczyk`, and check that exact text.
- `tests/test_game_interaction.py`: add a regression test for opening a
  playable pending roll while retaining the injected dice source.
- `README.md` and `AGENTS.md`: record the review, requirement sources, and
  student-oriented maintenance guidance.

No source files were removed or merged, and no public classes or APIs were
removed. Each existing module has a distinct role; merging them would mix
game data, rules, input routing, or drawing. The small `RandomSource` protocol
keeps test dice understandable, and the engine's separate roll validation
still protects against an overriding dice implementation. The `Game` alias
and existing snapshot APIs remain compatible. No future stage was implemented.

The baseline was **192 passed, 0 failed**. After refactoring it was
**193 passed, 0 failed**, with the existing suite retained. A separate
double-scaling run passed all **26** board/interaction cases. Native X11 startup,
rolling, pawn selection, a bonus roll, victory notification, and restart were
also exercised at a device pixel ratio of 2. The complete two-player game is
verified with simulated Qt input, not a claim that two people manually played
it. Ruff lint/format, compilation, and Git whitespace checks passed as well.

## Linux environment troubleshooting

Qt's X11 backend needs native libraries in addition to the Python wheels.
If startup reports that the `xcb` plugin cannot load and
`libxcb-cursor.so.0` is missing, install the distribution's cursor library.
On Debian/Ubuntu:

```bash
sudo apt install libxcb-cursor0
```
