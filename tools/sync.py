#!/usr/bin/env python3
"""
定时同步：抓取 t.me/justsomecalls 最新一页 -> 去重 -> 写入仓库 data/。

- data/latest.json      最近一次抓取的全部消息（上限 200 条）
- data/history.ndjson   全部已抓取消息的增量存档（每行一条）
"""

import json
import os
import sys
from datetime import datetime, timezone

from reader import fetch_page, parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
LATEST = os.path.join(DATA, "latest.json")
HISTORY = os.path.join(DATA, "history.ndjson")


def load_existing():
    known = {}
    if os.path.exists(LATEST):
        try:
            for m in json.load(open(LATEST, encoding="utf-8")):
                known[m["id"]] = m
        except Exception:
            pass
    if os.path.exists(HISTORY):
        for line in open(HISTORY, encoding="utf-8"):
            line = line.strip()
            if line:
                try:
                    m = json.loads(line)
                    known[m["id"]] = m
                except Exception:
                    pass
    return known


def main():
    os.makedirs(DATA, exist_ok=True)
    try:
        status, html = fetch_page()
    except Exception as e:
        print(f"FETCH_FAIL {type(e).__name__}: {e}")
        sys.exit(1)

    messages = parse(html)
    if not messages:
        print("EMPTY_PAGE status=", status)
        sys.exit(1)

    known = load_existing()
    new = []
    for m in messages:
        if m["id"] not in known:
            known[m["id"]] = m
            new.append(m)

    # latest.json 保留最新 200 条（含历史已知，便于回看）
    latest = sorted(known.values(), key=lambda x: int(x["id"].split("/")[-1]))[-200:]
    with open(LATEST, "w", encoding="utf-8") as f:
        json.dump(latest, f, ensure_ascii=False, indent=1)

    # history.ndjson 只追加真正的新消息
    if new:
        new_sorted = sorted(new, key=lambda x: int(x["id"].split("/")[-1]))
        with open(HISTORY, "a", encoding="utf-8") as f:
            for m in new_sorted:
                f.write(json.dumps(m, ensure_ascii=False) + "\n")

    ids = [m["id"] for m in messages]
    print(
        "OK http=%s pageMsgs=%s new=%s total=%s range=%s..%s"
        % (
            status,
            len(messages),
            len(new),
            len(known),
            ids[0].split("/")[-1],
            ids[-1].split("/")[-1],
        )
    )
    print("checkedAt=", datetime.now(timezone.utc).isoformat())


if __name__ == "__main__":
    main()
