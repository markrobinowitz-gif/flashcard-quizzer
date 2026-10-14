"""
Unit tests for the quiz mode strategies.

The randomised modes are driven with a seeded ``random.Random`` so that
every assertion is exact rather than statistical. The most important tests
here are the termination tests: a mode that never returns ``None`` would
hang the application.
"""

import random
from collections import Counter
from typing import List

import pytest

from flashcards.models import Flashcard
from flashcards.modes.adaptive import MAX_ATTEMPTS, AdaptiveMode
from flashcards.modes.base import QuizMode
from flashcards.modes.random_mode import RandomMode
from flashcards.modes.sequential import SequentialMode


def drain(mode: QuizMode, correct: bool = True, limit: int = 1000) -> List[str]:
    """Run a mode to exhaustion, returning the terms it asked."""
    asked: List[str] = []
    for _ in range(limit):
        card = mode.next_card()
        if card is None:
            return asked
        asked.append(card.term)
        mode.record_result(card, correct)
    raise AssertionError("mode did not terminate")


class TestQuizModeBase:
    """Test suite for behaviour shared by every strategy."""

    @pytest.mark.parametrize(
        "mode_class", [SequentialMode, RandomMode, AdaptiveMode]
    )
    def test_empty_deck_is_rejected(self, mode_class) -> None:
        """Test that no strategy accepts an empty deck."""
        with pytest.raises(ValueError, match="at least one flashcard"):
            mode_class([])

    @pytest.mark.parametrize(
        "mode_class", [SequentialMode, RandomMode, AdaptiveMode]
    )
    def test_modes_expose_name_and_description(
        self, mode_class, sample_cards
    ) -> None:
        """Test that every strategy is self-describing."""
        mode = mode_class(sample_cards)
        assert isinstance(mode.name, str) and mode.name
        assert isinstance(mode.description, str) and mode.description

    @pytest.mark.parametrize(
        "mode_class", [SequentialMode, RandomMode, AdaptiveMode]
    )
    def test_cards_property_is_a_defensive_copy(
        self, mode_class, sample_cards
    ) -> None:
        """Test that mutating the returned deck cannot corrupt the mode."""
        mode = mode_class(sample_cards)
        mode.cards.clear()
        assert len(mode.cards) == len(sample_cards)

    def test_quiz_mode_cannot_be_instantiated(self, sample_cards) -> None:
        """Test that the abstract base class is genuinely abstract."""
        with pytest.raises(TypeError):
            QuizMode(sample_cards)  # type: ignore[abstract]

    def test_base_record_result_is_a_no_op(self, sample_cards) -> None:
        """Test that the default feedback hook does nothing and returns."""
        mode = SequentialMode(sample_cards)
        assert mode.record_result(sample_cards[0], False) is None

    def test_constructor_copies_the_deck(self, sample_cards) -> None:
        """Test that later changes to the caller's list are not seen."""
        deck = list(sample_cards)
        mode = SequentialMode(deck)
        deck.append(Flashcard("late", "addition"))
        assert len(drain(mode)) == 3


class TestSequentialMode:
    """Test suite for SequentialMode."""

    def test_asks_every_card_in_file_order(self, sample_cards) -> None:
        """Test that cards come back in the order given."""
        mode = SequentialMode(sample_cards)
        assert drain(mode) == ["alpha", "beta", "gamma"]

    def test_returns_none_when_exhausted(self, sample_cards) -> None:
        """Test that the mode reports completion exactly once per card."""
        mode = SequentialMode(sample_cards)
        drain(mode)
        assert mode.next_card() is None
        assert mode.next_card() is None

    def test_order_is_unaffected_by_results(self, sample_cards) -> None:
        """Test that wrong answers do not change a fixed ordering."""
        mode = SequentialMode(sample_cards)
        assert drain(mode, correct=False) == ["alpha", "beta", "gamma"]

    def test_name_is_sequential(self, sample_cards) -> None:
        """Test the command-line name of the mode."""
        assert SequentialMode(sample_cards).name == "sequential"


class TestRandomMode:
    """Test suite for RandomMode."""

    def test_asks_every_card_exactly_once(self, sample_cards) -> None:
        """Test that shuffling does not drop or duplicate cards."""
        mode = RandomMode(sample_cards, rng=random.Random(7))
        asked = drain(mode)
        assert sorted(asked) == ["alpha", "beta", "gamma"]

    def test_seeded_order_is_reproducible(self, sample_cards) -> None:
        """Test that the same seed yields the same order."""
        first = drain(RandomMode(sample_cards, rng=random.Random(99)))
        second = drain(RandomMode(sample_cards, rng=random.Random(99)))
        assert first == second

    def test_different_seeds_can_differ(self) -> None:
        """Test that the deck is genuinely shuffled, not merely copied."""
        deck = [Flashcard(str(i), str(i)) for i in range(25)]
        a = drain(RandomMode(deck, rng=random.Random(1)))
        b = drain(RandomMode(deck, rng=random.Random(2)))
        assert a != b

    def test_does_not_mutate_the_source_deck(self, sample_cards) -> None:
        """Test that shuffling works on a copy."""
        original = list(sample_cards)
        RandomMode(sample_cards, rng=random.Random(3))
        assert sample_cards == original

    def test_returns_none_when_exhausted(self, sample_cards) -> None:
        """Test that the mode terminates."""
        mode = RandomMode(sample_cards, rng=random.Random(5))
        drain(mode)
        assert mode.next_card() is None

    def test_defaults_to_its_own_rng(self, sample_cards) -> None:
        """Test that the mode works without an injected random source."""
        assert sorted(drain(RandomMode(sample_cards))) == [
            "alpha",
            "beta",
            "gamma",
        ]

    def test_name_is_random(self, sample_cards) -> None:
        """Test the command-line name of the mode."""
        assert RandomMode(sample_cards).name == "random"


