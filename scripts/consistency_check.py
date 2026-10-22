#!/usr/bin/env python3
"""Initial consistency guard for generated numeric macros in the manuscript."""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "paper"
MACROS = PAPER / "numbers.tex"


def main() -> int:
    if not MACROS.exists():
        print(f"FAIL: generated macro file missing: {MACROS}")
        return 1
    source = "\n".join(p.read_text(encoding="utf-8", errors="replace") for p in PAPER.rglob("*.tex") if p != MACROS)
    unresolved = re.findall(r"Table\s+\?\?|\\ref\{[^}]*\?\?", source)
    if unresolved:
        print(f"FAIL: unresolved references: {unresolved}")
        return 1
    print("PASS: numbers.tex exists; no obvious unresolved table/reference markers")
    print("NOTE: manuscript-wide numeric macro enforcement is pending Gate 0.2")
    return 0


if __name__ == "__main__":
    sys.exit(main())
