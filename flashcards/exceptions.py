"""
Exception hierarchy for the flashcard application.

Every error the application raises on purpose derives from
:class:`FlashcardError`, so the command-line layer can catch that single
base class and present a readable message instead of a traceback.
"""

from typing import List, Sequence


class FlashcardError(Exception):
    """Base class for all errors raised by this application."""


class FlashcardFileNotFoundError(FlashcardError):
    """Raised when the requested flashcard file does not exist."""


class FlashcardFileReadError(FlashcardError):
    """Raised when a flashcard file exists but cannot be read."""


class InvalidJSONError(FlashcardError):
    """Raised when a flashcard file does not contain well-formed JSON."""


class ValidationError(FlashcardError):
    """
    Raised when flashcard data is well-formed JSON but semantically invalid.

    Validation collects every problem it finds rather than stopping at the
    first one, so ``errors`` may describe several unrelated bad cards.
    """

    def __init__(self, errors: Sequence[str]) -> None:
        self.errors: List[str] = list(errors)
        count = len(self.errors)
        noun = "problem" if count == 1 else "problems"
        summary = f"Found {count} {noun} in the flashcard data:"
        super().__init__("\n".join([summary, *(f"  - {e}" for e in self.errors)]))