class TestAdaptiveMode:
    """Test suite for AdaptiveMode."""

    def test_correct_answers_retire_cards_immediately(
        self, sample_cards
    ) -> None:
        """Test that an all-correct run asks each card exactly once."""
        mode = AdaptiveMode(sample_cards, rng=random.Random(11))
        asked = drain(mode, correct=True)
        assert sorted(asked) == ["alpha", "beta", "gamma"]

    def test_terminates_even_when_every_answer_is_wrong(
        self, sample_cards
    ) -> None:
        """Test the attempt cap, which is what guarantees termination."""
        mode = AdaptiveMode(sample_cards, rng=random.Random(11))
        asked = drain(mode, correct=False)
        assert len(asked) == len(sample_cards) * MAX_ATTEMPTS

    def test_each_card_is_capped_individually(self, sample_cards) -> None:
        """Test that no single card exceeds the attempt cap."""
        mode = AdaptiveMode(sample_cards, rng=random.Random(11))
        asked = drain(mode, correct=False)
        for term in ["alpha", "beta", "gamma"]:
            assert asked.count(term) == MAX_ATTEMPTS

    def test_never_asks_the_same_card_twice_in_a_row(self) -> None:
        """Test that consecutive repeats are avoided when possible."""
        deck = [Flashcard(str(i), str(i)) for i in range(5)]
        mode = AdaptiveMode(deck, rng=random.Random(4))
        asked = drain(mode, correct=False)
        assert all(a != b for a, b in zip(asked, asked[1:]))

    def test_single_card_deck_repeats_up_to_the_cap(self) -> None:
        """Test the edge case where no alternative card exists."""
        mode = AdaptiveMode([Flashcard("solo", "only")], rng=random.Random(1))
        assert drain(mode, correct=False) == ["solo"] * MAX_ATTEMPTS

    def test_missed_cards_are_asked_more_often(self) -> None:
        """Test that weighting actually favours the missed card."""
        # Three cards, not two: with a two-card deck the no-immediate-repeat
        # rule forces strict alternation and would mask the weighting.
        deck = [
            Flashcard("hard", "h"),
            Flashcard("easy1", "e"),
            Flashcard("easy2", "e"),
        ]
        mode = AdaptiveMode(deck, rng=random.Random(2), max_attempts=99)
        hard = deck[0]
        # Miss 'hard' twice so its weight climbs to 3 against 1 and 1.
        mode.record_result(hard, False)
        mode.record_result(hard, False)
        draws = [mode.next_card() for _ in range(600)]
        counts = Counter(c.term for c in draws if c is not None)
        assert counts["hard"] > counts["easy1"]
        assert counts["hard"] > counts["easy2"]

    def test_two_card_deck_alternates(self) -> None:
        """Test the documented consequence of the no-repeat rule.

        With only two cards in play there is never a third option, so the
        mode alternates regardless of weighting. This is intended, and is
        recorded here so the behaviour is not mistaken for a weighting bug.
        """
        deck = [Flashcard("hard", "h"), Flashcard("easy", "e")]
        mode = AdaptiveMode(deck, rng=random.Random(2), max_attempts=99)
        mode.record_result(deck[0], False)
        mode.record_result(deck[0], False)
        asked = [mode.next_card().term for _ in range(10)]
        assert all(a != b for a, b in zip(asked, asked[1:]))

    def test_wrong_then_right_retires_the_card(self, sample_cards) -> None:
        """Test that a corrected answer stops the card coming back."""
        mode = AdaptiveMode(sample_cards, rng=random.Random(6))
        card = sample_cards[0]
        mode.record_result(card, False)
        mode.record_result(card, True)
        assert card.term not in drain(mode, correct=True)

    def test_custom_max_attempts_is_honoured(self, sample_cards) -> None:
        """Test that the cap is configurable."""
        mode = AdaptiveMode(
            sample_cards, rng=random.Random(8), max_attempts=1
        )
        assert len(drain(mode, correct=False)) == len(sample_cards)

    def test_max_attempts_below_one_is_rejected(self, sample_cards) -> None:
        """Test that a nonsensical cap is refused up front."""
        with pytest.raises(ValueError, match="at least 1"):
            AdaptiveMode(sample_cards, max_attempts=0)

    def test_foreign_card_is_ignored(self, sample_cards) -> None:
        """Test that replaying an unknown card cannot corrupt state."""
        mode = AdaptiveMode(sample_cards, rng=random.Random(9))
        mode.record_result(Flashcard("foreign", "card"), False)
        assert len(drain(mode, correct=True)) == len(sample_cards)

    def test_defaults_to_its_own_rng(self, sample_cards) -> None:
        """Test that the mode works without an injected random source."""
        assert len(drain(AdaptiveMode(sample_cards))) == len(sample_cards)

    def test_name_is_adaptive(self, sample_cards) -> None:
        """Test the command-line name of the mode."""
        assert AdaptiveMode(sample_cards).name == "adaptive"

    def test_description_mentions_the_cap(self, sample_cards) -> None:
        """Test that the description explains the retirement rule."""
        mode = AdaptiveMode(sample_cards, max_attempts=4)
        assert "4 attempts" in mode.description
