"""
The quiz mode factory.

Registration lives in one dictionary, so adding a fourth mode means adding
one entry here rather than editing a conditional in the CLI. The CLI asks
the factory for the list of valid names, which keeps ``argparse`` choices
and the registry from drifting apart.
"""

import random
from typing import Dict, List, Optional, Sequence, Type

from flashcards.models import Flashcard
from flashcards.modes.adaptive import AdaptiveMode
from flashcards.modes.base import QuizMode
from flashcards.modes.random_mode import RandomMode
from flashcards.modes.sequential import SequentialMode

DEFAULT_MODE = "sequential"


class QuizModeFactory:
    """Create quiz mode strategies by name."""

    _registry: Dict[str, Type[QuizMode]] = {
        "sequential": SequentialMode,
        "random": RandomMode,
        "adaptive": AdaptiveMode,
    }

    @classmethod
    def available_modes(cls) -> List[str]:
        """Return the registered mode names, in a stable order."""
        return list(cls._registry)

    @classmethod
    def create(
        cls,
        mode_name: str,
        cards: Sequence[Flashcard],
        rng: Optional[random.Random] = None,
    ) -> QuizMode:
        """
        Build the quiz mode registered under ``mode_name``.

        Args:
            mode_name: The mode to create; matched case-insensitively.
            cards: The flashcards the mode will order.
            rng: Optional random source, passed only to modes that use one.
                Supplying it lets tests pin an exact ordering.

        Returns:
            A ready-to-use quiz mode.

        Raises:
            ValueError: If ``mode_name`` is not a registered mode, or if
                the deck is empty.
        """
        key = mode_name.strip().lower()
        mode_class = cls._registry.get(key)

        if mode_class is None:
            valid = ", ".join(cls.available_modes())
            raise ValueError(
                f"Unknown quiz mode '{mode_name}'. Choose one of: {valid}."
            )

        # Only the randomised strategies accept an injected random source;
        # passing one to SequentialMode would be a TypeError.
        if rng is not None and mode_class in (RandomMode, AdaptiveMode):
            return mode_class(cards, rng=rng)  # type: ignore[call-arg]

        return mode_class(cards)
