"""
Session scoring and the persisted history behind ``--stats``.

:class:`SessionStats` accumulates what happened during one quiz;
:class:`HistoryStore` appends finished sessions to a JSON file so that
``--stats`` can report on past study without running a quiz.

Persistence deliberately reuses :class:`utils.file_handler.FileHandler`
rather than reimplementing JSON I/O, so the new feature builds on the
existing utility layer.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from flashcards.models import Flashcard
from utils.file_handler import FileHandler

HISTORY_FILENAME = "history.json"
SESSIONS_KEY = "sessions"


@dataclass(frozen=True)
class AnswerRecord:
    """One answered question, kept for the end-of-session report."""

    term: str
    expected: str
    given: str
    correct: bool


class SessionStats:
    """Accumulate results for a single quiz session."""

    def __init__(self, mode_name: str = "", deck_name: str = "") -> None:
        """
        Start an empty scoreboard.

        Args:
            mode_name: The quiz mode used, recorded for the history file.
            deck_name: The deck studied, recorded for the history file.
        """
        self.mode_name = mode_name
        self.deck_name = deck_name
        self.started_at = datetime.now()
        self._records: List[AnswerRecord] = []
        self.completed = False

    def record(self, card: Flashcard, given: str, correct: bool) -> None:
        """
        Record the outcome of one question.

        Args:
            card: The card that was asked.
            given: The answer the user typed.
            correct: Whether that answer was accepted.
        """
        self._records.append(
            AnswerRecord(
                term=card.term,
                expected=card.definition,
                given=given,
                correct=correct,
            )
        )

    @property
    def records(self) -> List[AnswerRecord]:
        """Return a copy of the individual answer records."""
        return list(self._records)

    @property
    def total_questions(self) -> int:
        """Return how many questions were answered."""
        return len(self._records)

    @property
    def correct_count(self) -> int:
        """Return how many answers were correct."""
        return sum(1 for r in self._records if r.correct)

    @property
    def incorrect_count(self) -> int:
        """Return how many answers were wrong."""
        return self.total_questions - self.correct_count

    @property
    def accuracy(self) -> float:
        """
        Return the percentage of correct answers, 0.0 to 100.0.

        A session with no questions scores 0.0 rather than raising, so an
        immediately-aborted quiz still reports cleanly.
        """
        if not self._records:
            return 0.0
        return (self.correct_count / self.total_questions) * 100.0

    @property
    def missed_terms(self) -> List[str]:
        """
        Return the terms answered wrongly, in first-missed order.

        A term appears once however many times it was missed, which keeps
        the end-of-session list readable in adaptive mode.
        """
        missed: List[str] = []
        for record in self._records:
            if not record.correct and record.term not in missed:
                missed.append(record.term)
        return missed

    @property
    def missed_records(self) -> List[AnswerRecord]:
        """Return the first wrong answer for each missed term."""
        seen: set = set()
        first_misses: List[AnswerRecord] = []
        for record in self._records:
            if not record.correct and record.term not in seen:
                seen.add(record.term)
                first_misses.append(record)
        return first_misses

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serialisable summary for the history file."""
        return {
            "timestamp": self.started_at.isoformat(timespec="seconds"),
            "deck": self.deck_name,
            "mode": self.mode_name,
            "total_questions": self.total_questions,
            "correct": self.correct_count,
            "accuracy": round(self.accuracy, 1),
            "missed_terms": self.missed_terms,
            "completed": self.completed,
        }


class HistoryStore:
    """Read and append session summaries in a JSON history file."""

    def __init__(
        self,
        data_dir: str = "data",
        file_handler: Optional[FileHandler] = None,
    ) -> None:
        """
        Open (and create if needed) the directory holding the history file.

        Args:
            data_dir: Directory for the history file.
            file_handler: Pre-built handler, mainly for tests.
        """
        self._handler = file_handler or FileHandler(data_dir)

    def load_sessions(self) -> List[Dict[str, Any]]:
        """
        Return every recorded session, oldest first.

        A missing or unreadable history file yields an empty list: losing
        past statistics must never stop the user from studying.
        """
        try:
            data = self._handler.load_data(HISTORY_FILENAME)
        except RuntimeError:
            return []

        sessions = data.get(SESSIONS_KEY, []) if isinstance(data, dict) else []
        return [s for s in sessions if isinstance(s, dict)]

    def append(self, stats: SessionStats) -> None:
        """
        Add one finished session to the history file.

        Args:
            stats: The session to record.

        Raises:
            RuntimeError: If the history file could not be written.
        """
        sessions = self.load_sessions()
        sessions.append(stats.to_dict())
        self._handler.save_data(HISTORY_FILENAME, {SESSIONS_KEY: sessions})


def summarize_history(sessions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Aggregate recorded sessions into the figures ``--stats`` reports.

    Args:
        sessions: Session summaries as returned by ``HistoryStore``.

    Returns:
        Totals across all sessions, plus the most frequently missed terms.
    """
    total_questions = sum(int(s.get("total_questions", 0)) for s in sessions)
    total_correct = sum(int(s.get("correct", 0)) for s in sessions)

    miss_counts: Dict[str, int] = {}
    for session in sessions:
        for term in session.get("missed_terms", []) or []:
            if isinstance(term, str):
                miss_counts[term] = miss_counts.get(term, 0) + 1

    ranked = sorted(miss_counts.items(), key=lambda kv: (-kv[1], kv[0]))

    accuracy = (
        (total_correct / total_questions) * 100.0 if total_questions else 0.0
    )

    return {
        "session_count": len(sessions),
        "total_questions": total_questions,
        "total_correct": total_correct,
        "accuracy": accuracy,
        "toughest_terms": ranked,
    }
