"""Six-sided dice with an injectable random source."""

import random
from typing import Protocol

from Ludo.core.board import Board


class RandomSource(Protocol):
    """The small random-number interface needed by Dice."""

    def randint(self, a: int, b: int) -> int:
        """Describe the integer-generation operation required by Dice.

        Args:
            a: Inclusive lower bound.
            b: Inclusive upper bound.

        Returns:
            An integer between a and b, including both bounds.
        """
        ...


class Dice:
    """Use random.Random by default, or a seeded/scripted source in tests."""

    def __init__(self, rng: RandomSource | None = None) -> None:
        """Initialize a six-sided die with an optional random source.

        Args:
            rng: An object providing randint(a, b). Creates a random.Random
                instance when None.
        """
        self._rng = rng if rng is not None else random.Random()

    def roll(self) -> int:
        """Generate and validate one six-sided dice result.

        Returns:
            An integer from 1 to 6.
        """
        value = self._rng.randint(1, 6)
        Board.validate_roll(value)
        return value
