"""
Adaptive quiz mode: spend more time on the cards the user keeps missing.

Design decisions worth stating explicitly, because "adaptive" is otherwise
an open-ended word:

**Retirement.** A card leaves the pool once it has been answered correctly
once, or once it has been asked :data:`MAX_ATTEMPTS` times. The attempt cap
is what guarantees the session ends — without it, a user who never gets a
card right would be asked it forever.

**Weighting.** Each remaining card is weighted ``1 + misses``, so a card
missed twice is three times as likely to come up as a fresh one. This keeps
the focus on weak material without ever starving the untried cards, which a
strict "hardest first" ordering would do.

**No immediate repeats.** When more than one card remains, the card just
asked is excluded from the draw, so the user is never asked the same
question twice in a row.
"""

import random
from typing import Dict, List, Optional, Sequence

from flashcards.models import Flashcard
from flashcards.modes.base import QuizMode

MAX_ATTEMPTS = 3


class AdaptiveMode(QuizMode):
    """Re-queue missed cards, weighted by how often they were missed."""

    def __init__(
        self,
        cards: Sequence[Flashcard],
        rng: Optional[random.Random] = None,
        max_attempts: int = MAX_ATTEMPTS,
    ) -> None:
        """
        Initialise per-card attempt tracking.

        Args:
            cards: The flashcards to quiz on.
            rng: Random source to use. Defaults to a fresh ``Random``.
            max_attempts: How many times a card may be asked before it is
                retired unanswered.

        Raises:
            ValueError: If the deck is empty or ``max_attempts`` is below 1.
        """
        super().__init__(cards)
        if max_attempts < 1:
            raise ValueError("max_attempts must be at least 1.")

        self._rng = rng if rng is not None else random.Random()
        self._max_attempts = max_attempts
        self._misses: Dict[Flashcard, int] = {c: 0 for c in self._cards}
        self._attempts: Dict[Flashcard, int] = {c: 0 for c in self._cards}
        self._retired: set = set()
        self._last_asked: Optional[Flashcard] = None

    @property
    def name(self) -> str:
        """Return the mode's command-line name."""
        return "adaptive"

    @property
    def description(self) -> str:
        """Return a one-line description of the mode."""
        return (
            "Missed cards come back more often; each card is retired once "
            f"answered correctly or after {self._max_attempts} attempts."
        )

    def _available(self) -> List[Flashcard]:
        """Return the cards still in play, newest misses included."""
        return [c for c in self._cards if c not in self._retired]

    def next_card(self) -> Optional[Flashcard]:
        """
        Draw the next card, favouring those missed most often.

        Returns:
            The next card, or ``None`` once every card has been retired.
        """
        available = self._available()
        if not available:
            return None

        candidates = available
        if len(available) > 1 and self._last_asked in available:
            candidates = [c for c in available if c is not self._last_asked]

        weights = [1 + self._misses[c] for c in candidates]
        card = self._rng.choices(candidates, weights=weights, k=1)[0]
        self._last_asked = card
        return card

    def record_result(self, card: Flashcard, correct: bool) -> None:
        """
        Update attempt counts and retire the card when it is done with.

        Cards that are not part of this deck are ignored, so a caller
        cannot corrupt the mode's state by replaying a foreign card.

        Args:
            card: The card that was just asked.
            correct: Whether the user answered it correctly.
        """
        if card not in self._attempts:
            return

        self._attempts[card] += 1
        if not correct:
            self._misses[card] += 1

        if correct or self._attempts[card] >= self._max_attempts:
            self._retired.add(card)
