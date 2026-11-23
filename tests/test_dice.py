"""Deterministic dice injection and invalid-source regression tests."""

import random
from unittest.mock import Mock

import pytest

from Ludo.core.dice import Dice
from Ludo.core.exceptions import InvalidRollError


def test_seeded_random_sources_produce_reproducible_valid_rolls() -> None:
    """Verify that matching seeds produce identical valid dice sequences."""
    dice = Dice(random.Random(42))
    duplicate = Dice(random.Random(42))
    rolls = [dice.roll() for _ in range(100)]
    assert rolls == [duplicate.roll() for _ in range(100)]
    assert set(rolls) == {1, 2, 3, 4, 5, 6}


def test_dice_uses_inclusive_bounds_from_the_injected_source() -> None:
    """Verify that Dice requests inclusive bounds from its random source."""
    source = Mock()
    source.randint.side_effect = [6, 1, 4]
    dice = Dice(random_source=source)
    assert [dice.roll() for _ in range(3)] == [6, 1, 4]
    assert source.randint.call_count == 3
    source.randint.assert_called_with(1, 6)


@pytest.mark.parametrize("value", [0, 7, -1, True, 6.0, "6", None])
def test_invalid_random_source_results_are_rejected(value: object) -> None:
    """Verify that an invalid random-source result raises an error.

    Args:
        value: A parametrized result outside the accepted integer range
            1..6.
    """
    source = Mock()
    source.randint.return_value = value
    with pytest.raises(InvalidRollError):
        Dice(source).roll()
