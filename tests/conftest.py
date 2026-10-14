"""Shared pytest fixtures for the flashcard test suite."""

from pathlib import Path
from typing import List

import pytest

from flashcards.models import Flashcard

FIXTURE_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixture_path():
    """Return a callable that resolves a fixture file name to a path."""

    def _resolve(name: str) -> Path:
        return FIXTURE_DIR / name

    return _resolve


@pytest.fixture
def sample_cards() -> List[Flashcard]:
    """Return a small, predictable deck for mode and session tests."""
    return [
        Flashcard("alpha", "first"),
        Flashcard("beta", "second"),
        Flashcard("gamma", "third"),
    ]
