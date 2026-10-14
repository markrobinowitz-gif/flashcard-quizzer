"""
Quiz mode strategies and the factory that selects between them.

Re-exported here so callers can write ``from flashcards.modes import
QuizModeFactory`` without knowing which module each strategy lives in.
"""

from flashcards.modes.adaptive import AdaptiveMode
from flashcards.modes.base import QuizMode
from flashcards.modes.factory import QuizModeFactory
from flashcards.modes.random_mode import RandomMode
from flashcards.modes.sequential import SequentialMode

__all__ = [
    "AdaptiveMode",
    "QuizMode",
    "QuizModeFactory",
    "RandomMode",
    "SequentialMode",
]
