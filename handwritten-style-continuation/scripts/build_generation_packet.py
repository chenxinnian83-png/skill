#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read_text(path):
    return Path(path).read_text(encoding="utf-8")


def load_json(path):
    return json.loads(read_text(path))


def normalized(values):
    if isinstance(values, str):
        values = [values]
    return {str(value).strip().lower() for value in values if str(value).strip()}


def score_segment(segment, scene, pressure):
    segment_scene = normalized(segment.get("scene", []))
    segment_pressure = normalized(segment.get("pressure", []))
    return 5 * len(scene & segment_scene) + 3 * len(pressure & segment_pressure)


def extract(lines, start, end):
    return "\n".join(lines[start - 1:end]).strip()


def validate_unit(unit):
    required = ["unit_id", "scene", "entry_fact", "required_events", "forbidden_events", "exit_fact"]
    missing = [key for key in required if key not in unit]
    if missing:
        raise ValueError("current_unit.json missing: " + ", ".join(missing))
    if not isinstance(unit["required_events"], list) or not isinstance(unit["forbidden_events"], list):
        raise ValueError("required_events and forbidden_events must be arrays")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--unit", required=True)
    parser.add_argument("--tail", required=True)
    parser.add_argument("--state", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    unit = load_json(args.unit)
    validate_unit(unit)
    state = load_json(args.state)
    tail = read_text(args.tail).strip()
    mother = read_text(ROOT / "references" / "mother_text.txt")
    index = load_json(ROOT / "references" / "mother_scene_index.json")
    protocol = read_text(ROOT / "references" / "generation_protocol.md").strip()

    scene = normalized(unit.get("scene", []))
    pressure = normalized(unit.get("pressure", []))
    ranked = sorted(
        index["segments"],
        key=lambda item: (-score_segment(item, scene, pressure), item["start_line"]),
    )
    selected = ranked[:2]
    lines = mother.splitlines()
    coverage = score_segment(selected[0], scene, pressure) if selected else 0

    parts = [
        "# 当前生成包",
        "",
        "## 参照覆盖",
        "",
        "OK" if coverage > 0 else "LOW_REFERENCE_COVERAGE",
        "",
        "## 当前事件契约",
        "",
        "```json",
        json.dumps(unit, ensure_ascii=False, indent=2),
        "```",
        "",
        "## 章节状态",
        "",
        "```json",
        json.dumps(state, ensure_ascii=False, indent=2),
        "```",
        "",
        "## 前文尾窗",
        "",
        tail,
    ]

    for number, segment in enumerate(selected, 1):
        parts.extend([
            "",
            f"## 母版连续参照 {number}｜{segment['id']}",
            "",
            extract(lines, segment["start_line"], segment["end_line"]),
        ])

    parts.extend(["", protocol, ""])
    Path(args.output).write_text("\n".join(parts), encoding="utf-8")


if __name__ == "__main__":
    main()

