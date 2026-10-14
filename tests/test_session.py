"""
Unit tests for the quiz loop.

Input and output are both injected, so every path through the loop is
driven with scripted answers and asserted on captured output.
"""

from typing import List

import pytest

from flashcards.display import Display
from flashcards.models import Flashcard
from flashcards.modes.sequential import SequentialMode
from flashcards.session import QuizSession


def make_session(cards, answers: List[str], deck_name: str = "deck"):
    """Build a session driven by a fixed list of answers."""
    lines: List[str] = []
    display = Display(output_fn=lines.append, use_color=False)
    supply = iter(answers)

    def fake_input(_prompt: str) -> str:
        return next(supply)

    session = QuizSession(
        mode=SequentialMode(cards),
        display=display,
        input_fn=fake_input,
        deck_name=deck_name,
    )
    return session, lines


class TestQuizSessionHappyPath:
    """Test suite for ordinary completed sessions."""

    def test_all_correct_session(self, sample_cards) -> None:
        """Test that correct answers are scored and the session completes."""
        session, _ = make_session(
            sample_cards, ["first", "second", "third"]
        )
        stats = session.run()
        assert stats.total_questions == 3
        assert stats.correct_count == 3
        assert stats.accuracy == 100.0
        assert stats.completed is True

    def test_mixed_results_are_scored(self, sample_cards) -> None:
        """Test that wrong answers are counted and listed."""
        session, _ = make_session(sample_cards, ["first", "nope", "third"])
        stats = session.run()
        assert stats.correct_count == 2
        assert stats.missed_terms == ["beta"]

    def test_answers_are_compared_case_insensitively(self) -> None:
        """Test the headline answer-matching requirement."""
        cards = [Flashcard("term", "Binary Search")]
        session, _ = make_session(cards, ["   bInArY   seaRCH  "])
        assert session.run().correct_count == 1

    def test_feedback_is_shown_for_each_question(
        self, sample_cards
    ) -> None:
        """Test that the user gets immediate feedback per answer."""
        session, lines = make_session(
            sample_cards, ["first", "nope", "third"]
        )
        session.run()
        text = "\n".join(lines)
        assert text.count("✓ Correct!") == 2
        assert text.count("✗ Not quite") == 1

    def test_deck_name_reaches_the_statistics(self, sample_cards) -> None:
        """Test that the deck is recorded for the history file."""
        session, _ = make_session(
            sample_cards, ["first", "second", "third"], deck_name="algos"
        )
        assert session.run().deck_name == "algos"

    def test_warnings_are_displayed_before_the_quiz(
        self, sample_cards
    ) -> None:
        """Test that loader warnings are surfaced to the user."""
        session, lines = make_session(
            sample_cards, ["first", "second", "third"]
        )
        session.run(["card 4 was skipped"])
        assert "card 4 was skipped" in "\n".join(lines)

    def test_report_is_printed_at_the_end(self, sample_cards) -> None:
        """Test that statistics are always shown."""
        session, lines = make_session(
            sample_cards, ["first", "second", "third"]
        )
        session.run()
        assert "Session Statistics" in "\n".join(lines)


class TestQuizSessionExitPaths:
    """Test suite for the ways a session can end early."""

    @pytest.mark.parametrize("command", ["exit", "EXIT", "  quit  ", "Quit"])
    def test_exit_command_stops_the_quiz(
        self, command, sample_cards
    ) -> None:
        """Test that the exit keyword ends the session cleanly."""
        session, lines = make_session(sample_cards, ["first", command])
        stats = session.run()
        assert stats.total_questions == 1
        assert stats.completed is False
        assert "Session ended early." in "\n".join(lines)

    def test_keyboard_interrupt_is_handled(self, sample_cards) -> None:
        """Test that Ctrl+C ends the session instead of raising."""

        def interrupt(_prompt: str) -> str:
            raise KeyboardInterrupt

        lines: List[str] = []
        session = QuizSession(
            mode=SequentialMode(sample_cards),
            display=Display(output_fn=lines.append, use_color=False),
            input_fn=interrupt,
        )
        stats = session.run()
        assert stats.total_questions == 0
        assert "Session ended early." in "\n".join(lines)

    def test_end_of_input_is_handled(self, sample_cards) -> None:
        """Test that closed or piped stdin ends the session cleanly."""

        def eof(_prompt: str) -> str:
            raise EOFError

        lines: List[str] = []
        session = QuizSession(
            mode=SequentialMode(sample_cards),
            display=Display(output_fn=lines.append, use_color=False),
            input_fn=eof,
        )
        assert session.run().total_questions == 0

    def test_statistics_are_still_reported_after_exit(
        self, sample_cards
    ) -> None:
        """Test that quitting early still shows what was answered."""
        session, lines = make_session(sample_cards, ["nope", "exit"])
        session.run()
        text = "\n".join(lines)
        assert "Total questions: 1" in text
        assert "alpha" in text

    def test_empty_answer_is_treated_as_an_attempt(self) -> None:
        """Test that pressing Enter counts as a wrong answer, not a quit."""
        cards = [Flashcard("term", "definition")]
        session, _ = make_session(cards, [""])
        stats = session.run()
        assert stats.total_questions == 1
        assert stats.correct_count == 0


class TestQuizSessionModeIntegration:
    """Test suite for the session's contract with the mode."""

    def test_results_are_fed_back_to_the_mode(self, sample_cards) -> None:
        """Test that the mode is told the outcome of each question."""
        recorded = []

        class SpyMode(SequentialMode):
            def record_result(self, card, correct) -> None:
                recorded.append((card.term, correct))

        lines: List[str] = []
        supply = iter(["first", "nope", "third"])
        session = QuizSession(
            mode=SpyMode(sample_cards),
            display=Display(output_fn=lines.append, use_color=False),
            input_fn=lambda _p: next(supply),
        )
        session.run()
        assert recorded == [
            ("alpha", True),
            ("beta", False),
            ("gamma", True),
        ]

    def test_questions_are_numbered_sequentially(
        self, sample_cards
    ) -> None:
        """Test that question numbers increase as the quiz proceeds."""
        session, lines = make_session(
            sample_cards, ["first", "second", "third"]
        )
        session.run()
        text = "\n".join(lines)
        assert "Q1." in text and "Q2." in text and "Q3." in text
