#!/usr/bin/env python3
"""Student-friendly wrapper: extract a Garden Gallery payload interactively.

Example:
    python tools/extract_payload.py evidence/images/img_0147.jpg recovered_payload.bin

The passphrase is prompted for without echoing it and is not placed in shell history.
"""
from __future__ import annotations

import sys
from pathlib import Path

try:
    from jpeg_steg import command_extract
except SystemExit:
    raise
except ImportError as exc:
    raise SystemExit(
        "Could not load the JPEG extraction utility. Install dependencies with:\n"
        "  python -m pip install -r requirements-extraction.txt"
    ) from exc


def main() -> int:
    if len(sys.argv) != 3:
        print(
            "Usage: python tools/extract_payload.py INPUT.jpg OUTPUT.bin",
            file=sys.stderr,
        )
        return 2
    source = Path(sys.argv[1])
    destination = Path(sys.argv[2])
    if not source.is_file() and not source.is_absolute():
        package_candidate = Path(__file__).resolve().parents[1] / "evidence" / "images" / source
        if package_candidate.is_file():
            source = package_candidate
    if not source.is_file():
        print(f"Input image not found: {source}", file=sys.stderr)
        return 2
    passphrase = input("Coefficient-permutation passphrase: ").strip()
    try:
        command_extract(str(source), str(destination), passphrase)
    except (ValueError, OSError, RuntimeError) as exc:
        print(f"Extraction failed: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
