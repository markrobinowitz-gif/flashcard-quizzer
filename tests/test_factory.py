"""
Unit tests for the quiz mode factory.

The factory is the single place that maps a user-supplied string onto a
strategy class, so these tests cover the mapping, the case-insensitivity
the CLI relies on, and the error raised for an unknown name.
"""

import random

import pytest

from flashcards.modes import (
    AdaptiveMode,
    QuizMode,
    QuizModeFactory,
    RandomMode,
    SequentialMode,
)


class TestQuizModeFactory:
    """Test suite for QuizModeFactory."""

    @pytest.mark.parametrize(
        "name,expected",
        [
            ("sequential", SequentialMode),
            ("random", RandomMode),
            ("adaptive", AdaptiveMode),
        ],
    )
    def test_creates_the_registered_class(
        self, name, expected, sample_cards
    ) -> None:
        """Test that each name maps to the right strategy."""
        mode = QuizModeFactory.create(name, sample_cards)
        assert isinstance(mode, expected)

    def test_every_product_is_a_quiz_mode(self, sample_cards) -> None:
        """Test that the factory only ever returns QuizMode instances."""
        for name in QuizModeFactory.available_modes():
            assert isinstance(
                QuizModeFactory.create(name, sample_cards), QuizMode
            )

    @pytest.mark.parametrize(
        "name", ["SEQUENTIAL", "Random", "  adaptive  ", "AdApTiVe"]
    )
    def test_name_matching_is_forgiving(self, name, sample_cards) -> None:
        """Test that case and padding do not matter."""
        assert isinstance(
            QuizModeFactory.create(name, sample_cards), QuizMode
        )

    def test_unknown_mode_raises_value_error(self, sample_cards) -> None:
        """Test that an unknown name is rejected."""
        with pytest.raises(ValueError, match="Unknown quiz mode 'turbo'"):
            QuizModeFactory.create("turbo", sample_cards)

    def test_unknown_mode_lists_the_valid_names(self, sample_cards) -> None:
        """Test that the error message tells the user what is valid."""
        with pytest.raises(ValueError) as exc_info:
            QuizModeFactory.create("turbo", sample_cards)
        message = str(exc_info.value)
        for name in QuizModeFactory.available_modes():
            assert name in message

    def test_empty_mode_name_is_rejected(self, sample_cards) -> None:
        """Test that a blank mode name does not silently default."""
        with pytest.raises(ValueError):
            QuizModeFactory.create("", sample_cards)

    def test_empty_deck_is_rejected(self) -> None:
        """Test that the factory propagates the empty-deck guard."""
        with pytest.raises(ValueError, match="at least one flashcard"):
            QuizModeFactory.create("sequential", [])

    def test_available_modes_covers_all_requirements(self) -> None:
        """Test that all three required modes are registered."""
        assert set(QuizModeFactory.available_modes()) == {
            "sequential",
            "random",
            "adaptive",
        }

    def test_available_modes_returns_a_copy(self) -> None:
        """Test that callers cannot mutate the registry through the list."""
        QuizModeFactory.available_modes().clear()
        assert len(QuizModeFactory.available_modes()) == 3

    def test_rng_is_forwarded_to_randomised_modes(self, sample_cards) -> None:
        """Test that a seeded source makes random mode reproducible."""
        first = QuizModeFactory.create(
            "random", sample_cards, rng=random.Random(42)
        )
        second = QuizModeFactory.create(
            "random", sample_cards, rng=random.Random(42)
        )
        assert first.next_card() == second.next_card()

    def test_rng_is_not_passed_to_sequential_mode(
        self, sample_cards
    ) -> None:
        """Test that the ordered mode ignores an irrelevant rng argument."""
        mode = QuizModeFactory.create(
            "sequential", sample_cards, rng=random.Random(42)
        )
        assert mode.next_card().term == "alpha"
