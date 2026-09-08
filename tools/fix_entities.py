#!/usr/bin/env python3
"""修正已发消息中的 HTML 实体残留（&#036; -> $），避免频道出现乱码符号。"""

import json
import os
import urllib.parse
import urllib.request

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")


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
    try:
        updates = api("getUpdates", {"timeout": 0, "allowed_updates": '["channel_post"]'}).get("result", [])
    except Exception as e:
        print("getUpdates failed:", e)
        return

    fixed = 0
    for u in updates:
        post = u.get("channel_post") or {}
        chat = post.get("chat", {})
        if chat.get("type") != "channel":
            continue
        text = post.get("text") or ""
        if "&#036;" not in text and "&#x24;" not in text:
            continue
        new_text = text.replace("&#036;", "$").replace("&#x24;", "$")
        try:
            api(
                "editMessageText",
                {
                    "chat_id": chat["id"],
                    "message_id": post["message_id"],
                    "text": new_text,
                    "disable_web_page_preview": True,
                },
            )
            fixed += 1
            print("FIXED", chat.get("username"), post["message_id"])
        except Exception as e:
            print("EDIT_FAIL", post["message_id"], e)
    print(json.dumps({"fixed": fixed, "updates": len(updates)}))


if __name__ == "__main__":
    main()
