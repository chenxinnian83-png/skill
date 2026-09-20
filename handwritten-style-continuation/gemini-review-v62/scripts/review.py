#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read_text(path):
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(str(path))
    return path.read_text(encoding="utf-8")


def read_json(path):
    return json.loads(read_text(path))


def canonical(text):
    return text.replace("\r\n", "\n").replace("\r", "\n").strip()


def compact(text):
    return re.sub(r"\s+", "", canonical(text))


def digest(text):
    return hashlib.sha256(canonical(text).encode("utf-8")).hexdigest()


def stable_digest(value):
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def label(name, text):
    return f"===== {name} =====\n{text.rstrip()}\n===== END {name} ====="


def strip_fence(text):
    value = text.strip()
    if value.startswith("```json"):
        value = value[7:]
    elif value.startswith("```"):
        value = value[3:]
    if value.endswith("```"):
        value = value[:-3]
    return value.strip()


def backend_settings(config):
    backend = (os.getenv("REVIEW_BACKEND") or config.get("backend") or "").strip().lower()
    if backend not in {"local_gemini", "custom"}:
        raise ValueError("unsupported backend: " + backend)
    section = config.get(backend, {})
    if backend == "local_gemini":
        prefix = "GEMINI_REVIEW"
    else:
        prefix = "CUSTOM_REVIEW"
    api_base = (os.getenv(prefix + "_API_BASE") or section.get("api_base") or "").rstrip("/")
    model = os.getenv(prefix + "_MODEL") or section.get("model") or ""
    api_key = os.getenv(prefix + "_API_KEY") or ""
    env_json = os.getenv(prefix + "_JSON_MODE")
    json_mode = env_json.strip().lower() == "true" if env_json else bool(section.get("json_mode", True))
    if not api_base or not model:
        raise ValueError("review api_base and model are required")
    uri = api_base if api_base.endswith("/chat/completions") else api_base + "/chat/completions"
    return backend, uri, model, api_key, json_mode


def validate_common(obj):
    required = {"verdict", "restart_from", "summary", "issue_codes", "evidence"}
    if not isinstance(obj, dict) or not required.issubset(obj):
        raise ValueError("review JSON missing required fields")
    if obj["verdict"] not in {"PASS", "FAIL"}:
        raise ValueError("invalid verdict")
    if not isinstance(obj["issue_codes"], list) or not isinstance(obj["evidence"], list):
        raise ValueError("issue_codes and evidence must be arrays")
    if obj["verdict"] == "FAIL" and not obj["evidence"]:
        raise ValueError("FAIL requires evidence")


def validate_style(obj, target, mother):
    validate_common(obj)
    axes = {
        "surface_language",
        "syntactic_motion",
        "narrator_voice",
        "modification_habit",
        "paragraph_assembly",
        "rhythm_shift",
    }
    scores = obj.get("axis_scores")
    if not isinstance(scores, dict) or set(scores) != axes:
        raise ValueError("invalid axis_scores")
    if any(not isinstance(scores[key], int) or not 0 <= scores[key] <= 4 for key in axes):
        raise ValueError("axis scores must be integers from 0 to 4")
    for evidence in obj["evidence"]:
        if not isinstance(evidence, dict):
            raise ValueError("style evidence must be objects")
        if not {"target_quote", "mother_quote", "dimension", "analysis"}.issubset(evidence):
            raise ValueError("style evidence missing fields")
        for field in ("target_quote", "dimension", "analysis"):
            if not isinstance(evidence[field], str) or not evidence[field].strip():
                raise ValueError("style evidence contains an empty required field")
        if compact(evidence["target_quote"]) not in compact(target):
            raise ValueError("style target_quote is not present in the reviewed text")
        mother_quote = evidence["mother_quote"]
        if not isinstance(mother_quote, str):
            raise ValueError("style mother_quote must be a string")
        if obj["verdict"] == "PASS" and not mother_quote.strip():
            raise ValueError("PASS style evidence requires a mother_quote")
        if mother_quote.strip() and compact(mother_quote) not in compact(mother):
            raise ValueError("style mother_quote is not present in the mother text")
    average = sum(scores.values()) / len(scores)
    eligible = min(scores.values()) >= 3 and average >= 3.3 and len(obj["evidence"]) >= 3
    if obj["verdict"] == "PASS" and not eligible:
        obj["verdict"] = "FAIL"
        obj["restart_from"] = obj.get("restart_from") or "正文开头"
        obj["issue_codes"] = list(dict.fromkeys(obj["issue_codes"] + ["INSUFFICIENT_POSITIVE_EVIDENCE"]))
        obj["summary"] = "未达到文风 PASS 的正向证据与维度阈值。"
    return obj


