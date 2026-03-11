"""Tests for the sdlc validate CLI command."""

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from sdlc_control_plane.cli import main

FIXTURES = Path(__file__).parent / "fixtures"


class TestValidateCLI:
    def setup_method(self) -> None:
        self.runner = CliRunner()

    def test_valid_file_exits_0(self) -> None:
        result = self.runner.invoke(main, ["validate", str(FIXTURES / "valid_task_review.json")])
        assert result.exit_code == 0

    def test_invalid_file_exits_1(self) -> None:
        result = self.runner.invoke(
            main, ["validate", str(FIXTURES / "invalid_missing_fields.json")]
        )
        assert result.exit_code == 1

    def test_nonexistent_file_exits_2(self) -> None:
        result = self.runner.invoke(main, ["validate", "/tmp/nonexistent_cert_12345.json"])
        assert result.exit_code == 2

    def test_type_override(self) -> None:
        result = self.runner.invoke(
            main,
            [
                "validate",
                "--type",
                "task_review",
                str(FIXTURES / "valid_task_review.json"),
            ],
        )
        assert result.exit_code == 0

    def test_multiple_files_mixed(self) -> None:
        result = self.runner.invoke(
            main,
            [
                "validate",
                str(FIXTURES / "valid_task_review.json"),
                str(FIXTURES / "invalid_missing_fields.json"),
            ],
        )
        assert result.exit_code == 1

    def test_file_error_priority_over_validation_error(self) -> None:
        result = self.runner.invoke(
            main,
            [
                "validate",
                str(FIXTURES / "invalid_missing_fields.json"),
                "/tmp/nonexistent_cert_12345.json",
            ],
        )
        assert result.exit_code == 2

    def test_valid_output_contains_filename(self) -> None:
        result = self.runner.invoke(main, ["validate", str(FIXTURES / "valid_task_review.json")])
        assert "valid_task_review.json" in result.output

    def test_invalid_output_contains_error_detail(self) -> None:
        result = self.runner.invoke(
            main, ["validate", str(FIXTURES / "invalid_missing_fields.json")]
        )
        assert result.exit_code == 1
        assert "Field required" in result.output
