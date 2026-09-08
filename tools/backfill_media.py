#!/usr/bin/env python3
"""为“已发布但漏图”的帖子回补图片：删除旧文字帖 -> 标记为待重发。

映射依据：@allcallsad 中测试消息为 3，此后我们按 published.ndjson 顺序
连续发送，频道消息 id = 4 + published 顺序下标（已由 fix 日志验证）。
"""

import json
import os
import urllib.parse
import urllib.request

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHAT = "@allcallsad"
BASE_CHANNEL_MSG = 4

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
HISTORY = os.path.join(DATA, "history.ndjson")
PUBLISHED = os.path.join(DATA, "published.ndjson")


def api(method, params=None):
    data = urllib.parse.urlencode(params or {}).encode()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{TOKEN}/{method}", data=data
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def main():
    if not TOKEN:
        print("SKIP no token")
        return
    history = {}
    for line in open(HISTORY, encoding="utf-8"):
        line = line.strip()
        if line:
            m = json.loads(line)
            history[m["id"]] = m

    entries = []
    for line in open(PUBLISHED, encoding="utf-8"):
        line = line.strip()
        if line:
            entries.append(json.loads(line))

    candidates = []
    for idx, entry in enumerate(entries):
        hid = entry["id"]
        src = history.get(hid) or {}
        has_media = bool(src.get("media"))
        media_sent = int(entry.get("mediaSent") or 0)
        if has_media and not media_sent:
            candidates.append({"channelMsg": BASE_CHANNEL_MSG + idx, "id": hid})

    print("CANDIDATES", json.dumps(candidates, ensure_ascii=False))
    deleted = 0
    for cand in sorted(candidates, key=lambda x: -x["channelMsg"]):
        try:
            api("deleteMessage", {"chat_id": CHAT, "message_id": cand["channelMsg"]})
            deleted += 1
            print("DELETED", cand["channelMsg"], cand["id"])
        except Exception as e:
            print("DELETE_FAIL", cand["channelMsg"], cand["id"], type(e).__name__, e)

    remove_ids = {c["id"] for c in candidates}
    if remove_ids:
        kept = [e for e in entries if e["id"] not in remove_ids]
        with open(PUBLISHED, "w", encoding="utf-8") as f:
            for e in kept:
                f.write(json.dumps(e, ensure_ascii=False) + "\n")
        print("REMAIN", len(kept), "REMOVED", len(remove_ids))
    print(json.dumps({"deleted": deleted, "candidates": len(candidates)}))


if __name__ == "__main__":
    main()
