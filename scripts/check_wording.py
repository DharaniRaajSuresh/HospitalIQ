#!/usr/bin/env python3
import re
from pathlib import Path

def main():
    paper_path = Path("paper/main.tex")
    text = paper_path.read_text(encoding="utf-8")
    words = [
        "revolutionary", "profound", "groundbreaking", "complete decoupling",
        "flawless", "eliminate author", "eliminating author", "zero perceptible",
        "pre-registered", "pre-registration", "guarantee"
    ]
    found = False
    for w in words:
        matches = list(re.finditer(re.escape(w), text, re.IGNORECASE))
        if matches:
            found = True
            print(f"Found {len(matches)} occurrence(s) of '{w}':")
            for m in matches:
                start = max(0, m.start() - 40)
                end = min(len(text), m.end() + 40)
                snippet = text[start:end].replace("\n", " ")
                print(f"   [{m.start()}]: ...{snippet}...")
    if not found:
        print("PASS: No flagged hyperbolic words found.")

if __name__ == "__main__":
    main()
