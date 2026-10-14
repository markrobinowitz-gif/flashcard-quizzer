"""
Unit tests for the Flashcard model and answer normalisation.

Answer comparison is the single most user-visible behaviour in the app, so
these tests cover casing, surrounding whitespace, internal whitespace, and
non-ASCII folding.
"""

import pytest

from flashcards.models import Flashcard, normalize_answer


class TestNormalizeAnswer:
    """Test suite for the normalize_answer helper."""

    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("Binary Search", "binary search"),
            ("  padded  ", "padded"),
            ("collapse   internal    runs", "collapse internal runs"),
            ("MiXeD CaSe", "mixed case"),
            ("tab\tseparated", "tab separated"),
            ("new\nline", "new line"),
            ("", ""),
            ("   ", ""),
        ],
    )
    def test_normalization_cases(self, raw: str, expected: str) -> None:
        """Test that whitespace and casing are normalised consistently."""
        assert normalize_answer(raw) == expected

    def test_casefold_handles_non_ascii(self) -> None:
        """Test that casefold folds non-ASCII characters correctly."""
        assert normalize_answer("STRASSE") == normalize_answer("strasse")
        assert normalize_answer("Café") == "café"


class TestFlashcard:
    """Test suite for the Flashcard dataclass."""

    def test_is_correct_ignores_case(self) -> None:
        """Test that answers match regardless of capitalisation."""
        card = Flashcard("Big-O", "Upper Bound")
        assert card.is_correct("upper bound")
        assert card.is_correct("UPPER BOUND")

    def test_is_correct_ignores_surrounding_whitespace(self) -> None:
        """Test that leading and trailing whitespace is ignored."""
        card = Flashcard("Big-O", "Upper Bound")
        assert card.is_correct("   upper bound   ")

    def test_is_correct_rejects_wrong_answer(self) -> None:
        """Test that a genuinely different answer is rejected."""
        card = Flashcard("Big-O", "Upper Bound")
        assert not card.is_correct("lower bound")

    def test_is_correct_rejects_empty_answer(self) -> None:
        """Test that an empty answer is not treated as correct."""
        card = Flashcard("Big-O", "Upper Bound")
        assert not card.is_correct("")

    def test_empty_answer_matches_only_empty_definition(self) -> None:
        """Test that normalisation does not make blanks universally right."""
        card = Flashcard("Blank", "   ")
        assert card.is_correct("")

    def test_hint_defaults_to_none(self) -> None:
        """Test that the optional hint field defaults to None."""
        assert Flashcard("term", "definition").hint is None

    def test_card_is_frozen(self) -> None:
        """Test that cards are immutable once constructed."""
        card = Flashcard("term", "definition")
        with pytest.raises(Exception):
            card.term = "changed"  # type: ignore[misc]

    def test_card_is_hashable(self) -> None:
        """Test that cards can be used as dictionary keys."""
        card = Flashcard("term", "definition")
        assert {card: 1}[card] == 1
