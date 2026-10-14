"""
The quiz loop.

:class:`QuizSession` is deliberately ignorant of *which* cards it asks —
that is the quiz mode's job — and of *how* text reaches the screen — that
is the display's job. What it owns is the turn structure: ask, read, judge,
report, feed the result back to the mode.

Input and output are injected rather than calling ``input``/``print``
directly, so the whole loop can be exercised in tests with scripted
answers and captured output.
"""

from typing import Callable, Optional, Sequence

from flashcards.display import Display
from flashcards.models import normalize_answer
from flashcards.modes.base import QuizMode
from flashcards.stats import SessionStats

EXIT_COMMANDS = frozenset({"exit", "quit"})


class QuizSession:
    """Run a quiz from a mode, reporting through a display."""

    def __init__(
        self,
        mode: QuizMode,
        display: Display,
        input_fn: Callable[[str], str] = input,
        deck_name: str = "",
    ) -> None:
        """
        Wire a session together.

        Args:
            mode: The strategy deciding which card comes next.
            display: Where output is written.
            input_fn: Callable used to read one line from the user.
            deck_name: Name of the deck, recorded in the statistics.
        """
        self._mode = mode
        self._display = display
        self._input = input_fn
        self.stats = SessionStats(mode_name=mode.name, deck_name=deck_name)

    def _read_answer(self, prompt: str) -> Optional[str]:
        """
        Read one answer from the user.

        Returns:
            The text typed, or ``None`` if the user asked to stop. Ctrl+C
            and end-of-input are both treated as "stop", so a piped or
            closed stdin ends the quiz cleanly instead of raising.
        """
        try:
            return self._input(prompt)
        except (EOFError, KeyboardInterrupt):
            return None

    def run(self, warnings: Sequence[str] = ()) -> SessionStats:
        """
        Ask questions until the mode is done or the user stops.

        Args:
            warnings: Deck-loading warnings to show before the first card.

        Returns:
            The session statistics, whether or not the quiz was completed.
        """
        self._display.welcome(
            deck_name=self.stats.deck_name,
            mode_name=self._mode.name,
            description=self._mode.description,
            card_count=len(self._mode.cards),
        )
        self._display.warnings(warnings)

        question_number = 0
        while True:
            card = self._mode.next_card()
            if card is None:
                self.stats.completed = True
                break

            question_number += 1
            prompt = self._display.question(
                question_number, card.term, card.hint
            )
            answer = self._read_answer(prompt)

            if answer is None or normalize_answer(answer) in EXIT_COMMANDS:
                self._display.write()
                self._display.muted("Session ended early.")
                break

            correct = card.is_correct(answer)
            self._display.feedback(correct, card.definition)
            self._mode.record_result(card, correct)
            self.stats.record(card, answer, correct)

        self._display.session_report(self.stats)
        return self.stats
