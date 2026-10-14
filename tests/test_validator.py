"""
Unit tests for flashcard validation rules.

Validation collects every problem rather than failing on the first, so most
of these tests assert on the *set* of messages produced by a bad deck.
"""

from typing import Any, List

from flashcards.validator import validate_card, validate_deck


class TestValidateCard:
    """Test suite for single-card validation."""

    def test_accepts_canonical_field_names(self) -> None:
        """Test that term/definition are accepted."""
        errors: List[str] = []
        card = validate_card({"term": "A", "definition": "B"}, 0, errors)
        assert card is not None
        assert (card.term, card.definition) == ("A", "B")
        assert errors == []

    def test_accepts_question_answer_aliases(self) -> None:
        """Test that question/answer aliases map onto term/definition."""
        errors: List[str] = []
        card = validate_card({"question": "A", "answer": "B"}, 0, errors)
        assert card is not None
        assert (card.term, card.definition) == ("A", "B")

    def test_accepts_front_back_aliases(self) -> None:
        """Test that front/back aliases map onto term/definition."""
        errors: List[str] = []
        card = validate_card({"front": "A", "back": "B"}, 0, errors)
        assert card is not None
        assert (card.term, card.definition) == ("A", "B")

    def test_strips_surrounding_whitespace(self) -> None:
        """Test that stored values are trimmed."""
        errors: List[str] = []
        card = validate_card({"term": "  A  ", "definition": " B "}, 0, errors)
        assert card is not None
        assert (card.term, card.definition) == ("A", "B")

    def test_captures_optional_hint(self) -> None:
        """Test that a usable hint is retained."""
        errors: List[str] = []
        raw = {"term": "A", "definition": "B", "hint": " clue "}
        card = validate_card(raw, 0, errors)
        assert card is not None
        assert card.hint == "clue"

    def test_blank_hint_is_discarded(self) -> None:
        """Test that a blank hint is treated as absent, not as an error."""
        errors: List[str] = []
        raw = {"term": "A", "definition": "B", "hint": "   "}
        card = validate_card(raw, 0, errors)
        assert card is not None
        assert card.hint is None
        assert errors == []

    def test_non_string_hint_is_discarded(self) -> None:
        """Test that a wrongly-typed hint does not invalidate the card."""
        errors: List[str] = []
        raw = {"term": "A", "definition": "B", "hint": 7}
        card = validate_card(raw, 0, errors)
        assert card is not None
        assert card.hint is None
        assert errors == []

    def test_rejects_non_object_entry(self) -> None:
        """Test that a non-object entry is reported with its position."""
        errors: List[str] = []
        assert validate_card("oops", 2, errors) is None
        assert errors == ["Card 3: expected an object, got str."]

    def test_rejects_missing_term(self) -> None:
        """Test that a missing term is reported."""
        errors: List[str] = []
        assert validate_card({"definition": "B"}, 0, errors) is None
        assert "missing required field 'term'" in errors[0]

    def test_rejects_missing_definition(self) -> None:
        """Test that a missing definition is reported."""
        errors: List[str] = []
        assert validate_card({"term": "A"}, 0, errors) is None
        assert "missing required field 'definition'" in errors[0]

    def test_rejects_non_string_values(self) -> None:
        """Test that a non-string field is reported with its type."""
        errors: List[str] = []
        assert validate_card({"term": "A", "definition": 42}, 0, errors) is None
        assert errors == ["Card 1: field 'definition' must be text, got int."]

    def test_rejects_blank_values(self) -> None:
        """Test that a whitespace-only field is reported as empty."""
        errors: List[str] = []
        assert validate_card({"term": "  ", "definition": "B"}, 0, errors) is None
        assert errors == ["Card 1: field 'term' must not be empty."]

    def test_reports_both_bad_fields_at_once(self) -> None:
        """Test that one card can produce several messages."""
        errors: List[str] = []
        assert validate_card({}, 0, errors) is None
        assert len(errors) == 2

    def test_rejects_null_entry(self) -> None:
        """Test that a JSON null entry is reported."""
        errors: List[str] = []
        assert validate_card(None, 0, errors) is None
        assert "got NoneType" in errors[0]


class TestValidateDeck:
    """Test suite for whole-deck validation."""

    def test_valid_deck_produces_no_errors(self) -> None:
        """Test that a clean deck validates without complaint."""
        raw: List[Any] = [
            {"term": "A", "definition": "1"},
            {"term": "B", "definition": "2"},
        ]
        cards, errors = validate_deck(raw)
        assert [c.term for c in cards] == ["A", "B"]
        assert errors == []

    def test_preserves_file_order(self) -> None:
        """Test that cards keep the order they appear in the file."""
        raw: List[Any] = [
            {"term": str(i), "definition": "x"} for i in range(5)
        ]
        cards, _ = validate_deck(raw)
        assert [c.term for c in cards] == ["0", "1", "2", "3", "4"]

    def test_skips_bad_cards_but_keeps_good_ones(self) -> None:
        """Test that one bad card does not discard the whole deck."""
        raw: List[Any] = [
            {"term": "Good", "definition": "kept"},
            {"term": "Bad"},
        ]
        cards, errors = validate_deck(raw)
        assert [c.term for c in cards] == ["Good"]
        assert len(errors) == 1

    def test_duplicate_terms_are_skipped_and_reported(self) -> None:
        """Test that a repeated term keeps the first card only."""
        raw: List[Any] = [
            {"term": "Alpha", "definition": "first"},
            {"term": "ALPHA", "definition": "second"},
        ]
        cards, errors = validate_deck(raw)
        assert len(cards) == 1
        assert cards[0].definition == "first"
        assert "duplicate term" in errors[0]
        assert "first seen on card 1" in errors[0]

    def test_empty_deck_is_reported(self) -> None:
        """Test that an empty list produces an explanatory message."""
        cards, errors = validate_deck([])
        assert cards == []
        assert errors == ["The deck contains no flashcards."]

    def test_all_bad_deck_reports_each_problem(self) -> None:
        """Test that a wholly invalid deck reports every card."""
        cards, errors = validate_deck([{}, "x", None])
        assert cards == []
        assert len(errors) == 4
