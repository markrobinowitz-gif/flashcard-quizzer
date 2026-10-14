"""
The abstract quiz mode — the Strategy interface of this application.

A quiz mode owns exactly one decision: *which card comes next*. It knows
nothing about terminals, scoring or input. That narrow responsibility is
what lets :class:`~flashcards.session.QuizSession` run an identical loop no
matter which mode is plugged in.

The interface has two halves:

``next_card``
    Required. Returns the next card, or ``None`` once the mode considers
    the session finished.

``record_result``
    An optional feedback hook, given a concrete no-op implementation here.
    Order-only strategies (sequential, random) have nothing to learn from
    an answer, and forcing them to write an empty override would add noise
    without adding meaning. :class:`~flashcards.modes.adaptive.AdaptiveMode`
    overrides it to re-queue cards the user got wrong.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Sequence

from flashcards.models import Flashcard


class QuizMode(ABC):
    """Abstract base class for quiz ordering strategies."""

    def __init__(self, cards: Sequence[Flashcard]) -> None:
        """
        Store a private copy of the deck.

        Args:
            cards: The flashcards to quiz on.

        Raises:
            ValueError: If the deck is empty.
        """
        if not cards:
            raise ValueError("A quiz needs at least one flashcard.")
        self._cards: List[Flashcard] = list(cards)

    @property
    def cards(self) -> List[Flashcard]:
        """Return a copy of the deck, so callers cannot mutate our state."""
        return list(self._cards)

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the mode's short name, as used on the command line."""

    @property
    @abstractmethod
    def description(self) -> str:
        """Return a one-line description shown when the quiz starts."""

    @abstractmethod
    def next_card(self) -> Optional[Flashcard]:
        """
        Return the next card to ask, or ``None`` when the session is done.

        Implementations must guarantee that repeated calls eventually
        return ``None``, so that the session loop always terminates.
        """

    def record_result(self, card: Flashcard, correct: bool) -> None:
        """
        Observe the outcome of a question.

        The default implementation ignores the result, which is correct for
        any strategy whose order is fixed in advance.

        Args:
            card: The card that was just asked.
            correct: Whether the user answered it correctly.
        """
