"""Sequential quiz mode: ask every card once, in file order."""

from typing import Optional, Sequence

from flashcards.models import Flashcard
from flashcards.modes.base import QuizMode


class SequentialMode(QuizMode):
    """Ask each card exactly once, in the order it appears in the deck."""

    def __init__(self, cards: Sequence[Flashcard]) -> None:
        """Initialise the deck and the read position."""
        super().__init__(cards)
        self._position = 0

    @property
    def name(self) -> str:
        """Return the mode's command-line name."""
        return "sequential"

    @property
    def description(self) -> str:
        """Return a one-line description of the mode."""
        return "Cards in file order, each asked once."

    def next_card(self) -> Optional[Flashcard]:
        """
        Return the card at the current position and advance.

        Returns:
            The next card, or ``None`` once the deck is exhausted.
        """
        if self._position >= len(self._cards):
            return None

        card = self._cards[self._position]
        self._position += 1
        return card
