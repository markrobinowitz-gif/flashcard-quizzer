"""Unit tests for terminal presentation and colour handling."""

import io

import pytest

from flashcards.display import GREEN, RED, Display, supports_color
from flashcards.models import Flashcard
from flashcards.stats import SessionStats, summarize_history


@pytest.fixture
def captured():
    """Return a display writing into a list, plus that list."""
    lines = []
    return Display(output_fn=lines.append, use_color=False), lines


class TestSupportsColor:
    """Test suite for colour auto-detection."""

    def test_no_color_env_disables_colour(self, monkeypatch) -> None:
        """Test that the NO_COLOR convention is honoured."""
        monkeypatch.setenv("NO_COLOR", "1")
        assert supports_color(io.StringIO()) is False

    def test_non_tty_stream_disables_colour(self, monkeypatch) -> None:
        """Test that redirected output is left plain."""
        monkeypatch.delenv("NO_COLOR", raising=False)
        assert supports_color(io.StringIO()) is False

    def test_tty_stream_enables_colour(self, monkeypatch) -> None:
        """Test that a real terminal gets colour."""
        monkeypatch.delenv("NO_COLOR", raising=False)

        class FakeTTY:
            def isatty(self) -> bool:
                return True

        assert supports_color(FakeTTY()) is True

    def test_stream_without_isatty_is_safe(self, monkeypatch) -> None:
        """Test that an odd stream does not raise."""
        monkeypatch.delenv("NO_COLOR", raising=False)
        assert supports_color(object()) is False


class TestPaint:
    """Test suite for the colour wrapper."""

    def test_colour_disabled_returns_plain_text(self, captured) -> None:
        """Test that no escape codes leak into plain output."""
        display, _ = captured
        assert display.paint("hello", GREEN) == "hello"

    def test_colour_enabled_wraps_text(self) -> None:
        """Test that styles are applied and reset."""
        display = Display(output_fn=lambda _: None, use_color=True)
        painted = display.paint("hello", RED)
        assert painted.startswith(RED)
        assert painted.endswith("\033[0m")

    def test_no_styles_returns_plain_text(self) -> None:
        """Test the no-style shortcut."""
        display = Display(output_fn=lambda _: None, use_color=True)
        assert display.paint("hello") == "hello"


class TestMessages:
    """Test suite for the individual message helpers."""

    def test_success_and_failure_are_marked(self, captured) -> None:
        """Test that feedback lines carry a visible marker."""
        display, lines = captured
        display.success("Correct!")
        display.failure("Nope")
        assert lines[0].startswith("✓")
        assert lines[1].startswith("✗")

    def test_feedback_shows_expected_answer_when_wrong(
        self, captured
    ) -> None:
        """Test that a wrong answer reveals the definition."""
        display, lines = captured
        display.feedback(False, "the answer")
        assert "the answer" in lines[0]

    def test_feedback_does_not_reveal_answer_when_correct(
        self, captured
    ) -> None:
        """Test that a correct answer does not repeat the definition."""
        display, lines = captured
        display.feedback(True, "the answer")
        assert "the answer" not in lines[0]

    def test_question_renders_term_and_returns_prompt(
        self, captured
    ) -> None:
        """Test that the question is shown and a prompt returned."""
        display, lines = captured
        prompt = display.question(1, "alpha", None)
        assert "alpha" in lines[0]
        assert "Q1." in lines[0]
        assert "answer" in prompt.lower()

    def test_question_shows_hint_when_present(self, captured) -> None:
        """Test that a hint is displayed beneath the term."""
        display, lines = captured
        display.question(1, "alpha", "a clue")
        assert any("a clue" in line for line in lines)

    def test_error_handles_multiline_messages(self, captured) -> None:
        """Test that a multi-line validation error prints every line."""
        display, lines = captured
        display.error("line one\nline two")
        assert lines == ["line one", "line two"]

    def test_warnings_are_skipped_when_empty(self, captured) -> None:
        """Test that a clean load prints nothing."""
        display, lines = captured
        display.warnings([])
        assert lines == []

    def test_warnings_are_listed_with_a_count(self, captured) -> None:
        """Test that skipped cards are summarised and listed."""
        display, lines = captured
        display.warnings(["bad card 1", "bad card 2"])
        text = "\n".join(lines)
        assert "2 cards were skipped" in text
        assert "bad card 1" in text

    def test_welcome_names_deck_and_mode(self, captured) -> None:
        """Test that the banner identifies the session."""
        display, lines = captured
        display.welcome("deck", "random", "shuffled", 3)
        text = "\n".join(lines)
        assert "deck" in text and "random" in text and "3 cards" in text


class TestSessionReport:
    """Test suite for the end-of-session statistics block."""

    def test_reports_totals_and_accuracy(self, captured) -> None:
        """Test that the required figures all appear."""
        display, lines = captured
        stats = SessionStats()
        stats.record(Flashcard("a", "1"), "1", True)
        stats.record(Flashcard("b", "2"), "x", False)
        display.session_report(stats)
        text = "\n".join(lines)
        assert "Total questions: 2" in text
        assert "50.0%" in text

    def test_lists_missed_terms_with_answers(self, captured) -> None:
        """Test that missed terms show expected and given answers."""
        display, lines = captured
        stats = SessionStats()
        stats.record(Flashcard("beta", "second"), "wrong", False)
        display.session_report(stats)
        text = "\n".join(lines)
        assert "beta" in text
        assert "second" in text
        assert "wrong" in text

    def test_blank_answer_is_labelled(self, captured) -> None:
        """Test that an empty answer reads clearly in the report."""
        display, lines = captured
        stats = SessionStats()
        stats.record(Flashcard("beta", "second"), "   ", False)
        display.session_report(stats)
        assert "(no answer)" in "\n".join(lines)

    def test_perfect_session_says_nothing_missed(self, captured) -> None:
        """Test the all-correct message."""
        display, lines = captured
        stats = SessionStats()
        stats.record(Flashcard("a", "1"), "1", True)
        display.session_report(stats)
        assert "Nothing missed" in "\n".join(lines)

    def test_empty_session_is_reported_gracefully(self, captured) -> None:
        """Test that an aborted session still prints a clean report."""
        display, lines = captured
        display.session_report(SessionStats())
        assert "No questions were answered." in "\n".join(lines)


class TestHistoryReport:
    """Test suite for the --stats report."""

    def test_empty_history_explains_itself(self, captured) -> None:
        """Test the first-run message."""
        display, lines = captured
        display.history_report(summarize_history([]))
        assert "No sessions recorded yet." in "\n".join(lines)

    def test_reports_aggregate_figures(self, captured) -> None:
        """Test that totals across sessions are shown."""
        display, lines = captured
        summary = summarize_history(
            [{"total_questions": 4, "correct": 3, "missed_terms": ["hard"]}]
        )
        display.history_report(summary)
        text = "\n".join(lines)
        assert "Sessions recorded: 1" in text
        assert "75.0%" in text
        assert "hard" in text

    def test_toughest_terms_are_limited(self, captured) -> None:
        """Test that the list honours the limit argument."""
        display, lines = captured
        summary = summarize_history(
            [{"missed_terms": ["a", "b", "c", "d"]}]
        )
        display.history_report(summary, limit=2)
        text = "\n".join(lines)
        assert "• " in text
        assert text.count("missed in") == 2
