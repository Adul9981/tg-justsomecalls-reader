#!/usr/bin/env python3
"""验证 Telegram Bot：token、目标频道、管理员权限，并发送一条测试消息。"""

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHAT = "@allcallsad"


def api(method, params=None):
    url = f"https://api.telegram.org/bot{TOKEN}/{method}"
    data = urllib.parse.urlencode(params or {}).encode()
    req = urllib.request.Request(url, data=data)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def main():
    if not TOKEN:
        print(json.dumps({"ok": False, "error": "TELEGRAM_BOT_TOKEN not set"}))
        sys.exit(1)

    out = {}
    try:
        me = api("getMe")["result"]
        out["me"] = {"id": me["id"], "username": me.get("username"), "name": me.get("first_name")}
    except Exception as e:
        print(json.dumps({"ok": False, "step": "getMe", "error": str(e)}))
        sys.exit(1)

    try:
        chat = api("getChat", {"chat_id": CHAT})["result"]
        out["chat"] = {
            "id": chat["id"],
            "title": chat.get("title"),
            "type": chat.get("type"),
            "username": chat.get("username"),
        }
    except Exception as e:
        print(json.dumps({"ok": False, "step": "getChat", "chat": CHAT, "error": str(e)}))
        sys.exit(1)

    try:
        member = api("getChatMember", {"chat_id": CHAT, "user_id": me["id"]})["result"]
        out["member"] = {
            "status": member.get("status"),
            "canPostMessages": member.get("can_post_messages"),
            "customTitle": member.get("custom_title"),
        }
    except Exception as e:
        print(json.dumps({"ok": False, "step": "getChatMember", "error": str(e)}))
        sys.exit(1)

    status = out["member"].get("status")
    if status != "administrator":
        print(json.dumps({"ok": False, "error": "bot is not an admin", **out}))
        sys.exit(1)

    try:
        sent = api(
            "sendMessage",
            {
                "chat_id": CHAT,
                "text": "✅ 连接正常：中文镜像频道已就绪（测试消息）\n\n由 tg-justsomecalls-reader 云端服务发出",
                "disable_web_page_preview": True,
            },
        )["result"]
        out["testMessage"] = {"messageId": sent["message_id"], "date": sent["date"]}
    except Exception as e:
        print(json.dumps({"ok": False, "step": "sendMessage", "error": str(e), **out}))
        sys.exit(1)

    out["ok"] = True
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()
