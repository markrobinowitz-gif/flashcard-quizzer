"""
All terminal presentation for the quizzer.

Every user-facing string lives here, which keeps the session loop readable
and makes the wording testable in one place.

Colour is written as raw ANSI escapes rather than through a third-party
library, so the application has no runtime dependencies. It is switched off
automatically when output is not a terminal (piped, redirected, or captured
by the test suite) and when the ``NO_COLOR`` convention is in force, so
redirected output stays free of escape sequences.
"""

import os
import sys
from typing import Any, Callable, Dict, List, Optional, Sequence, TextIO

from flashcards.stats import AnswerRecord, SessionStats

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
CYAN = "\033[36m"

SEPARATOR_WIDTH = 52


def supports_color(stream: Optional[TextIO] = None) -> bool:
    """
    Report whether coloured output is appropriate for ``stream``.

    Args:
        stream: The stream to test. Defaults to standard output.

    Returns:
        ``True`` if colour should be emitted.
    """
    if os.environ.get("NO_COLOR") is not None:
        return False

    target = stream if stream is not None else sys.stdout
    try:
        return bool(target.isatty())
    except (AttributeError, ValueError):
        return False


class Display:
    """Render messages, prompts and reports to the terminal."""

    def __init__(
        self,
        output_fn: Callable[[str], None] = print,
        use_color: Optional[bool] = None,
    ) -> None:
        """
        Configure where output goes and whether it is coloured.

        Args:
            output_fn: Callable used to emit a line. Injected so tests can
                capture output without patching built-ins.
            use_color: Force colour on or off. Defaults to auto-detection.
        """
        self._output = output_fn
        self.use_color = supports_color() if use_color is None else use_color

    def paint(self, text: str, *styles: str) -> str:
        """
        Wrap ``text`` in ANSI styles, or return it unchanged.

        Args:
            text: The text to style.
            *styles: ANSI escape sequences to apply.

        Returns:
            The styled text when colour is enabled, else the plain text.
        """
        if not self.use_color or not styles:
            return text
        return f"{''.join(styles)}{text}{RESET}"

    def write(self, text: str = "") -> None:
        """Emit one line of text."""
        self._output(text)

    def heading(self, text: str) -> None:
        """Emit a bold heading between separator rules."""
        self.write()
        self.write(self.paint("=" * SEPARATOR_WIDTH, CYAN))
        self.write(self.paint(text, BOLD, CYAN))
        self.write(self.paint("=" * SEPARATOR_WIDTH, CYAN))

    def info(self, text: str) -> None:
        """Emit an ordinary informational line."""
        self.write(text)

    def muted(self, text: str) -> None:
        """Emit a de-emphasised line."""
        self.write(self.paint(text, DIM))

    def success(self, text: str) -> None:
        """Emit a success line in green."""
        self.write(self.paint(f"✓ {text}", GREEN, BOLD))

    def failure(self, text: str) -> None:
        """Emit a failure line in red."""
        self.write(self.paint(f"✗ {text}", RED, BOLD))

    def warning(self, text: str) -> None:
        """Emit a warning line in yellow."""
        self.write(self.paint(f"! {text}", YELLOW))

    def error(self, text: str) -> None:
        """Emit an error, which may span several lines, in red."""
        for line in str(text).splitlines() or [""]:
            self.write(self.paint(line, RED))

    def welcome(self, deck_name: str, mode_name: str, description: str,
                card_count: int) -> None:
        """
        Announce the start of a quiz.

        Args:
            deck_name: Name of the deck being studied.
            mode_name: Name of the quiz mode.
            description: One-line description of the mode.
            card_count: How many cards the deck holds.
        """
        self.heading("Flashcard Quizzer")
        noun = "card" if card_count == 1 else "cards"
        self.info(f"Deck: {deck_name}  ({card_count} {noun})")
        self.info(f"Mode: {mode_name} — {description}")
        self.muted("Type your answer and press Enter.")
        self.muted("Type 'exit' or press Ctrl+C to stop early.")
        self.write()

    def question(self, number: int, term: str, hint: Optional[str]) -> str:
        """
        Render a question and return the prompt to read input with.

        Args:
            number: The 1-based question number.
            term: The term being asked.
            hint: An optional hint to show beneath the term.

        Returns:
            The prompt string for the input call.
        """
        self.write(
            f"{self.paint(f'Q{number}.', BOLD)} "
            f"What is: {self.paint(term, CYAN, BOLD)}"
        )
        if hint:
            self.muted(f"   hint: {hint}")
        return "   Your answer: "

    def feedback(self, correct: bool, expected: str) -> None:
        """
        Report whether an answer was right, showing the expected text.

        Args:
            correct: Whether the answer was accepted.
            expected: The card's definition.
        """
        if correct:
            self.success("Correct!")
        else:
            self.failure(f"Not quite — the answer is: {expected}")
        self.write()

    def warnings(self, messages: Sequence[str]) -> None:
        """
        Report non-fatal problems found while loading a deck.

        Args:
            messages: The warning messages to show.
        """
        if not messages:
            return
        count = len(messages)
        noun = "card was" if count == 1 else "cards were"
        self.warning(f"{count} {noun} skipped while loading the deck:")
        for message in messages:
            self.muted(f"   {message}")
        self.write()

    def _missed_section(self, missed: List[AnswerRecord]) -> None:
        """Render the list of missed terms and their answers."""
        if not missed:
            self.success("Nothing missed — every card answered correctly.")
            return

        count = len(missed)
        noun = "term" if count == 1 else "terms"
        self.write(self.paint(f"Missed {noun} ({count}):", BOLD))
        for record in missed:
            self.write(f"   • {self.paint(record.term, YELLOW)}")
            self.muted(f"       expected: {record.expected}")
            given = record.given.strip() or "(no answer)"
            self.muted(f"       you said: {given}")

    def session_report(self, stats: SessionStats) -> None:
        """
        Render the end-of-session statistics.

        Args:
            stats: The finished session's scoreboard.
        """
        self.heading("Session Statistics")

        if stats.total_questions == 0:
            self.muted("No questions were answered.")
            self.write()
            return

        accuracy = f"{stats.accuracy:.1f}%"
        accuracy_style = (
            GREEN if stats.accuracy >= 80 else
            YELLOW if stats.accuracy >= 50 else RED
        )
        self.info(f"Total questions: {stats.total_questions}")
        self.info(f"Correct:         {stats.correct_count}")
        self.info(f"Incorrect:       {stats.incorrect_count}")
        self.info(f"Accuracy:        {self.paint(accuracy, accuracy_style)}")
        self.write()
        self._missed_section(stats.missed_records)
        self.write()

    def history_report(
        self, summary: Dict[str, Any], limit: int = 5
    ) -> None:
        """
        Render aggregated statistics from previous sessions.

        Args:
            summary: Aggregate produced by ``summarize_history``.
            limit: How many of the toughest terms to list.
        """
        self.heading("Study History")

        if not summary["session_count"]:
            self.muted("No sessions recorded yet.")
            self.muted("Run a quiz first, then check back with --stats.")
            self.write()
            return

        accuracy = f"{summary['accuracy']:.1f}%"
        self.info(f"Sessions recorded: {summary['session_count']}")
        self.info(f"Questions answered: {summary['total_questions']}")
        self.info(f"Correct:            {summary['total_correct']}")
        self.info(f"Overall accuracy:   {self.paint(accuracy, BOLD)}")

        toughest = summary["toughest_terms"][:limit]
        if toughest:
            self.write()
            self.write(self.paint("Most frequently missed:", BOLD))
            for term, count in toughest:
                times = "session" if count == 1 else "sessions"
                self.write(
                    f"   • {self.paint(term, YELLOW)} "
                    f"— missed in {count} {times}"
                )
        self.write()
