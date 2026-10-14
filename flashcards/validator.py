"""
Validation of raw flashcard data.

This module deliberately knows nothing about files or JSON syntax: it
receives already-parsed Python objects and reports what is wrong with them.
That separation keeps the rules testable without touching the filesystem.

Validation is *collecting* rather than *failing fast* — every problem in a
deck is reported at once so the user can fix the file in a single pass.
"""

from typing import Any, Dict, List, Optional, Tuple

from flashcards.models import Flashcard, normalize_answer

# Canonical field names, each with the aliases accepted as a substitute.
TERM_KEYS: Tuple[str, ...] = ("term", "question", "front")
DEFINITION_KEYS: Tuple[str, ...] = ("definition", "answer", "back")
HINT_KEYS: Tuple[str, ...] = ("hint",)


def _first_present(raw: Dict[str, Any], keys: Tuple[str, ...]) -> Optional[str]:
    """Return the first key from ``keys`` that is present in ``raw``."""
    for key in keys:
        if key in raw:
            return key
    return None


def _extract_field(
    raw: Dict[str, Any],
    keys: Tuple[str, ...],
    position: str,
    errors: List[str],
) -> Optional[str]:
    """
    Pull one required text field out of a raw card, recording any problem.

    Args:
        raw: The raw card dictionary.
        keys: Accepted key names, most canonical first.
        position: Human-readable card position used in error messages.
        errors: Mutable list that problems are appended to.

    Returns:
        The cleaned field value, or ``None`` if it was missing or invalid.
    """
    key = _first_present(raw, keys)
    if key is None:
        expected = " or ".join(f"'{k}'" for k in keys)
        errors.append(f"{position}: missing required field {expected}.")
        return None

    value = raw[key]
    if not isinstance(value, str):
        type_name = type(value).__name__
        errors.append(
            f"{position}: field '{key}' must be text, got {type_name}."
        )
        return None

    if not value.strip():
        errors.append(f"{position}: field '{key}' must not be empty.")
        return None

    return value.strip()


def validate_card(
    raw: Any, index: int, errors: List[str]
) -> Optional[Flashcard]:
    """
    Convert one raw entry into a :class:`Flashcard`, or record why not.

    Args:
        raw: The raw entry, which may be any JSON type.
        index: Zero-based position of the entry, used in messages.
        errors: Mutable list that problems are appended to.

    Returns:
        The validated card, or ``None`` if the entry was unusable.
    """
    position = f"Card {index + 1}"

    if not isinstance(raw, dict):
        type_name = type(raw).__name__
        errors.append(f"{position}: expected an object, got {type_name}.")
        return None

    term = _extract_field(raw, TERM_KEYS, position, errors)
    definition = _extract_field(raw, DEFINITION_KEYS, position, errors)

    if term is None or definition is None:
        return None

    hint_key = _first_present(raw, HINT_KEYS)
    hint: Optional[str] = None
    if hint_key is not None:
        hint_value = raw[hint_key]
        if isinstance(hint_value, str) and hint_value.strip():
            hint = hint_value.strip()

    return Flashcard(term=term, definition=definition, hint=hint)


def validate_deck(raw_cards: List[Any]) -> Tuple[List[Flashcard], List[str]]:
    """
    Validate every entry in a deck.

    Duplicate terms are reported but not treated as fatal: the first card
    wins and later ones are skipped, which keeps a mostly-good deck usable.

    Args:
        raw_cards: The raw list of card entries.

    Returns:
        A tuple of the valid cards and the list of problems found.
    """
    errors: List[str] = []
    cards: List[Flashcard] = []
    seen_terms: Dict[str, int] = {}

    for index, raw in enumerate(raw_cards):
        card = validate_card(raw, index, errors)
        if card is None:
            continue

        key = normalize_answer(card.term)
        if key in seen_terms:
            first = seen_terms[key] + 1
            errors.append(
                f"Card {index + 1}: duplicate term '{card.term}' "
                f"(first seen on card {first}); this copy was skipped."
            )
            continue

        seen_terms[key] = index
        cards.append(card)

    if not cards and not errors:
        errors.append("The deck contains no flashcards.")

    return cards, errors
