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
    known_ids = set(known.keys())
    prev_max = None
    if known_ids:
        prev_max = max(int(i.split("/")[-1]) for i in known_ids)

    new = []
    for m in messages:
        if m["id"] not in known_ids:
            known_ids.add(m["id"])
            known[m["id"]] = m
            new.append(m)

    # 若两次运行之间发帖超过一页，向更早分页补抓，直到接上已存记录
    pages = 1
    while pages < 60 and prev_max is not None:
        cur_min = min(int(m["id"].split("/")[-1]) for m in messages)
        if cur_min <= prev_max + 1:
            break
        try:
            _, older_html = fetch_page(before=messages[0]["id"])
        except Exception as e:
            print("BACKFILL_FAIL", type(e).__name__, e)
            break
        older = parse(older_html)
        if not older:
            break
        pages += 1
        for m in older:
            if m["id"] not in known_ids:
                known_ids.add(m["id"])
                known[m["id"]] = m
                new.append(m)
        messages = older

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
    print("pagesFetched=", pages)
    print("checkedAt=", datetime.now(timezone.utc).isoformat())


if __name__ == "__main__":
    main()
