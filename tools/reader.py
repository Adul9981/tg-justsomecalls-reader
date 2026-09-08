#!/usr/bin/env python3
"""
Cloud reader for t.me/justsomecalls public web preview.

用法（GitHub Actions / 任意有外网的机器）:
    python3 tools/reader.py --probe       # 探测并输出摘要
    python3 tools/reader.py --json        # 输出本次抓取到的最新一页消息(JSON)
    python3 tools/reader.py --before ID   # 抓取 ID 之前的更早一页
"""

import json
import html as htmlmod
import re
import sys
import urllib.request

CHANNEL = "justsomecalls"
BASE = f"https://t.me/s/{CHANNEL}"
UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)


def fetch_page(before=None, timeout=30):
    url = BASE + (f"?before={before}" if before else "")
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": UA,
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        status = resp.status
        html = resp.read().decode("utf-8", errors="replace")
    return status, html


def parse(html):
    """解析公开预览页中的消息。"""
    messages = []
    # 每条消息形如: class="tgme_widget_message ..." data-post="justsomecalls/123"
    chunks = re.split(r'class="tgme_widget_message[\s"][^>]*data-post="', html)
    for chunk in chunks[1:]:
        post_id = chunk.split('"', 1)[0]
        date = None
        mtime = re.search(r'<time datetime="([^"]+)"', chunk)
        if mtime:
            date = mtime.group(1)
        text = ""
        mtext = re.search(
            r'<div class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>',
            chunk,
            re.S,
        )
        if mtext:
            text = mtext.group(1)
            text = re.sub(r"<br\s*/?>", "\n", text)
            text = re.sub(r"<[^>]+>", "", text)
            text = htmlmod.unescape(text)
            text = re.sub(r"[ \t]+\n", "\n", text).strip()
        messages.append({"id": post_id, "date": date, "text": text})
    return messages


def main():
    args = sys.argv[1:]
    mode = "probe"
    before = None
    if "--json" in args:
        mode = "json"
    if "--before" in args:
        before = args[args.index("--before") + 1]

    try:
        status, html = fetch_page(before)
    except Exception as e:
        print(json.dumps({"ok": False, "error": f"{type(e).__name__}: {e}"}))
        sys.exit(1)

    messages = parse(html)
    if mode == "json":
        print(
            json.dumps(
                {
                    "ok": True,
                    "httpStatus": status,
                    "channel": CHANNEL,
                    "count": len(messages),
                    "messages": messages,
                },
                ensure_ascii=False,
            )
        )
        return

    # probe 摘要，便于在 Actions 日志里一眼确认
    print(f"HTTP={status} htmlBytes={len(html)} messages={len(messages)}")
    ids = [m["id"] for m in messages]
    print(f"idRange={ids[-1] if ids else None}..{ids[0] if ids else None}")
    for m in messages[:3]:
        snippet = (m["text"] or "").replace("\n", " ")[:180]
        print(f"- {m['id']} {m['date']} | {snippet}")
    if not messages:
        title = re.search(r"<title>(.*?)</title>", html, re.S)
        print("TITLE:", title.group(1).strip() if title else "?")
        print("HAS_PREVIEW_PAGE:", "tgme_page" in html)


if __name__ == "__main__":
    main()
