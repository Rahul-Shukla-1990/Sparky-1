#!/usr/bin/env python3
"""Create a distributable archive of the DarkWatch demo."""
from __future__ import annotations

import argparse
import os
import pathlib
import sys
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_ARCHIVE = ROOT / "darkwatch-v7.zip"


def iter_files(base: pathlib.Path) -> list[pathlib.Path]:
    """Yield repo files that should be added to the archive."""
    skip_dirs = {".git", "__pycache__", ".pytest_cache", ".ruff_cache"}
    for path in base.rglob("*"):
        relative = path.relative_to(base)
        if any(part in skip_dirs for part in relative.parts):
            continue
        if path.is_dir():
            continue
        if relative.name.endswith((".pyc", ".pyo")):
            continue
        if relative.name == DEFAULT_ARCHIVE.name:
            continue
        yield relative


def create_archive(target: pathlib.Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for relative in iter_files(ROOT):
            zf.write(ROOT / relative, arcname=relative)
    print(f"Archive written to {target}")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "output",
        nargs="?",
        default=str(DEFAULT_ARCHIVE),
        help="Destination zip file (defaults to darkwatch-v7.zip in the repo root)",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    create_archive(pathlib.Path(args.output).resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
