"""Six-sided dice with an injectable random source."""

import random
from typing import Protocol

from src.core.board import Board


class RandomSource(Protocol):
    """The small random-number interface needed by Dice."""

    def randint(self, a: int, b: int) -> int:
        """Return an integer in the inclusive range [a, b]."""
        ...


class Dice:
    """Use random.Random by default, or a seeded/scripted source in tests."""

    def __init__(self, rng: RandomSource | None = None) -> None:
        self._rng = rng if rng is not None else random.Random()

    def roll(self) -> int:
        value = self._rng.randint(1, 6)
        Board.validate_roll(value)
        return value
