#!/usr/bin/env python3
import argparse
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source")
    parser.add_argument("output")
    args = parser.parse_args()

    lines = Path(args.source).read_text(encoding="utf-8").splitlines()
    cleaned = []
    for line in lines:
        if line.strip() == "......":
            if cleaned and cleaned[-1] != "":
                cleaned.append("")
            continue
        cleaned.append(line.rstrip())

    while cleaned and cleaned[-1] == "":
        cleaned.pop()
    Path(args.output).write_text("\n".join(cleaned) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

