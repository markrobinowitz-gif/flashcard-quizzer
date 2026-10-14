"""
Command-line interface for the Flashcard Quizzer.

This module owns argument parsing and is the single place where
application errors are turned into readable messages and exit codes. Every
expected failure is caught here, so the user never sees a traceback.

Exit codes follow the usual command-line convention:

* ``0`` — the quiz ran (or history was shown) successfully
* ``1`` — a runtime problem, such as an unreadable or invalid deck
* ``2`` — a usage problem, raised by ``argparse`` itself
"""

import argparse
import random
from pathlib import Path
from typing import Optional, Sequence

from flashcards import __version__
from flashcards.display import Display
from flashcards.exceptions import FlashcardError
from flashcards.loader import load_flashcards_with_warnings
from flashcards.modes.factory import DEFAULT_MODE, QuizModeFactory
from flashcards.session import QuizSession
from flashcards.stats import HistoryStore, summarize_history

EXIT_OK = 0
EXIT_ERROR = 1


def build_parser() -> argparse.ArgumentParser:
    """
    Construct the argument parser.

    Mode choices are taken from the factory registry rather than written
    out again here, so the two cannot drift apart.

    Returns:
        The configured parser.
    """
    parser = argparse.ArgumentParser(
        prog="flashcards",
        description="Study a deck of flashcards from the command line.",
        epilog=(
            "Examples:\n"
            "  python main.py -f examples/flashcards.json\n"
            "  python main.py -f deck.json -m random\n"
            "  python main.py -f deck.json -m adaptive\n"
            "  python main.py --stats\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "-f",
        "--file",
        dest="file",
        metavar="PATH",
        help="Path to a JSON flashcard file.",
    )
    parser.add_argument(
        "-m",
        "--mode",
        dest="mode",
        default=DEFAULT_MODE,
        choices=QuizModeFactory.available_modes(),
        help=f"Quiz mode to use (default: {DEFAULT_MODE}).",
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show statistics from previous sessions and exit.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        metavar="N",
        help="Seed the random source, for reproducible card order.",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable coloured output.",
    )
    parser.add_argument(
        "--data-dir",
        default="data",
        metavar="PATH",
        help="Directory holding the session history (default: data).",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return parser


def _make_display(args: argparse.Namespace) -> Display:
    """Build a display honouring the --no-color flag."""
    return Display(use_color=False if args.no_color else None)


def _show_history(args: argparse.Namespace, display: Display) -> int:
    """
    Print aggregated statistics from previous sessions.

    Args:
        args: Parsed command-line arguments.
        display: Where to write the report.

    Returns:
        The process exit code.
    """
    store = HistoryStore(args.data_dir)
    display.history_report(summarize_history(store.load_sessions()))
    return EXIT_OK


def _run_quiz(args: argparse.Namespace, display: Display) -> int:
    """
    Load a deck, run one quiz session, and record the result.

    Args:
        args: Parsed command-line arguments.
        display: Where to write the quiz.

    Returns:
        The process exit code.
    """
    cards, warnings = load_flashcards_with_warnings(args.file)
    rng = random.Random(args.seed) if args.seed is not None else None
    mode = QuizModeFactory.create(args.mode, cards, rng=rng)

    session = QuizSession(
        mode=mode,
        display=display,
        deck_name=Path(args.file).stem,
    )
    stats = session.run(warnings)

    if stats.total_questions:
        try:
            HistoryStore(args.data_dir).append(stats)
        except (RuntimeError, OSError) as exc:
            # Failing to save history must not fail the quiz the user
            # has just completed; warn and carry on.
            display.warning(f"Could not save session history: {exc}")

    return EXIT_OK


def main(argv: Optional[Sequence[str]] = None) -> int:
    """
    Run the application.

    Args:
        argv: Argument list, defaulting to ``sys.argv[1:]``.

    Returns:
        The process exit code.
    """
    parser = build_parser()
    args = parser.parse_args(argv)
    display = _make_display(args)

    if args.stats:
        return _show_history(args, display)

    if not args.file:
        parser.error("one of -f/--file or --stats is required")

    try:
        return _run_quiz(args, display)
    except FlashcardError as exc:
        display.error(str(exc))
        return EXIT_ERROR
    except KeyboardInterrupt:
        display.write()
        display.muted("Interrupted. Goodbye!")
        return EXIT_OK
