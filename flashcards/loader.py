"""
Loading flashcard decks from JSON files.

Two on-disk shapes are supported:

* a bare array — ``[{"term": "...", "definition": "..."}, ...]``
* an object wrapper — ``{"cards": [...]}``

Every failure mode (missing file, unreadable file, bad encoding, malformed
JSON, wrong top-level shape, invalid cards) is converted into a
:class:`~flashcards.exceptions.FlashcardError` carrying a message fit to
show a user. No traceback ever reaches the terminal.
"""

import json
from pathlib import Path
from typing import Any, List, Tuple, Union

from flashcards.exceptions import (
    FlashcardFileNotFoundError,
    FlashcardFileReadError,
    InvalidJSONError,
    ValidationError,
)
from flashcards.models import Flashcard
from flashcards.validator import validate_deck

CARDS_KEY = "cards"


def _read_text(path: Path) -> str:
    """
    Read a file as UTF-8, translating OS errors into application errors.

    Args:
        path: The file to read.

    Returns:
        The file's text content.

    Raises:
        FlashcardFileNotFoundError: If the path does not exist.
        FlashcardFileReadError: If the file cannot be read or decoded.
    """
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise FlashcardFileNotFoundError(
            f"Flashcard file not found: {path}"
        ) from None
    except IsADirectoryError:
        raise FlashcardFileReadError(
            f"Expected a file but found a directory: {path}"
        ) from None
    except PermissionError:
        raise FlashcardFileReadError(
            f"Permission denied reading: {path}"
        ) from None
    except UnicodeDecodeError:
        raise FlashcardFileReadError(
            f"File is not valid UTF-8 text: {path}. "
            "Re-save the file with UTF-8 encoding."
        ) from None
    except OSError as exc:
        raise FlashcardFileReadError(f"Could not read {path}: {exc}") from None


def _parse_json(text: str, path: Path) -> Any:
    """
    Parse JSON text, reporting the exact position of any syntax error.

    Args:
        text: The raw file content.
        path: The originating path, used in the error message.

    Returns:
        The parsed JSON data.

    Raises:
        InvalidJSONError: If the text is not well-formed JSON.
    """
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise InvalidJSONError(
            f"Malformed JSON in {path} at line {exc.lineno}, "
            f"column {exc.colno}: {exc.msg}."
        ) from None


def _extract_card_list(data: Any, path: Path) -> List[Any]:
    """
    Narrow parsed JSON down to the list of raw card entries.

    Args:
        data: The parsed top-level JSON value.
        path: The originating path, used in error messages.

    Returns:
        The raw list of card entries.

    Raises:
        ValidationError: If the top-level shape is not supported.
    """
    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        if CARDS_KEY not in data:
            keys = ", ".join(sorted(repr(k) for k in data)) or "none"
            raise ValidationError(
                [
                    f"{path}: object form must contain a '{CARDS_KEY}' key "
                    f"(found: {keys})."
                ]
            )
        cards = data[CARDS_KEY]
        if not isinstance(cards, list):
            type_name = type(cards).__name__
            raise ValidationError(
                [f"{path}: '{CARDS_KEY}' must be a list, got {type_name}."]
            )
        return cards

    type_name = type(data).__name__
    raise ValidationError(
        [
            f"{path}: expected a list of cards or an object with a "
            f"'{CARDS_KEY}' key, got {type_name}."
        ]
    )


def load_flashcards_with_warnings(
    source: Union[str, Path],
) -> Tuple[List[Flashcard], List[str]]:
    """
    Load a deck, returning non-fatal problems instead of raising for them.

    Individual bad cards are skipped and described in the returned warnings
    so that a mostly-good deck stays usable; only a deck with no usable
    cards at all is treated as fatal.

    Args:
        source: Path to the JSON flashcard file.

    Returns:
        A tuple of the validated cards and any warnings about skipped cards.

    Raises:
        FlashcardFileNotFoundError: If the file does not exist.
        FlashcardFileReadError: If the file cannot be read or decoded.
        InvalidJSONError: If the file is not well-formed JSON.
        ValidationError: If no usable cards could be loaded.
    """
    path = Path(source)
    data = _parse_json(_read_text(path), path)
    raw_cards = _extract_card_list(data, path)
    cards, errors = validate_deck(raw_cards)

    if not cards:
        raise ValidationError(errors)

    return cards, errors


def load_flashcards(source: Union[str, Path]) -> List[Flashcard]:
    """
    Load and validate a flashcard deck from disk, ignoring warnings.

    Args:
        source: Path to the JSON flashcard file.

    Returns:
        The validated flashcards, in file order.

    Raises:
        FlashcardError: If the deck could not be loaded. See
            :func:`load_flashcards_with_warnings` for the specific types.
    """
    cards, _ = load_flashcards_with_warnings(source)
    return cards
