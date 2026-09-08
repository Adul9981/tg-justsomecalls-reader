#!/usr/bin/env python3
"""从频道公开预览读取已发消息，修正残留 HTML 实体（&#036; -> $）。"""

import html as htmlmod
import json
import os
import re
import urllib.parse
import urllib.request

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHANNEL = "allcallsad"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"


def fetch_preview():
    req = urllib.request.Request(
        f"https://t.me/s/{CHANNEL}",
        headers={"User-Agent": UA},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", errors="replace")


def api(method, params=None):
    data = urllib.parse.urlencode(params or {}).encode()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{TOKEN}/{method}", data=data
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def main():
    html = fetch_preview()
    fixed = 0
    for chunk in re.split(r'class="tgme_widget_message[\s"][^>]*data-post="', html)[1:]:
        post_ref = chunk.split('"', 1)[0]  # allcallsad/5
        msg_id = post_ref.split("/")[-1]
        m = re.search(
            r'<div class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>',
            chunk,
            re.S,
        )
        if not m:
            continue
        text = m.group(1)
        text = re.sub(r"<br\s*/?>", "\n", text)
        text = re.sub(r"<[^>]+>", "", text)
        text = htmlmod.unescape(text)
        if "&#036;" in text or "&#x24;" in text:
            new_text = text.replace("&#036;", "$").replace("&#x24;", "$")
            try:
                params = {
                    "chat_id": f"@{CHANNEL}",
                    "message_id": int(msg_id),
                }
                if "tgme_widget_message_photo_wrap" in chunk:
                    params["caption"] = new_text
                    api("editMessageCaption", params)
                else:
                    params["text"] = new_text
                    params["disable_web_page_preview"] = True
                    api("editMessageText", params)
                fixed += 1
                print("FIXED", msg_id)
            except Exception as e:
                print("EDIT_FAIL", msg_id, type(e).__name__, e)
    print(json.dumps({"fixed": fixed}))


if __name__ == "__main__":
    main()
