"""
Flashcard Quizzer — a command-line study tool.

The package is organised in layers, each depending only on the ones above
it: ``exceptions``/``models`` carry no logic, ``validator`` and ``loader``
turn raw JSON into validated :class:`~flashcards.models.Flashcard` objects,
``modes`` selects which card comes next, ``session`` runs the quiz loop, and
``cli`` wires everything to the command line.
"""

__version__ = "1.0.0"
