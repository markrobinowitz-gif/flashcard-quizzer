"""
Unit tests for argument parsing, exit codes and top-level error handling.

The promise these tests protect is that no input, however malformed, ever
reaches the user as a traceback.
"""

import itertools

import pytest

from flashcards.cli import EXIT_ERROR, EXIT_OK, build_parser, main
from flashcards.modes.factory import DEFAULT_MODE
from flashcards.session import QuizSession


@pytest.fixture
def scripted(monkeypatch):
    """Return a callable that scripts the answers a CLI run will receive.

    ``QuizSession`` captures the built-in ``input`` as a default argument
    when the class is defined, so patching ``builtins.input`` has no
    effect. Replacing the name the CLI looks up lets the test supply an
    ``input_fn`` the same way production code could.
    """

    def _install(*answers: str, repeat: bool = False) -> None:
        supply = (
            itertools.cycle(answers) if repeat else iter(answers)
        )

        def factory(**kwargs):
            kwargs["input_fn"] = lambda _prompt="": next(supply)
            return QuizSession(**kwargs)

        monkeypatch.setattr("flashcards.cli.QuizSession", factory)

    return _install


class TestArgumentParsing:
    """Test suite for the argparse configuration."""

    def test_file_flag_short_and_long(self) -> None:
        """Test that -f and --file are equivalent."""
        parser = build_parser()
        assert parser.parse_args(["-f", "d.json"]).file == "d.json"
        assert parser.parse_args(["--file", "d.json"]).file == "d.json"

    def test_mode_flag_short_and_long(self) -> None:
        """Test that -m and --mode are equivalent."""
        parser = build_parser()
        assert parser.parse_args(["-m", "random"]).mode == "random"
        assert parser.parse_args(["--mode", "random"]).mode == "random"

    def test_mode_defaults_to_sequential(self) -> None:
        """Test the documented default mode."""
        assert build_parser().parse_args([]).mode == DEFAULT_MODE

    def test_stats_flag_is_boolean(self) -> None:
        """Test that --stats is a switch."""
        parser = build_parser()
        assert parser.parse_args(["--stats"]).stats is True
        assert parser.parse_args([]).stats is False

    def test_invalid_mode_is_rejected(self) -> None:
        """Test that argparse refuses an unregistered mode."""
        with pytest.raises(SystemExit) as exc_info:
            build_parser().parse_args(["-m", "turbo"])
        assert exc_info.value.code == 2

    @pytest.mark.parametrize("mode", ["sequential", "random", "adaptive"])
    def test_all_three_modes_are_accepted(self, mode) -> None:
        """Test that every required mode is a valid choice."""
        assert build_parser().parse_args(["-m", mode]).mode == mode


class TestMainExitCodes:
    """Test suite for the exit codes main() returns."""

    def test_missing_arguments_exit_two(self) -> None:
        """Test that no arguments is a usage error."""
        with pytest.raises(SystemExit) as exc_info:
            main([])
        assert exc_info.value.code == 2

    def test_successful_quiz_exits_zero(
        self, fixture_path, tmp_path, monkeypatch, scripted
    ) -> None:
        """Test a complete run from the command line."""
        scripted("a", "b", "c")
        code = main(
            [
                "-f",
                str(fixture_path("valid_array.json")),
                "--no-color",
                "--data-dir",
                str(tmp_path),
            ]
        )
        assert code == EXIT_OK

    def test_missing_file_exits_one_without_traceback(
        self, capsys, tmp_path
    ) -> None:
        """Test that a missing deck is reported, not raised."""
        code = main(
            ["-f", str(tmp_path / "nope.json"), "--no-color"]
        )
        assert code == EXIT_ERROR
        out = capsys.readouterr().out
        assert "not found" in out
        assert "Traceback" not in out

    def test_malformed_json_exits_one(
        self, fixture_path, capsys
    ) -> None:
        """Test that a syntax error is reported readably."""
        code = main(
            ["-f", str(fixture_path("malformed.json")), "--no-color"]
        )
        assert code == EXIT_ERROR
        assert "Malformed JSON" in capsys.readouterr().out

    def test_empty_deck_exits_one(self, fixture_path, capsys) -> None:
        """Test that an empty deck is reported readably."""
        code = main(
            ["-f", str(fixture_path("empty_array.json")), "--no-color"]
        )
        assert code == EXIT_ERROR
        assert "no flashcards" in capsys.readouterr().out

    def test_keyboard_interrupt_exits_zero(
        self, fixture_path, monkeypatch, capsys
    ) -> None:
        """Test that Ctrl+C at the top level is a clean exit."""

        def interrupt(*_args, **_kwargs):
            raise KeyboardInterrupt

        monkeypatch.setattr(
            "flashcards.cli.QuizSession", interrupt
        )
        code = main(
            ["-f", str(fixture_path("valid_array.json")), "--no-color"]
        )
        assert code == EXIT_OK
        assert "Interrupted" in capsys.readouterr().out


