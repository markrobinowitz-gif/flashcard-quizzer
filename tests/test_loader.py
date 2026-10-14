"""
Unit tests for loading flashcard decks from disk.

These cover both supported JSON shapes and every failure mode the CLI
promises to handle without showing a traceback.
"""

import pytest

from flashcards.exceptions import (
    FlashcardError,
    FlashcardFileNotFoundError,
    FlashcardFileReadError,
    InvalidJSONError,
    ValidationError,
)
from flashcards.loader import load_flashcards, load_flashcards_with_warnings


class TestLoadValidDecks:
    """Test suite for successfully loaded decks."""

    def test_loads_bare_array_format(self, fixture_path) -> None:
        """Test that a top-level JSON array loads."""
        cards = load_flashcards(fixture_path("valid_array.json"))
        assert len(cards) == 3
        assert cards[0].term == "Big-O notation"

    def test_loads_object_with_cards_key(self, fixture_path) -> None:
        """Test that the {"cards": [...]} wrapper loads."""
        cards = load_flashcards(fixture_path("valid_object.json"))
        assert len(cards) == 2
        assert cards[0].term == "Stack"

    def test_object_format_supports_aliases_and_hints(
        self, fixture_path
    ) -> None:
        """Test that aliases and hints survive the round trip."""
        cards = load_flashcards(fixture_path("valid_object.json"))
        assert cards[0].hint == "Last in, first out"
        assert cards[1].term == "Queue"
        assert cards[1].definition == "FIFO collection"

    def test_loads_unicode_content(self, fixture_path) -> None:
        """Test that non-ASCII decks load and compare correctly."""
        cards = load_flashcards(fixture_path("unicode.json"))
        assert cards[0].term == "Großschreibung"
        assert cards[1].is_correct("COFFEE HOUSE")

    def test_accepts_string_path(self, fixture_path) -> None:
        """Test that a plain string path is accepted alongside Path."""
        cards = load_flashcards(str(fixture_path("valid_array.json")))
        assert len(cards) == 3


class TestLoadFailures:
    """Test suite for the error paths."""

    def test_missing_file_raises_not_found(self, fixture_path) -> None:
        """Test that a missing file raises a typed, readable error."""
        with pytest.raises(FlashcardFileNotFoundError, match="not found"):
            load_flashcards(fixture_path("no_such_file.json"))

    def test_directory_raises_read_error(self, tmp_path) -> None:
        """Test that passing a directory is reported clearly."""
        with pytest.raises(FlashcardFileReadError, match="directory"):
            load_flashcards(tmp_path)

    def test_malformed_json_reports_position(self, fixture_path) -> None:
        """Test that a syntax error names the line and column."""
        with pytest.raises(InvalidJSONError) as exc_info:
            load_flashcards(fixture_path("malformed.json"))
        message = str(exc_info.value)
        assert "line" in message and "column" in message

    def test_non_utf8_file_raises_read_error(self, tmp_path) -> None:
        """Test that a non-UTF-8 file is reported, not crashed on."""
        bad = tmp_path / "latin1.json"
        bad.write_bytes(b'[{"term": "caf\xe9", "definition": "x"}]')
        with pytest.raises(FlashcardFileReadError, match="UTF-8"):
            load_flashcards(bad)

    def test_empty_array_raises_validation_error(self, fixture_path) -> None:
        """Test that an empty deck is rejected with an explanation."""
        with pytest.raises(ValidationError, match="no flashcards"):
            load_flashcards(fixture_path("empty_array.json"))

    def test_object_without_cards_key_is_rejected(self, fixture_path) -> None:
        """Test that the wrong object key is reported helpfully."""
        with pytest.raises(ValidationError) as exc_info:
            load_flashcards(fixture_path("wrong_shape.json"))
        assert "'cards'" in str(exc_info.value)

    def test_cards_key_must_be_a_list(self, fixture_path) -> None:
        """Test that a non-list 'cards' value is reported with its type."""
        with pytest.raises(ValidationError, match="must be a list"):
            load_flashcards(fixture_path("cards_not_list.json"))

    def test_top_level_scalar_is_rejected(self, tmp_path) -> None:
        """Test that JSON that is neither list nor object is rejected."""
        scalar = tmp_path / "scalar.json"
        scalar.write_text("42", encoding="utf-8")
        with pytest.raises(ValidationError, match="got int"):
            load_flashcards(scalar)

    def test_deck_of_only_bad_cards_is_fatal(self, tmp_path) -> None:
        """Test that a deck with no usable cards raises rather than returns."""
        deck = tmp_path / "bad.json"
        deck.write_text('[{"term": "no definition"}]', encoding="utf-8")
        with pytest.raises(ValidationError):
            load_flashcards(deck)

    def test_all_errors_derive_from_flashcard_error(
        self, fixture_path
    ) -> None:
        """Test that the CLI can catch every failure with one base class."""
        with pytest.raises(FlashcardError):
            load_flashcards(fixture_path("no_such_file.json"))
        with pytest.raises(FlashcardError):
            load_flashcards(fixture_path("malformed.json"))

    def test_validation_error_lists_each_problem(self, tmp_path) -> None:
        """Test that ValidationError carries the individual messages."""
        deck = tmp_path / "bad.json"
        deck.write_text('[{}, "x"]', encoding="utf-8")
        with pytest.raises(ValidationError) as exc_info:
            load_flashcards(deck)
        assert len(exc_info.value.errors) == 3

    def test_single_problem_message_is_singular(self, tmp_path) -> None:
        """Test that the summary line reads naturally for one problem."""
        deck = tmp_path / "empty.json"
        deck.write_text("[]", encoding="utf-8")
        with pytest.raises(ValidationError, match="Found 1 problem"):
            load_flashcards(deck)


class TestLoadWithWarnings:
    """Test suite for the warning-preserving loader used by the CLI."""

    def test_returns_good_cards_and_warnings(self, fixture_path) -> None:
        """Test that a partly-bad deck yields cards plus explanations."""
        cards, warnings = load_flashcards_with_warnings(
            fixture_path("missing_fields.json")
        )
        assert [c.term for c in cards] == ["Good"]
        assert len(warnings) == 5

    def test_clean_deck_produces_no_warnings(self, fixture_path) -> None:
        """Test that a valid deck reports nothing."""
        cards, warnings = load_flashcards_with_warnings(
            fixture_path("valid_array.json")
        )
        assert len(cards) == 3
        assert warnings == []
