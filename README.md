# Flashcard Quizzer

A command-line flashcard study tool built for the AI-Assisted Development course project. Load a deck of flashcards from JSON, quiz yourself in one of three modes, get immediate colored feedback, and track your accuracy across sessions.

Built on the course starter template, extending it with a new `flashcards/` package while leaving the original `utils/` modules intact.

## Overview

The application reads a JSON deck, asks you to define each term, and compares your answer case-insensitively. Wrong answers reveal the expected definition immediately. At the end of a session you get total questions, accuracy, and a list of every term you missed. Sessions are appended to a history file so `--stats` can report on your study over time.

Three quiz modes are implemented behind a common interface using the **Strategy pattern**, and selected at runtime by a **Factory** (see [Design Patterns](#design-patterns)).

### Verified Results

| Check | Result |
|---|---|
| Test suite | **208 passed, 0 failed** |
| Coverage | **99%** (630 statements, 5 missed) |
| flake8 | **Clean — 0 errors** |

## Features

- **Two JSON deck formats** — a bare array or a `{"cards": [...]}` object wrapper
- **Flexible field names** — `term`/`definition`, with `question`/`answer` and `front`/`back` accepted as aliases, plus an optional `hint`
- **Three quiz modes** — sequential, random, and adaptive
- **Graceful error handling** — missing files, malformed JSON, wrong top-level shape, non-UTF-8 encoding, and invalid cards all produce a readable message and a non-zero exit code; **no traceback ever reaches the terminal**
- **Partial-deck tolerance** — individual bad cards are skipped and reported as warnings so a mostly-good deck stays usable; only a deck with no usable cards is fatal
- **Case-insensitive answers** — comparison ignores capitalisation, surrounding whitespace, and repeated internal whitespace
- **Colored feedback** — green for correct, red for incorrect, automatically disabled when output is piped or redirected, and when `NO_COLOR` is set
- **Graceful exit** — type `exit` or `quit`, press Ctrl+C, or close stdin
- **Session statistics** — total questions, correct/incorrect counts, accuracy percentage, and missed terms with both the expected and the given answer
- **Persistent history** — `--stats` reports aggregate accuracy and your most frequently missed terms across all past sessions
- **Full type hints** on every function and method
- **Zero runtime dependencies** — the application itself uses only the Python standard library

## Requirements

- **Python 3.9 or higher** (developed and tested on 3.10)
- No third-party packages are needed to *run* the quizzer. The packages in `requirements.txt` are development tools (pytest, flake8, black, isort, mypy).

## Setup

1. **Create a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install the development dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

> If the installed tool scripts are not on your `PATH`, invoke them as modules instead: `python -m pytest`, `python -m flake8`, and so on.

## Running the Application

```bash
python main.py -f <deck.json> [-m <mode>]
```

The repository ships several decks under `tests/fixtures/` that you can try immediately.

### Quiz Modes

**Sequential** — asks every card once, in the order it appears in the file. This is the default, so `-m` can be omitted.

```bash
python main.py -f tests/fixtures/valid_array.json
python main.py -f tests/fixtures/valid_array.json -m sequential
```

**Random** — asks every card exactly once, in a shuffled order.

```bash
python main.py -f tests/fixtures/valid_array.json -m random
```

**Adaptive** — spends more time on the cards you keep missing. Each remaining card is weighted `1 + misses`, so a card missed twice comes up three times as often as a fresh one. A card is retired once you answer it correctly, or after **3 attempts** — that cap is what guarantees the session ends. The same card is never asked twice in a row while another card is still in play.

```bash
python main.py -f tests/fixtures/valid_array.json -m adaptive
```

### Session Statistics

```bash
python main.py --stats
```

Reports how many sessions you have recorded, total questions answered, overall accuracy, and the terms missed in the most sessions. Requires no deck file.

### Example Session

```
====================================================
Flashcard Quizzer
====================================================
Deck: valid_array  (3 cards)
Mode: sequential — Cards in file order, each asked once.
Type your answer and press Enter.
Type 'exit' or press Ctrl+C to stop early.

Q1. What is: Big-O notation
   Your answer: upper bound on growth rate
✓ Correct!

Q2. What is: Binary search
   Your answer: something wrong
✗ Not quite — the answer is: O(log n) search on sorted data

Q3. What is: Hash table
   Your answer: key-value store with O(1) average lookup
✓ Correct!

====================================================
Session Statistics
====================================================
Total questions: 3
Correct:         2
Incorrect:       1
Accuracy:        66.7%

Missed term (1):
   • Binary search
       expected: O(log n) search on sorted data
       you said: something wrong
```

## Command-Line Options

| Option | Description |
|---|---|
| `-f PATH`, `--file PATH` | Path to the JSON flashcard file. Required unless `--stats` is used. |
| `-m MODE`, `--mode MODE` | Quiz mode: `sequential`, `random`, or `adaptive`. Defaults to `sequential`. Matched case-insensitively. |
| `--stats` | Show statistics from previous sessions and exit. Needs no deck file. |
| `--seed N` | Seed the random source, making `random` and `adaptive` card order reproducible. |
| `--no-color` | Disable colored output. |
| `--data-dir PATH` | Directory holding the session history file. Defaults to `data`. |
| `--version` | Print the version and exit. |
| `-h`, `--help` | Show the help message and exit. |

### The Three Core Flags

**`-f` / `--file`** — points at the JSON deck to study. If the file is missing, unreadable, not valid UTF-8, not valid JSON, or contains no usable cards, the application prints an explanatory message and exits with code `1`.

**`-m` / `--mode`** — chooses the quiz strategy. The valid names come from the factory registry, so `argparse` and the registry cannot drift apart; an unrecognised name is rejected by `argparse` with exit code `2`.

**`--stats`** — switches the application into a reporting mode. Instead of running a quiz it reads `data/history.json`, aggregates every recorded session, and prints overall accuracy plus your most frequently missed terms. A session is only recorded if at least one question was answered, so quitting immediately leaves no trace.

### Exit Codes

| Code | Meaning |
|---|---|
| `0` | The quiz ran, or history was shown, successfully |
| `1` | A runtime problem, such as an unreadable or invalid deck |
| `2` | A usage problem, raised by `argparse` |

## Exiting Gracefully

Any of the following ends the session cleanly, prints the statistics for whatever you answered so far, and exits with code `0`:

- Type **`exit`** or **`quit`** at an answer prompt (case-insensitive, surrounding whitespace ignored)
- Press **Ctrl+C**
- Close stdin / reach end of input (useful when piping answers in)

Pressing Enter on an empty prompt is treated as an attempted answer, not as a request to quit.

## Supported JSON Formats

### Array Format

```json
[
  {"term": "Big-O notation", "definition": "Upper bound on growth rate"},
  {"term": "Binary search", "definition": "O(log n) search on sorted data"}
]
```

### Object Format

```json
{
  "title": "Data Structures",
  "cards": [
    {"term": "Stack", "definition": "LIFO collection", "hint": "Last in, first out"},
    {"question": "Queue", "answer": "FIFO collection"}
  ]
}
```

### Field Names

| Purpose | Canonical | Accepted aliases |
|---|---|---|
| The prompt | `term` | `question`, `front` |
| The answer | `definition` | `answer`, `back` |
| Optional hint | `hint` | — |

Both the term and the definition are required, must be text, and must not be blank. A `hint` that is missing, blank, or not text is simply ignored rather than treated as an error.

### Validation Behaviour

Validation collects **every** problem in a deck rather than stopping at the first, so a broken file can be fixed in a single pass. Messages are positional, for example:

```
Card 3: expected an object, got str.
Card 4: missing required field 'definition' or 'answer' or 'back'.
Card 6: field 'term' must be text, got int.
```

Duplicate terms are reported but not fatal — the first card wins and later copies are skipped.

## Testing

### Run the test suite

```bash
pytest
```

### Run with coverage

```bash
pytest --cov=. --cov-report=term-missing
```

For a browsable HTML report:

```bash
pytest --cov=. --cov-report=html
```

The suite contains **208 tests** and reports **99% coverage**. The uncovered lines are the permission-denied and generic `OSError` branches in `flashcards/loader.py` (awkward to trigger portably) and the `__main__` guard in `main.py`.

### Run linting

```bash
flake8 .
```

Reports **no errors**. Configuration lives in `setup.cfg`, which pins the line length to 88 to match `.editorconfig` and ignores `E203`/`W503` for black compatibility.

### Run all quality checks

```bash
black . && isort . && flake8 . && pytest
```

### Test Organisation

| File | Covers |
|---|---|
| `test_models.py` | Answer normalisation and the `Flashcard` dataclass |
| `test_validator.py` | Per-card and whole-deck validation rules |
| `test_loader.py` | Both JSON formats and every load failure mode |
| `test_modes.py` | All three strategies, including termination guarantees |
| `test_factory.py` | Mode registration, lookup, and unknown-name errors |
| `test_stats.py` | Scoring, accuracy, missed terms, and history persistence |
| `test_display.py` | Message rendering and color auto-detection |
| `test_session.py` | The quiz loop, exit paths, and mode integration |
| `test_cli.py` | Argument parsing, exit codes, and end-to-end runs |
| `test_task_manager.py`, `test_file_handler.py` | The original starter modules |

Decks used by the tests live in `tests/fixtures/`, covering valid, malformed, empty, wrongly-shaped, non-UTF-8 and partially-invalid input.

## Design Patterns

### Strategy Pattern

The three quiz modes are interchangeable strategies behind the abstract base class `QuizMode` (`flashcards/modes/base.py`). A mode owns exactly one decision — *which card comes next* — and knows nothing about terminals, scoring, or input.

```python
class QuizMode(ABC):
    @abstractmethod
    def next_card(self) -> Optional[Flashcard]:
        """Return the next card, or None when the session is done."""

    def record_result(self, card: Flashcard, correct: bool) -> None:
        """Observe the outcome. Default implementation ignores it."""
```

`SequentialMode`, `RandomMode`, and `AdaptiveMode` each implement `next_card`. The second method, `record_result`, is a feedback hook with a concrete no-op default: order-only strategies have nothing to learn from an answer, while `AdaptiveMode` overrides it to re-queue cards you got wrong.

That uniform interface is what makes this a genuine Strategy rather than a disguised conditional — `QuizSession` runs an identical loop for all three modes, with no knowledge of which one it holds. Adding a fourth mode requires no change to the session loop at all.

### Factory Pattern

`QuizModeFactory` (`flashcards/modes/factory.py`) maps the user's `-m` string onto a strategy class through a single registry dictionary:

```python
_registry: Dict[str, Type[QuizMode]] = {
    "sequential": SequentialMode,
    "random": RandomMode,
    "adaptive": AdaptiveMode,
}
```

This keeps object construction out of the CLI, which simply asks for a mode by name. The factory is also the single source of truth for which names are valid: `argparse` populates its `choices` from `QuizModeFactory.available_modes()`, so the accepted flags and the registry cannot fall out of step. An unknown name raises a `ValueError` that lists the valid options.

## Project Structure

```
starter/
├── main.py                      # Entry point — forwards to flashcards.cli
├── flashcards/                  # The application
│   ├── __init__.py
│   ├── cli.py                   # argparse, error handling, exit codes
│   ├── display.py               # All terminal output and color handling
│   ├── exceptions.py            # FlashcardError hierarchy
│   ├── loader.py                # JSON loading, both deck formats
│   ├── models.py                # Flashcard dataclass, answer normalisation
│   ├── session.py               # The quiz loop
│   ├── stats.py                 # Scoring and persisted history
│   ├── validator.py             # Deck validation rules
│   └── modes/                   # Quiz strategies
│       ├── __init__.py
│       ├── base.py              # QuizMode ABC        (Strategy)
│       ├── sequential.py        # SequentialMode
│       ├── random_mode.py       # RandomMode
│       ├── adaptive.py          # AdaptiveMode
│       └── factory.py           # QuizModeFactory     (Factory)
├── utils/                       # Original starter modules, unchanged
│   ├── __init__.py
│   ├── file_handler.py          # JSON persistence, reused by stats.py
│   └── task_manager.py
├── tests/                       # 208 tests
│   ├── __init__.py
│   ├── conftest.py              # Shared fixtures
│   ├── fixtures/                # Test decks, valid and invalid
│   └── test_*.py
├── docs/                        # AI edit log, patterns guide, report template
├── ai_guidance/                 # Prompting and code review guidance
├── .claude/                     # AI assistant configuration
├── requirements.txt             # Development dependencies
├── setup.cfg                    # flake8, isort, mypy, pytest, coverage config
├── .editorconfig
└── README.md
```

### Architecture

Modules depend in one direction only:

```
exceptions / models  →  validator  →  loader  →  modes  →  session  →  cli
                                   display, stats (leaves)
```

The session loop takes its input and output as injected callables rather than calling `input` and `print` directly, which is what makes the interactive path fully testable with scripted answers and captured output.

Session history reuses the starter project's `utils.file_handler.FileHandler` rather than reimplementing JSON persistence, connecting the new feature to the existing utility layer.

## Course Project Information

This project was built for the AI-Assisted Development course. Supporting documentation:

- `docs/ai_edit_log.md` — detailed log of AI interactions, including defects found in AI-generated code and how they were resolved
- `docs/design_patterns.md` — the patterns guide the Strategy and Factory implementations follow
- `docs/report_template.md` — template for the final project report
- `docs/project_rubric.md` — assessment criteria
- `ai_guidance/prompting_best_practices.md` — effective prompting techniques
- `ai_guidance/code_review_checklist.md` — systematic review of AI-generated code

### Learning Objectives

- **AI Collaboration** — generating, reviewing, and refactoring code with AI while keeping ownership of quality
- **Software Engineering** — design patterns, separation of concerns, modular architecture
- **Testing** — comprehensive unit tests with high coverage, including edge cases and error conditions
- **Code Quality** — linting, formatting, and type checking
- **Documentation** — recording AI interactions and the decisions behind them

## Built With

* [Python](https://www.python.org/) — core language, standard library only at runtime
* [pytest](https://docs.pytest.org/) — testing framework
* [pytest-cov](https://pytest-cov.readthedocs.io/) — coverage reporting
* [Black](https://black.readthedocs.io/) — code formatter
* [isort](https://pycqa.github.io/isort/) — import organizer
* [flake8](https://flake8.pycqa.org/) — linting
* [mypy](https://mypy.readthedocs.io/) — static type checking
* [Claude](https://claude.ai/) — AI assistant for code generation and review

## License

[License](LICENSE.txt)
