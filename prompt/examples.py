#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""读取 prompts3.txt 中的示例提示词。"""

from __future__ import annotations

import os
import re
from typing import Any, Dict, List


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_EXAMPLES_PATH = os.path.join(PROJECT_ROOT, "prompt", "prompts3.txt")

_HEADER_RE = re.compile(r"^[①②③④⑤⑥⑦⑧⑨⑩]\s*(.+)$")
_SKIP_PREFIXES = ("MASK:", "这里是", "场景清楚")


def _clean_title(title: str) -> str:
    title = re.sub(r"[（(][^）)]*[）)]", "", title).strip()
    return re.sub(r"\s+", " ", title)


def load_example_prompts(path: str | None = None) -> List[Dict[str, str]]:
    """返回 ``[{"title": ..., "prompt": ...}, ...]``。"""
    path = path or DEFAULT_EXAMPLES_PATH
    with open(path, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()

    examples: List[Dict[str, Any]] = []
    current: Dict[str, Any] | None = None

    def flush() -> None:
        if current is not None and current["parts"]:
            current["prompt"] = "\n".join(current["parts"]).strip()
            current.pop("parts")
            examples.append(current)

    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        if any(line.startswith(prefix) for prefix in _SKIP_PREFIXES):
            continue

        match = _HEADER_RE.match(line)
        if match:
            flush()
            current = {"title": _clean_title(match.group(1)), "parts": []}
            continue

        if current is not None:
            current["parts"].append(line)

    flush()
    return examples


if __name__ == "__main__":
    import json

    for ex in load_example_prompts():
        print(ex["title"])
        print(ex["prompt"][:80].replace("\n", " "))
        print("-" * 60)
