"""Six-sided dice with an injectable random source."""

import random
from typing import Protocol

from Ludo.core.board import Board

__all__ = ("Dice", "RandomSource")


class RandomSource(Protocol):
    """The small random-number interface needed by Dice."""

    def randint(self, lower_bound: int, upper_bound: int, /) -> int:
        """Describe the integer-generation operation required by Dice.

        Args:
            lower_bound: Inclusive lower bound.
            upper_bound: Inclusive upper bound.

        Returns:
            An integer between lower_bound and upper_bound, inclusive.
        """
        ...


class Dice:
    """Use random.Random by default, or a seeded/scripted source in tests."""

    def __init__(self, random_source: RandomSource | None = None) -> None:
        """Initialize a six-sided die with an optional random source.

        Args:
            random_source: An object providing randint(lower_bound,
                upper_bound) using positional arguments. Creates a
                random.Random instance when None.
        """
        self._random_source = (
            random_source if random_source is not None else random.Random()
        )

    def roll(self) -> int:
        """Generate and validate one six-sided dice result.

        Returns:
            An integer from 1 to 6.
        """
        rolled_value = self._random_source.randint(
            Board.MIN_DICE, Board.MAX_DICE
        )
        Board.validate_roll(rolled_value)
        return rolled_value
