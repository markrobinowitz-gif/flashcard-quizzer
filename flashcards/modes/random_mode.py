"""Random quiz mode: ask every card once, in shuffled order."""

import random
from typing import List, Optional, Sequence

from flashcards.models import Flashcard
from flashcards.modes.base import QuizMode


class RandomMode(QuizMode):
    """
    Ask each card exactly once, in a random order.

    The random source is injectable so tests can pin a seed and assert on
    an exact ordering rather than on statistical properties.
    """

    def __init__(
        self,
        cards: Sequence[Flashcard],
        rng: Optional[random.Random] = None,
    ) -> None:
        """
        Shuffle a copy of the deck up front.

        Args:
            cards: The flashcards to quiz on.
            rng: Random source to use. Defaults to a fresh ``Random``.
        """
        super().__init__(cards)
        self._rng = rng if rng is not None else random.Random()
        self._queue: List[Flashcard] = list(self._cards)
        self._rng.shuffle(self._queue)
        self._position = 0

    @property
    def name(self) -> str:
        """Return the mode's command-line name."""
        return "random"

    @property
    def description(self) -> str:
        """Return a one-line description of the mode."""
        return "Cards in random order, each asked once."

    def next_card(self) -> Optional[Flashcard]:
        """
        Return the next card from the shuffled queue.

        Returns:
            The next card, or ``None`` once every card has been asked.
        """
        if self._position >= len(self._queue):
            return None

        card = self._queue[self._position]
        self._position += 1
        return card