class TestQuizBehaviourThroughCli:
    """Test suite for end-to-end behaviour driven by main()."""

    def test_deck_warnings_are_shown(
        self, fixture_path, tmp_path, monkeypatch, capsys, scripted
    ) -> None:
        """Test that skipped cards are reported before the quiz."""
        scripted("exit", repeat=True)
        main(
            [
                "-f",
                str(fixture_path("missing_fields.json")),
                "--no-color",
                "--data-dir",
                str(tmp_path),
            ]
        )
        assert "skipped while loading" in capsys.readouterr().out

    def test_object_format_deck_runs(
        self, fixture_path, tmp_path, monkeypatch, capsys, scripted
    ) -> None:
        """Test that the {"cards": [...]} format works end to end."""
        scripted("LIFO collection", "FIFO collection")
        main(
            [
                "-f",
                str(fixture_path("valid_object.json")),
                "--no-color",
                "--data-dir",
                str(tmp_path),
            ]
        )
        assert "Accuracy:        100.0%" in capsys.readouterr().out

    def test_seed_makes_random_mode_reproducible(
        self, fixture_path, tmp_path, monkeypatch, capsys, scripted
    ) -> None:
        """Test that --seed pins the card order."""
        outputs = []
        for _ in range(2):
            scripted("exit", repeat=True)
            main(
                [
                    "-f",
                    str(fixture_path("valid_array.json")),
                    "-m",
                    "random",
                    "--seed",
                    "7",
                    "--no-color",
                    "--data-dir",
                    str(tmp_path),
                ]
            )
            outputs.append(capsys.readouterr().out)
        assert outputs[0] == outputs[1]

    def test_adaptive_mode_runs_end_to_end(
        self, fixture_path, tmp_path, monkeypatch, capsys, scripted
    ) -> None:
        """Test that adaptive mode completes without hanging."""
        scripted("wrong", repeat=True)
        code = main(
            [
                "-f",
                str(fixture_path("valid_array.json")),
                "-m",
                "adaptive",
                "--seed",
                "1",
                "--no-color",
                "--data-dir",
                str(tmp_path),
            ]
        )
        assert code == EXIT_OK
        assert "Accuracy:        0.0%" in capsys.readouterr().out


class TestStatsFlag:
    """Test suite for the --stats history report."""

    def test_stats_on_empty_history(self, tmp_path, capsys) -> None:
        """Test the first-run message."""
        code = main(["--stats", "--data-dir", str(tmp_path), "--no-color"])
        assert code == EXIT_OK
        assert "No sessions recorded yet." in capsys.readouterr().out

    def test_stats_needs_no_deck_file(self, tmp_path) -> None:
        """Test that --stats alone is valid usage."""
        assert main(["--stats", "--data-dir", str(tmp_path)]) == EXIT_OK

    def test_session_is_recorded_and_reported(
        self, fixture_path, tmp_path, monkeypatch, capsys, scripted
    ) -> None:
        """Test that a finished quiz shows up in a later --stats run."""
        scripted("upper bound on growth rate", "x", "y")
        main(
            [
                "-f",
                str(fixture_path("valid_array.json")),
                "--no-color",
                "--data-dir",
                str(tmp_path),
            ]
        )
        capsys.readouterr()

        main(["--stats", "--data-dir", str(tmp_path), "--no-color"])
        out = capsys.readouterr().out
        assert "Sessions recorded: 1" in out
        assert "Questions answered: 3" in out
        assert "Binary search" in out

    def test_aborted_session_is_not_recorded(
        self, fixture_path, tmp_path, monkeypatch, capsys, scripted
    ) -> None:
        """Test that quitting before answering records nothing."""
        scripted("exit", repeat=True)
        main(
            [
                "-f",
                str(fixture_path("valid_array.json")),
                "--no-color",
                "--data-dir",
                str(tmp_path),
            ]
        )
        capsys.readouterr()
        main(["--stats", "--data-dir", str(tmp_path), "--no-color"])
        assert "No sessions recorded yet." in capsys.readouterr().out

    def test_history_write_failure_is_warned_not_fatal(
        self, fixture_path, tmp_path, monkeypatch, capsys, scripted
    ) -> None:
        """Test that an unwritable history file does not fail the quiz."""
        scripted("a", "b", "c")

        def boom(self, stats) -> None:
            raise RuntimeError("disk full")

        monkeypatch.setattr("flashcards.stats.HistoryStore.append", boom)
        code = main(
            [
                "-f",
                str(fixture_path("valid_array.json")),
                "--no-color",
                "--data-dir",
                str(tmp_path),
            ]
        )
        assert code == EXIT_OK
        assert "Could not save session history" in capsys.readouterr().out