def invoke(uri, model, api_key, json_mode, prompt, user_input, protocol, stage):
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": prompt},
            {"role": "user", "content": user_input},
        ],
        "temperature": protocol["review_temperature"],
        "max_tokens": protocol["max_output_tokens"],
        "stream": False,
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = "Bearer " + api_key
    retryable = {408, 429, 500, 502, 503, 504}
    last_error = None
    for attempt in range(1, protocol["max_attempts"] + 1):
        request = urllib.request.Request(uri, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=600) as response:
                wrapper = json.loads(response.read().decode("utf-8"))
            content = wrapper["choices"][0]["message"]["content"]
            if not content or not content.strip():
                raise ValueError(stage + " returned empty content")
            return json.loads(strip_fence(content))
        except urllib.error.HTTPError as error:
            body = error.read().decode("utf-8", errors="replace")
            last_error = RuntimeError(f"{stage} HTTP {error.code}: {body}")
            if error.code not in retryable:
                raise last_error
        except Exception as error:
            last_error = error
        if attempt < protocol["max_attempts"]:
            time.sleep(min(60, 8 * attempt))
    raise last_error or RuntimeError(stage + " failed")


def paths_for_mode(mode):
    if mode == "local":
        return (
            ROOT / "inbox" / "local" / "current_chunk.txt",
            ROOT / "result" / "local_review.json",
        )
    return (
        ROOT / "inbox" / "final" / "full_chapter.txt",
        ROOT / "result" / "final_review.json",
    )


def build_manifest(mode, target, mother, beats, draft, style_prompt, continuity_prompt, config, protocol):
    return {
        "mode": mode,
        "target_sha256": digest(target),
        "mother_sha256": digest(mother),
        "beats_sha256": digest(beats),
        "draft_sha256": digest(draft),
        "style_prompt_sha256": digest(style_prompt),
        "continuity_prompt_sha256": digest(continuity_prompt),
        "config_sha256": stable_digest(config),
        "protocol_sha256": stable_digest(protocol),
    }


def write_json(path, value):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run(mode):
    config = read_json(ROOT / "review-config.json")
    protocol = read_json(ROOT / "protocol.json")
    backend, uri, model, api_key, json_mode = backend_settings(config)
    target_path, result_path = paths_for_mode(mode)
    target = read_text(target_path)
    if not target.strip():
        raise ValueError("review input is empty")
    mother = read_text(ROOT / "reference" / "mother_text.txt")
    beats = read_text(ROOT / "inbox" / "context" / "current_beats.txt")
    draft = read_text(ROOT / "drafts" / "current_chapter.txt")
    style_prompt = read_text(ROOT / "prompts" / "style_review.md").strip()
    continuity_prompt = read_text(ROOT / "prompts" / "continuity_review.md").strip()
    manifest = build_manifest(mode, target, mother, beats, draft, style_prompt, continuity_prompt, config, protocol)
    manifest_hash = stable_digest(manifest)

    if mode == "local":
        tail = canonical(draft)[-protocol["local_tail_chars"]:]
        style_input = "\n\n".join([
            label("审稿模式", "Local"),
            label("唯一文风母版", mother),
            label("已通过正文尾窗，仅检查接缝", tail),
            label("本轮新增正文", target),
        ])
    else:
        style_input = "\n\n".join([
            label("审稿模式", "Final"),
            label("唯一文风母版", mother),
            label("完整章节正文", target),
        ])

    style = validate_style(
        invoke(uri, model, api_key, json_mode, style_prompt, style_input, protocol, "style"),
        target,
        mother,
    )
    continuity = None
    if style["verdict"] == "PASS":
        if mode == "local":
            continuity_input = "\n\n".join([
                label("审稿模式", "Local"),
                label("本章已通过正文", draft),
                label("用户细纲", beats),
                label("本轮新增正文", target),
            ])
        else:
            continuity_input = "\n\n".join([
                label("审稿模式", "Final"),
                label("用户细纲", beats),
                label("完整章节正文", target),
            ])
        continuity = invoke(uri, model, api_key, json_mode, continuity_prompt, continuity_input, protocol, "continuity")
        validate_common(continuity)

    passed = style["verdict"] == "PASS" and continuity is not None and continuity["verdict"] == "PASS"
    failed_stage = "" if passed else "style" if style["verdict"] == "FAIL" else "continuity"
    decisive = style if failed_stage == "style" else continuity
    output = {
        "status": "COMPLETE",
        "protocol_version": protocol["protocol_version"],
        "input_manifest_sha256": manifest_hash,
        **manifest,
        "backend": backend,
        "model": model,
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
        "verdict": "PASS" if passed else "FAIL",
        "failed_stage": failed_stage,
        "restart_from": "" if passed else str(decisive.get("restart_from", "")),
        "style_review": style,
        "continuity_review": continuity,
    }
    write_json(result_path, output)
    receipt = ROOT / "result" / "receipts" / f"{mode}-{manifest_hash}.json"
    write_json(receipt, output)
    print(json.dumps(output, ensure_ascii=True))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", required=True, choices=["local", "final"])
    args = parser.parse_args()
    try:
        run(args.mode)
    except Exception as error:
        target_path, result_path = paths_for_mode(args.mode)
        target = read_text(target_path) if target_path.exists() else ""
        protocol = read_json(ROOT / "protocol.json")
        output = {
            "status": "REVIEW_ERROR",
            "protocol_version": protocol.get("protocol_version", ""),
            "target_sha256": digest(target),
            "reviewed_at": datetime.now(timezone.utc).isoformat(),
            "error_type": type(error).__name__,
            "error": str(error),
        }
        write_json(result_path, output)
        print(json.dumps(output, ensure_ascii=True), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
