#!/usr/bin/env python3
"""Convert Ripchord XML presets (.rpc) to Logic Pro Chord Trigger presets (.pst)."""

from __future__ import annotations

import argparse
import struct
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path


PST_VERSION = 1
CHORD_TRIGGER_PARAMETER_COUNT = 10
CHORD_TRIGGER_STATE_VERSION = 0x134


@dataclass(frozen=True)
class Mapping:
    trigger: int
    notes: tuple[int, ...]
    name: str


def midi_note(value: str, *, field: str, source: Path) -> int:
    try:
        note = int(value.strip())
    except (AttributeError, ValueError) as exc:
        raise ValueError(f"{source.name}: invalid {field}: {value!r}") from exc
    if not 0 <= note <= 127:
        raise ValueError(f"{source.name}: {field} {note} is outside MIDI range 0..127")
    return note


def read_rpc(source: Path) -> list[Mapping]:
    try:
        root = ET.parse(source).getroot()
    except ET.ParseError as exc:
        raise ValueError(f"{source.name}: invalid XML: {exc}") from exc

    # Current Ripchord files use preset/input. Older files used
    # KeyboardMapping/mapping, so accept either spelling.
    inputs = root.findall("./preset/input")
    if not inputs:
        inputs = root.findall("./KeyboardMapping/mapping")
    if not inputs:
        raise ValueError(f"{source.name}: no Ripchord mappings found")

    mappings: list[Mapping] = []
    seen: set[int] = set()
    for input_element in inputs:
        trigger = midi_note(input_element.get("note", ""), field="trigger note", source=source)
        if trigger in seen:
            raise ValueError(f"{source.name}: duplicate trigger note {trigger}")
        seen.add(trigger)

        chord = input_element.find("chord")
        if chord is None:
            raise ValueError(f"{source.name}: trigger {trigger} has no chord")
        raw_notes = chord.get("notes", "")
        notes = tuple(
            midi_note(part, field=f"output note for trigger {trigger}", source=source)
            for part in raw_notes.split(";")
            if part.strip()
        )
        if not notes:
            raise ValueError(f"{source.name}: trigger {trigger} has no output notes")

        mappings.append(Mapping(trigger, notes, chord.get("name", "")))

    return sorted(mappings, key=lambda mapping: mapping.trigger)


def make_pst(mappings: list[Mapping]) -> bytes:
    range_low = mappings[0].trigger
    range_high = mappings[-1].trigger

    # Chord Trigger's private state stores a Single-mode chord first, followed
    # by Multi-mode mappings. We leave the Single chord empty and serialize
    # every Ripchord assignment as an exact interval from its trigger note.
    state = bytearray(struct.pack("<I", 0))
    state.extend(struct.pack("<I", len(mappings)))
    for mapping in mappings:
        offsets = tuple(note - mapping.trigger for note in mapping.notes)
        state.extend(struct.pack("<II", mapping.trigger, len(offsets)))
        state.extend(struct.pack(f"<{len(offsets)}i", *offsets))

    # The ten Chord Trigger parameters include Multi mode, trigger range, the
    # selected trigger key, momentary UI controls, remote-learn assignment,
    # and transpose. Values match the layout used by Logic's factory presets.
    parameters = (
        0.0,
        1.0,
        float(range_low),
        float(range_high),
        float(range_low),
        0.0,
        0.0,
        0.0,
        20.0,
        0.0,
    )

    total_size = 72 + len(state)
    header = struct.pack(
        "<III4s4sI10fII",
        total_size,
        PST_VERSION,
        CHORD_TRIGGER_PARAMETER_COUNT,
        b"GAME",
        b"TSPP",
        CHORD_TRIGGER_STATE_VERSION,
        *parameters,
        0,
        len(state) + 8,
    )
    assert len(header) == 72
    return header + state


def validate_pst(data: bytes, expected: list[Mapping]) -> None:
    if len(data) < 80:
        raise ValueError("generated preset is unexpectedly short")
    total_size, version, parameter_count = struct.unpack_from("<III", data, 0)
    if total_size != len(data) or version != PST_VERSION or parameter_count != 10:
        raise ValueError("generated preset header failed validation")
    if data[12:20] != b"GAMETSPP":
        raise ValueError("generated preset signature failed validation")

    cursor = 72
    single_count = struct.unpack_from("<I", data, cursor)[0]
    cursor += 4 + single_count * 4
    mapping_count = struct.unpack_from("<I", data, cursor)[0]
    cursor += 4
    if mapping_count != len(expected):
        raise ValueError("generated mapping count failed validation")

    for mapping in expected:
        trigger, note_count = struct.unpack_from("<II", data, cursor)
        cursor += 8
        offsets = struct.unpack_from(f"<{note_count}i", data, cursor)
        cursor += note_count * 4
        notes = tuple(trigger + offset for offset in offsets)
        if trigger != mapping.trigger or notes != mapping.notes:
            raise ValueError(f"generated mapping for trigger {mapping.trigger} failed validation")
    if cursor != len(data):
        raise ValueError("generated preset has trailing data")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", nargs="*", type=Path, help="RPC files (default: *.rpc)")
    parser.add_argument("-o", "--output", type=Path, default=Path("Chord Trigger Presets"))
    parser.add_argument("--force", action="store_true", help="replace existing PST files")
    args = parser.parse_args()

    sources = sorted(args.inputs or Path.cwd().glob("*.rpc"))
    if not sources:
        parser.error("no .rpc files found")
    args.output.mkdir(parents=True, exist_ok=True)

    converted = 0
    for source in sources:
        mappings = read_rpc(source)
        data = make_pst(mappings)
        validate_pst(data, mappings)
        destination = args.output / f"{source.stem}.pst"
        if destination.exists() and not args.force:
            raise FileExistsError(f"refusing to replace {destination}; use --force")
        destination.write_bytes(data)
        print(
            f"{source.name} -> {destination} "
            f"({len(mappings)} mappings, triggers {mappings[0].trigger}-{mappings[-1].trigger})"
        )
        converted += 1

    print(f"Converted {converted} preset(s).")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (FileExistsError, OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
