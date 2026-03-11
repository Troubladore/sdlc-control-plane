"""Tests for the sdlc validate CLI command."""

from __future__ import annotations

import json
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


class TestValidateWithRefChecks:
    def setup_method(self) -> None:
        self.runner = CliRunner()

    def test_broken_claim_ref_exits_1(self, tmp_path: Path) -> None:
        data = json.loads((FIXTURES / "valid_task_review.json").read_text())
        data["formal_conclusion"]["derived_from_claim_ids"] = ["p1", "GHOST"]
        cert_path = tmp_path / "broken.json"
        cert_path.write_text(json.dumps(data))
        result = self.runner.invoke(main, ["validate", str(cert_path)])
        assert result.exit_code == 1
        assert "missing_claim_ref" in result.output

    def test_duplicate_claim_id_exits_1(self, tmp_path: Path) -> None:
        data = json.loads((FIXTURES / "valid_task_review.json").read_text())
        data["quality_assertions"][0]["claim_id"] = "p1"
        cert_path = tmp_path / "dup.json"
        cert_path.write_text(json.dumps(data))
        result = self.runner.invoke(main, ["validate", str(cert_path)])
        assert result.exit_code == 1
        assert "duplicate_claim_id" in result.output

    def test_output_grouped_by_category(self, tmp_path: Path) -> None:
        data = json.loads((FIXTURES / "valid_task_review.json").read_text())
        data["quality_assertions"][0]["claim_id"] = "p1"
        cert_path = tmp_path / "grouped.json"
        cert_path.write_text(json.dumps(data))
        result = self.runner.invoke(main, ["validate", str(cert_path)])
        assert "REFERENCE" in result.output


class TestValidateWithProjectRoot:
    def setup_method(self) -> None:
        self.runner = CliRunner()

    def test_missing_file_exits_1(self, tmp_path: Path) -> None:
        data = json.loads((FIXTURES / "valid_task_review.json").read_text())
        data["premises"][0]["evidence_refs"][0]["artifact_ref"]["locator"] = {
            "path": "src/nonexistent.py"
        }
        cert_path = tmp_path / "cert.json"
        cert_path.write_text(json.dumps(data))
        result = self.runner.invoke(
            main, ["validate", str(cert_path), "--project-root", str(tmp_path)]
        )
        assert result.exit_code == 1
        assert "unresolvable_path" in result.output

    def test_invalid_project_root_exits_2(self) -> None:
        result = self.runner.invoke(
            main,
            [
                "validate",
                str(FIXTURES / "valid_task_review.json"),
                "--project-root",
                "/tmp/nonexistent_dir_12345",
            ],
        )
        assert result.exit_code == 2

    def test_valid_with_project_root_exits_0(self, tmp_path: Path) -> None:
        result = self.runner.invoke(
            main,
            [
                "validate",
                str(FIXTURES / "valid_task_review.json"),
                "--project-root",
                str(tmp_path),
            ],
        )
        assert result.exit_code == 0

    def test_warnings_do_not_cause_exit_1(self, tmp_path: Path) -> None:
        data = json.loads((FIXTURES / "valid_task_review.json").read_text())
        data["premises"][0]["evidence_refs"][0]["artifact_ref"]["locator"] = {}
        cert_path = tmp_path / "warn.json"
        cert_path.write_text(json.dumps(data))
        result = self.runner.invoke(main, ["validate", str(cert_path)])
        assert result.exit_code == 0
