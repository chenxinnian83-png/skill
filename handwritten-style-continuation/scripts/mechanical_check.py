#!/usr/bin/env python3
import argparse
import re
import sys
from collections import Counter
from pathlib import Path


def paragraphs(text):
    return [line.strip() for line in text.splitlines() if line.strip() and set(line.strip()) != {"."}]


def sentences(text):
    return [item.strip() for item in re.split(r"[。！？!?]+", text) if item.strip()]


def hanzi_count(text):
    return len(re.findall(r"[\u4e00-\u9fff]", text))


def ngrams(text, size):
    compact = re.sub(r"\s+", "", text)
    return {compact[i:i + size] for i in range(max(0, len(compact) - size + 1))}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("candidate")
    parser.add_argument("--mother", required=True)
    args = parser.parse_args()

    text = Path(args.candidate).read_text(encoding="utf-8")
    mother = Path(args.mother).read_text(encoding="utf-8")
    issues = []

    if "\ufffd" in text or re.search(r"\{\{.*?\}\}|\[TODO\]|<PLACEHOLDER>", text, re.I | re.S):
        issues.append("存在乱码或未替换占位符")

    counts = Counter(sentences(text))
    repeated = [sentence for sentence, count in counts.items() if count >= 3 and hanzi_count(sentence) >= 6]
    if repeated:
        issues.append("同一完整句重复三次以上：" + "｜".join(repeated[:3]))

    paras = paragraphs(text)
    run = []
    longest = []
    for para in paras:
        is_dialogue = para.startswith(("“", "「", "『")) or "道：“" in para or "问：“" in para
        if not is_dialogue and hanzi_count(para) < 12:
            run.append(para)
            if len(run) > len(longest):
                longest = list(run)
        else:
            run = []
    if len(longest) >= 5:
        issues.append("连续五个以上非对话短段，需要人工确认是否碎段表演")

    candidate_ngrams = ngrams(text, 24)
    mother_ngrams = ngrams(mother, 24)
    overlap = sorted(candidate_ngrams & mother_ngrams)
    if overlap:
        issues.append("发现与母版连续24字符重合，疑似复制：" + "｜".join(overlap[:3]))

    length = hanzi_count(text)
    if length < 250:
        issues.append(f"候选过短：{length}个汉字")
    if length > 1000:
        issues.append(f"候选过长：{length}个汉字")

    if issues:
        for issue in issues:
            print("FAIL " + issue)
        sys.exit(1)

    print(f"PASS 汉字数={length} 段落数={len(paras)}")


if __name__ == "__main__":
    main()

