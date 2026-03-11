"""Tests for filesystem-backed locator validation."""

from __future__ import annotations

import json
from pathlib import Path

from sdlc_control_plane.verification.locator_fs import validate_filesystem
from sdlc_control_plane.verification.models import validate_certificate

FIXTURES = Path(__file__).parent / "fixtures"


def _cert_with_locator(locator: dict) -> object:
    data = json.loads((FIXTURES / "valid_task_review.json").read_text())
    data["premises"][0]["evidence_refs"][0]["artifact_ref"]["locator"] = locator
    return validate_certificate(data)


class TestUnresolvablePath:
    def test_missing_file_detected(self, tmp_path: Path) -> None:
        cert = _cert_with_locator({"path": "src/nonexistent.py"})
        diagnostics = validate_filesystem(cert, tmp_path)
        errors = [d for d in diagnostics if d.code == "unresolvable_path"]
        assert len(errors) == 1

    def test_existing_file_no_error(self, tmp_path: Path) -> None:
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "foo.py").write_text("hello\n")
        cert = _cert_with_locator({"path": "src/foo.py"})
        diagnostics = validate_filesystem(cert, tmp_path)
        errors = [d for d in diagnostics if d.code == "unresolvable_path"]
        assert errors == []


class TestLineRangeExceedsFile:
    def test_end_line_exceeds_file(self, tmp_path: Path) -> None:
        (tmp_path / "small.py").write_text("line1\nline2\nline3\n")
        cert = _cert_with_locator({"path": "small.py", "start_line": 1, "end_line": 100})
        diagnostics = validate_filesystem(cert, tmp_path)
        warnings = [d for d in diagnostics if d.code == "line_range_exceeds_file"]
        assert len(warnings) == 1
        assert warnings[0].severity == "warning"

    def test_valid_line_range_no_warning(self, tmp_path: Path) -> None:
        (tmp_path / "ok.py").write_text("line1\nline2\nline3\n")
        cert = _cert_with_locator({"path": "ok.py", "start_line": 1, "end_line": 3})
        diagnostics = validate_filesystem(cert, tmp_path)
        warnings = [d for d in diagnostics if d.code == "line_range_exceeds_file"]
        assert warnings == []


class TestPathNotRegularFile:
    def test_directory_with_lines_is_error(self, tmp_path: Path) -> None:
        (tmp_path / "src").mkdir()
        cert = _cert_with_locator({"path": "src", "start_line": 1, "end_line": 10})
        diagnostics = validate_filesystem(cert, tmp_path)
        errors = [d for d in diagnostics if d.code == "path_not_regular_file"]
        assert len(errors) == 1
        assert errors[0].severity == "error"

    def test_directory_without_lines_no_error(self, tmp_path: Path) -> None:
        (tmp_path / "src").mkdir()
        cert = _cert_with_locator({"path": "src"})
        diagnostics = validate_filesystem(cert, tmp_path)
        errors = [d for d in diagnostics if d.code == "path_not_regular_file"]
        assert errors == []


class TestNoLocatorPaths:
    def test_cert_without_locators_produces_no_fs_diagnostics(self, tmp_path: Path) -> None:
        cert = validate_certificate(
            json.loads((FIXTURES / "valid_task_review.json").read_text())
        )
        diagnostics = validate_filesystem(cert, tmp_path)
        assert diagnostics == []
