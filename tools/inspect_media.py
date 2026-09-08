#!/usr/bin/env python3
"""探查 t.me/s/justsomecalls 预览页中的媒体标签结构（图片/视频），供开发使用。"""

import re
import sys
import urllib.request

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"


def main():
    req = urllib.request.Request(
        "https://t.me/s/justsomecalls",
        headers={"User-Agent": UA},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        html = r.read().decode("utf-8", errors="replace")

    tags = {}
    for cls in [
        "tgme_widget_message_photo",
        "tgme_widget_message_video",
        "tgme_widget_message_document",
        "tgme_widget_message_voice",
        "tgme_widget_message_roundvideo",
        "tgme_widget_message_sticker",
        "tgme_widget_message_link_preview",
    ]:
        tags[cls] = html.count(cls)

    print("TAG_COUNTS", tags)

    # 抓取任意含 photo/video 的整段 HTML 片段，便于人工确认结构
    shown = 0
    for m in re.finditer(r'<div class="tgme_widget_message_wrap.*?</div>\s*</div>\s*</div>', html, re.S):
        block = m.group(0)
        if ("photo" in block or "video" in block) and shown < 4:
            print("BLOCK_START", block[:1400].replace("\n", " "))
            shown += 1


if __name__ == "__main__":
    main()
