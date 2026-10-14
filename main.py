"""
Entry point for the Flashcard Quizzer.

Argument parsing, error handling and exit codes all live in
:mod:`flashcards.cli`; this module exists so the application can be run as
``python main.py`` and does nothing but forward the process exit code.
"""

import sys

from flashcards.cli import main

if __name__ == "__main__":
    sys.exit(main())
