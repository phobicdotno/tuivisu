"""Version/about discipline and CLI smoke checks (no PLC needed)."""

import re
import tomllib
from pathlib import Path

import tuivisy
from tuivisy.__main__ import build_parser
from tuivisy.about import RELEASE_NOTES

ROOT = Path(__file__).resolve().parent.parent


def test_version_matches_pyproject() -> None:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert tuivisy.__version__ == pyproject["project"]["version"]


def test_release_notes_top_entry_matches_version() -> None:
    first_line = RELEASE_NOTES.splitlines()[0]
    assert first_line.startswith(f"v{tuivisy.__version__}  ")


def test_release_notes_lines_fit() -> None:
    for line in RELEASE_NOTES.splitlines():
        assert len(line) <= 80, f"release-notes line too long: {line!r}"


def test_version_is_semver() -> None:
    assert re.fullmatch(r"\d+\.\d+\.\d+", tuivisy.__version__)


def test_cli_defaults() -> None:
    args = build_parser().parse_args([])
    assert args.url == "opc.tcp://localhost:4840"
    assert args.user is None and args.password is None
