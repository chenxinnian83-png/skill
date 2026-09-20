#!/usr/bin/env python3
import argparse
import re
from pathlib import Path


def hanzi_count(text):
    return len(re.findall(r"[\u4e00-\u9fff]", text))


def status(count):
    if count < 1200:
        return "HOLD"
    if count <= 1800:
        return "READY"
    return "READY_OVER_TARGET"


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    add = sub.add_parser("add")
    add.add_argument("batch")
    add.add_argument("candidate")
    check = sub.add_parser("status")
    check.add_argument("batch")
    clear = sub.add_parser("clear")
    clear.add_argument("batch")
    args = parser.parse_args()

    batch = Path(args.batch)
    if args.command == "add":
        candidate = Path(args.candidate).read_text(encoding="utf-8").strip()
        if not candidate:
            raise SystemExit("candidate is empty")
        existing = batch.read_text(encoding="utf-8").strip() if batch.exists() else ""
        joined = existing + ("\n\n......\n\n" if existing else "") + candidate + "\n"
        batch.parent.mkdir(parents=True, exist_ok=True)
        batch.write_text(joined, encoding="utf-8")
    elif args.command == "clear":
        batch.parent.mkdir(parents=True, exist_ok=True)
        batch.write_text("", encoding="utf-8")

    text = batch.read_text(encoding="utf-8") if batch.exists() else ""
    count = hanzi_count(text)
    print(f"{status(count)} 汉字数={count}")


if __name__ == "__main__":
    main()
