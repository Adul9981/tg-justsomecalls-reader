#!/usr/bin/env python3
"""取最新 N 条消息做 DeepSeek 翻译（只输出对照，不发布），供人工审稿。"""

import html as htmlmod
import json
import os
import re
import sys

import publish

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LATEST = os.path.join(ROOT, "data", "latest.json")
N = int(os.environ.get("BATCH_SIZE", "8"))


def main():
    if not os.path.exists(LATEST):
        print("NO_DATA")
        sys.exit(1)
    data = json.load(open(LATEST, encoding="utf-8"))
    data = [m for m in data if (m.get("text") or "").strip()]
    data = sorted(data, key=lambda x: int(x["id"].split("/")[-1]))[-N:]

    for m in data:
        raw = re.sub(r"\s+", " ", m.get("text") or "").strip()
        raw = htmlmod.unescape(raw)
        try:
            zh = publish.translate(raw)
        except Exception as e:
            print(json.dumps({"id": m["id"], "error": f"{type(e).__name__}: {e}"}, ensure_ascii=False))
            continue
        print(
            json.dumps(
                {"id": m["id"], "en": raw, "zh": zh},
                ensure_ascii=False,
            )
        )


if __name__ == "__main__":
    main()
