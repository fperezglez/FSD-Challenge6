#!/usr/bin/env python3
"""Decode the simple teaching container recovered from the JPEG."""
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("Usage: python tools/decode_container.py extracted_payload.bin")
p = Path(sys.argv[1])
data = p.read_bytes()
if len(data) < 7 or data[:4] != b"GG6C":
    raise SystemExit("Container marker missing: wrong file or incomplete extraction")
version = data[4]
if version != 1:
    raise SystemExit(f"Unsupported container version: {version}")
length = int.from_bytes(data[5:7], "little")
if len(data) < 7 + length:
    raise SystemExit("Container declares a message longer than the extracted file")
message = data[7:7+length]
print(f"Container: GG6C v{version}; readable note: {length} bytes\n")
print(message.decode("utf-8", errors="replace"))
