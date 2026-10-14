"""Unit tests for session scoring and persisted history."""

import pytest

from flashcards.models import Flashcard
from flashcards.stats import (
    HistoryStore,
    SessionStats,
    summarize_history,
)
from utils.file_handler import FileHandler


@pytest.fixture
def card() -> Flashcard:
    """Return a single card for recording results against."""
    return Flashcard("alpha", "first")


class TestSessionStats:
    """Test suite for SessionStats."""

    def test_empty_session_reports_zeroes(self) -> None:
        """Test that a session with no answers does not divide by zero."""
        stats = SessionStats()
        assert stats.total_questions == 0
        assert stats.correct_count == 0
        assert stats.incorrect_count == 0
        assert stats.accuracy == 0.0
        assert stats.missed_terms == []

    def test_counts_correct_and_incorrect(self, card, sample_cards) -> None:
        """Test the basic tallies."""
        stats = SessionStats()
        stats.record(card, "first", True)
        stats.record(sample_cards[1], "wrong", False)
        assert stats.total_questions == 2
        assert stats.correct_count == 1
        assert stats.incorrect_count == 1

    def test_accuracy_percentage(self, sample_cards) -> None:
        """Test that accuracy is a percentage, not a fraction."""
        stats = SessionStats()
        stats.record(sample_cards[0], "a", True)
        stats.record(sample_cards[1], "b", True)
        stats.record(sample_cards[2], "c", False)
        assert stats.accuracy == pytest.approx(66.666, rel=1e-3)

    def test_perfect_session_is_one_hundred_percent(self, card) -> None:
        """Test the upper bound of accuracy."""
        stats = SessionStats()
        stats.record(card, "first", True)
        assert stats.accuracy == 100.0

    def test_missed_terms_are_unique_and_ordered(self, sample_cards) -> None:
        """Test that a repeated miss is listed once, in first-miss order."""
        stats = SessionStats()
        stats.record(sample_cards[1], "x", False)
        stats.record(sample_cards[0], "y", False)
        stats.record(sample_cards[1], "z", False)
        assert stats.missed_terms == ["beta", "alpha"]

    def test_correct_terms_are_not_listed_as_missed(self, card) -> None:
        """Test that correct answers stay out of the missed list."""
        stats = SessionStats()
        stats.record(card, "first", True)
        assert stats.missed_terms == []

    def test_missed_records_keep_the_first_wrong_answer(
        self, sample_cards
    ) -> None:
        """Test that the report shows what the user first typed."""
        stats = SessionStats()
        stats.record(sample_cards[0], "first try", False)
        stats.record(sample_cards[0], "second try", False)
        records = stats.missed_records
        assert len(records) == 1
        assert records[0].given == "first try"
        assert records[0].expected == "first"

    def test_records_property_is_a_copy(self, card) -> None:
        """Test that callers cannot clear the internal record list."""
        stats = SessionStats()
        stats.record(card, "first", True)
        stats.records.clear()
        assert stats.total_questions == 1

    def test_to_dict_is_json_serialisable(self, card) -> None:
        """Test the shape written to the history file."""
        stats = SessionStats(mode_name="random", deck_name="deck")
        stats.record(card, "wrong", False)
        stats.completed = True
        data = stats.to_dict()
        assert data["mode"] == "random"
        assert data["deck"] == "deck"
        assert data["total_questions"] == 1
        assert data["correct"] == 0
        assert data["accuracy"] == 0.0
        assert data["missed_terms"] == ["alpha"]
        assert data["completed"] is True


class TestHistoryStore:
    """Test suite for reading and appending session history."""

    def test_missing_history_file_yields_no_sessions(self, tmp_path) -> None:
        """Test that a first run reads cleanly."""
        store = HistoryStore(str(tmp_path))
        assert store.load_sessions() == []

    def test_append_then_load_round_trip(self, tmp_path, card) -> None:
        """Test that an appended session can be read back."""
        store = HistoryStore(str(tmp_path))
        stats = SessionStats(mode_name="sequential", deck_name="deck")
        stats.record(card, "first", True)
        store.append(stats)
        sessions = store.load_sessions()
        assert len(sessions) == 1
        assert sessions[0]["correct"] == 1

    def test_appending_accumulates_sessions(self, tmp_path, card) -> None:
        """Test that history grows rather than being overwritten."""
        store = HistoryStore(str(tmp_path))
        for _ in range(3):
            stats = SessionStats()
            stats.record(card, "first", True)
            store.append(stats)
        assert len(store.load_sessions()) == 3

    def test_corrupt_history_is_ignored(self, tmp_path) -> None:
        """Test that unreadable history never blocks studying."""
        (tmp_path / "history.json").write_text("{not json", encoding="utf-8")
        assert HistoryStore(str(tmp_path)).load_sessions() == []

    def test_non_dict_entries_are_filtered_out(self, tmp_path) -> None:
        """Test that junk entries are skipped."""
        handler = FileHandler(str(tmp_path))
        handler.save_data("history.json", {"sessions": [{"correct": 1}, "x"]})
        assert len(HistoryStore(str(tmp_path)).load_sessions()) == 1

    def test_accepts_an_injected_file_handler(self, tmp_path, card) -> None:
        """Test that the store can reuse a caller's FileHandler."""
        store = HistoryStore(file_handler=FileHandler(str(tmp_path)))
        stats = SessionStats()
        stats.record(card, "first", True)
        store.append(stats)
        assert (tmp_path / "history.json").exists()


class TestSummarizeHistory:
    """Test suite for aggregating recorded sessions."""

    def test_empty_history_summarises_to_zeroes(self) -> None:
        """Test that no history does not divide by zero."""
        summary = summarize_history([])
        assert summary["session_count"] == 0
        assert summary["total_questions"] == 0
        assert summary["accuracy"] == 0.0
        assert summary["toughest_terms"] == []

    def test_totals_across_sessions(self) -> None:
        """Test that questions and correct answers are summed."""
        summary = summarize_history(
            [
                {"total_questions": 4, "correct": 2, "missed_terms": ["a"]},
                {"total_questions": 6, "correct": 6, "missed_terms": []},
            ]
        )
        assert summary["session_count"] == 2
        assert summary["total_questions"] == 10
        assert summary["total_correct"] == 8
        assert summary["accuracy"] == 80.0

    def test_toughest_terms_ranked_by_frequency(self) -> None:
        """Test that the most-missed term sorts first."""
        summary = summarize_history(
            [
                {"missed_terms": ["hard", "easy"]},
                {"missed_terms": ["hard"]},
            ]
        )
        assert summary["toughest_terms"][0] == ("hard", 2)
        assert summary["toughest_terms"][1] == ("easy", 1)

    def test_missing_and_null_fields_are_tolerated(self) -> None:
        """Test that partial history entries do not crash the summary."""
        summary = summarize_history([{}, {"missed_terms": None}])
        assert summary["session_count"] == 2
        assert summary["total_questions"] == 0

    def test_non_string_terms_are_skipped(self) -> None:
        """Test that junk inside missed_terms is ignored."""
        summary = summarize_history([{"missed_terms": ["ok", 7, None]}])
        assert summary["toughest_terms"] == [("ok", 1)]
