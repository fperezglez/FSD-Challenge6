#!/usr/bin/env python3
"""Cross-platform Python tools for the Garden Gallery JPEG-steganography lab.

This is a deliberately simplified F5-inspired teaching format, not a secure
or byte-compatible implementation of F5. It edits quantized luminance AC DCT
coefficients through pyjpegio (import name: jpegio).

Commands:
  python tools/jpeg_steg.py hist INPUT.jpg OUTPUT.csv
  python tools/jpeg_steg.py embed INPUT.jpg OUTPUT.jpg PAYLOAD.bin --passphrase TEXT
  python tools/jpeg_steg.py extract INPUT.jpg OUTPUT.bin --passphrase TEXT
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from typing import Iterable

try:
    import jpegio as jio
    import numpy as np
except ImportError as exc:  # keep error beginner-friendly
    raise SystemExit(
        "Missing JPEG coefficient dependencies. Install them with:\n"
        "  python -m pip install -r requirements-extraction.txt\n"
        "(The package is called pyjpegio on PyPI and jpegio in Python.)"
    ) from exc

MASK64 = (1 << 64) - 1
FNV_OFFSET = 1469598103934665603  # Match the classroom C implementation exactly.
FNV_PRIME = 1099511628211
XORSHIFT_MULT = 2685821657736338717


def _load_y_blocks(path: str | Path):
    """Read JPEG and return (JPEG object, Y coefficient array, block-major copy).

    pyjpegio stores each component's coefficient blocks as a tiled 2-D array;
    `blocks` is rearranged to the same block-row/block-column/natural-order
    layout used by libjpeg's JBLOCK array in the original classroom tool.
    """
    jpeg = jio.read(str(path))
    if not getattr(jpeg, "coef_arrays", None):
        raise ValueError(f"No coefficient arrays found in {path}")
    tiled = np.asarray(jpeg.coef_arrays[0])
    if tiled.ndim != 2 or tiled.shape[0] % 8 or tiled.shape[1] % 8:
        raise ValueError(f"Unexpected luminance coefficient-array shape: {tiled.shape}")
    bh = tiled.shape[0] // 8
    bw = tiled.shape[1] // 8
    blocks = tiled.reshape(bh, 8, bw, 8).transpose(0, 2, 1, 3).reshape(bh * bw, 64).copy()
    return jpeg, tiled, blocks, bh, bw


def _store_y_blocks(jpeg, tiled: np.ndarray, blocks: np.ndarray, bh: int, bw: int) -> None:
    restored = blocks.reshape(bh, bw, 8, 8).transpose(0, 2, 1, 3).reshape(tiled.shape)
    # Mutate the existing array rather than replacing the list item; this is
    # compatible with pyjpegio's JPEGStruct API across the supported versions.
    tiled[:, :] = restored.astype(tiled.dtype, copy=False)


def _flatten_ac(blocks: np.ndarray) -> np.ndarray:
    """Return all luminance AC coefficients in C-tool order (block-major, k=1..63)."""
    return blocks[:, 1:].reshape(-1)


def _write_histogram(path: str | Path, ac_values: Iterable[int]) -> None:
    values = np.asarray(ac_values, dtype=np.int64)
    if values.size == 0:
        raise ValueError("No luminance AC coefficients were found")
    h = {v: int(np.count_nonzero(values == v)) for v in range(-20, 21)}
    outside = int(values.size - sum(h.values()))
    with Path(path).open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["value", "count", "total_ac_y"])
        for v in range(-20, 21):
            writer.writerow([v, h[v], int(values.size)])
        writer.writerow(["OUTSIDE_RANGE", outside, int(values.size)])
        writer.writerow(["TOTAL", int(values.size), int(values.size)])


def command_hist(input_path: str, output_path: str) -> None:
    _jpeg, _tiled, blocks, _bh, _bw = _load_y_blocks(input_path)
    _write_histogram(output_path, _flatten_ac(blocks))
    print(f"Wrote quantized luminance AC histogram: {output_path}")


def _seed_from_passphrase(text: str) -> int:
    state = FNV_OFFSET
    for byte in text.encode("utf-8"):
        state ^= byte
        state = (state * FNV_PRIME) & MASK64
    return state or 0x9E3779B97F4A7C15


def _next_u64(state: int) -> tuple[int, int]:
    x = state & MASK64
    x ^= x >> 12
    x ^= (x << 25) & MASK64
    x ^= x >> 27
    x &= MASK64
    return x, (x * XORSHIFT_MULT) & MASK64


def _shuffled_locations(count: int, passphrase: str) -> list[int]:
    """Fisher-Yates permutation matching the classroom C program."""
    locations = list(range(count))
    state = _seed_from_passphrase(passphrase)
    for i in range(count - 1, 0, -1):
        state, value = _next_u64(state)
        j = value % (i + 1)
        locations[i], locations[j] = locations[j], locations[i]
    return locations


def _get_bit(data: bytes | bytearray, bit: int, nbits: int) -> int:
    if bit >= nbits:
        return 0
    return (data[bit // 8] >> (7 - bit % 8)) & 1


def _put_bit(data: bytearray, bit: int, value: int) -> None:
    if value:
        data[bit // 8] |= 1 << (7 - bit % 8)


def _pack_message(payload: bytes) -> bytes:
    if len(payload) > 0xFFFFFFFF:
        raise ValueError("Payload is too large for the classroom format")
    return len(payload).to_bytes(4, "big") + payload


def _read_length_from_bits(bits: bytearray) -> int:
    return int.from_bytes(bits[:4], "big")


def command_embed(input_path: str, output_path: str, payload_path: str, passphrase: str) -> None:
    jpeg, tiled, blocks, bh, bw = _load_y_blocks(input_path)
    ac_count = blocks.shape[0] * 63
    locations = _shuffled_locations(ac_count, passphrase)
    payload = Path(payload_path).read_bytes()
    msg = _pack_message(payload)
    bit_count = len(msg) * 8
    padded_bits = ((bit_count + 2) // 3) * 3
    cursor = 0
    bit = 0

    def get_coeff(loc: int) -> int:
        # loc is an AC-only linear index: 63 entries per block, k = 1..63.
        block, ac_slot = divmod(loc, 63)
        return int(blocks[block, ac_slot + 1])

    def set_coeff(loc: int, value: int) -> None:
        block, ac_slot = divmod(loc, 63)
        blocks[block, ac_slot + 1] = value

    def take_next_nonzero() -> int:
        nonlocal cursor
        while cursor < len(locations) and get_coeff(locations[cursor]) == 0:
            cursor += 1
        if cursor >= len(locations):
            raise ValueError("Insufficient nonzero AC coefficients for this payload")
        location = locations[cursor]
        cursor += 1
        return location

    while bit < padded_bits:
        group = [take_next_nonzero() for _ in range(7)]
        message_value = (
            (_get_bit(msg, bit, bit_count) << 2)
            | (_get_bit(msg, bit + 1, bit_count) << 1)
            | _get_bit(msg, bit + 2, bit_count)
        )
        while True:
            syndrome = 0
            for i, loc in enumerate(group):
                if abs(get_coeff(loc)) & 1:
                    syndrome ^= (i + 1)
            flip = syndrome ^ message_value
            if flip == 0:
                break
            chosen_slot = flip - 1
            chosen_location = group[chosen_slot]
            value = get_coeff(chosen_location)
            new_value = value - 1 if value > 0 else value + 1
            set_coeff(chosen_location, new_value)
            if new_value == 0:
                # Shrinkage: replace the vanished coefficient and recompute.
                group.pop(chosen_slot)
                group.append(take_next_nonzero())
        bit += 3

    _store_y_blocks(jpeg, tiled, blocks, bh, bw)
    jio.write(jpeg, str(output_path))
    print(f"Embedded {len(payload)}-byte teaching payload in {output_path}")


def command_extract(input_path: str, output_path: str, passphrase: str) -> None:
    _jpeg, _tiled, blocks, _bh, _bw = _load_y_blocks(input_path)
    locations = _shuffled_locations(blocks.shape[0] * 63, passphrase)
    capacity_bits = (len(locations) // 7) * 3
    output_bits = bytearray((capacity_bits + 7) // 8)
    cursor = 0
    bit = 0

    def get_coeff(loc: int) -> int:
        block, ac_slot = divmod(loc, 63)
        return int(blocks[block, ac_slot + 1])

    while bit + 3 <= capacity_bits:
        group: list[int] = []
        while len(group) < 7:
            while cursor < len(locations) and get_coeff(locations[cursor]) == 0:
                cursor += 1
            if cursor >= len(locations):
                break
            group.append(locations[cursor])
            cursor += 1
        if len(group) < 7:
            break
        syndrome = 0
        for i, loc in enumerate(group):
            if abs(get_coeff(loc)) & 1:
                syndrome ^= (i + 1)
        _put_bit(output_bits, bit, (syndrome >> 2) & 1)
        _put_bit(output_bits, bit + 1, (syndrome >> 1) & 1)
        _put_bit(output_bits, bit + 2, syndrome & 1)
        bit += 3
        if bit >= 32:
            length = _read_length_from_bits(output_bits)
            if length > 1_000_000:
                raise ValueError("Implausible payload length: wrong passphrase or not this classroom format")
            if bit >= 32 + length * 8:
                break

    if bit < 32:
        raise ValueError("Not enough payload bits: wrong passphrase or not this classroom format")
    length = _read_length_from_bits(output_bits)
    if length > 1_000_000 or bit < 32 + length * 8:
        raise ValueError("Payload incomplete: wrong passphrase or insufficient capacity")
    payload = bytes(
        sum(_get_bit(output_bits, 32 + 8 * j + k, bit) << (7 - k) for k in range(8))
        for j in range(length)
    )
    Path(output_path).write_bytes(payload)
    print(f"Extracted {len(payload)}-byte payload to {output_path}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    hist = sub.add_parser("hist", help="write signed luminance AC coefficient histogram CSV")
    hist.add_argument("input")
    hist.add_argument("output")
    embed = sub.add_parser("embed", help="embed a payload in a cover JPEG (instructor use)")
    embed.add_argument("input")
    embed.add_argument("output")
    embed.add_argument("payload")
    embed.add_argument("--passphrase", required=True)
    extract = sub.add_parser("extract", help="extract a teaching payload from a JPEG")
    extract.add_argument("input")
    extract.add_argument("output")
    extract.add_argument("--passphrase", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "hist":
            command_hist(args.input, args.output)
        elif args.command == "embed":
            command_embed(args.input, args.output, args.payload, args.passphrase)
        elif args.command == "extract":
            command_extract(args.input, args.output, args.passphrase)
    except (ValueError, OSError, RuntimeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
