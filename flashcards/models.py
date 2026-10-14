"""
Immutable data types shared across the application.

Keeping these free of I/O and of any knowledge about quiz modes means they
can be constructed cheaply in tests without touching the filesystem.
"""

import re
from dataclasses import dataclass
from typing import Optional

_WHITESPACE_RUN = re.compile(r"\s+")


def normalize_answer(text: str) -> str:
    """
    Reduce an answer to the form used for comparison.

    Comparison is case-insensitive and tolerant of stray whitespace, so
    ``"  Binary   Search "`` and ``"binary search"`` are treated as equal.
    ``str.casefold`` is used rather than ``str.lower`` because it folds
    non-ASCII characters correctly (for example the German "ß").

    Args:
        text: The raw text to normalise.

    Returns:
        The normalised comparison key.
    """
    return _WHITESPACE_RUN.sub(" ", text.strip()).casefold()


@dataclass(frozen=True)
class Flashcard:
    """
    A single question/answer pair.

    Frozen so that a card can be used as a dictionary key and cannot be
    mutated by a quiz mode while a session is in progress.
    """

    term: str
    definition: str
    hint: Optional[str] = None

    def is_correct(self, answer: str) -> bool:
        """
        Report whether ``answer`` matches this card's definition.

        Args:
            answer: The text the user typed.

        Returns:
            ``True`` if the answer matches case-insensitively.
        """
        return normalize_answer(answer) == normalize_answer(self.definition)
