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

    # 折叠空白后打印媒体标签附近 HTML，便于确认取图方式
    compact = re.sub(r"\s+", " ", html)
    shown = 0
    for m in re.finditer(r".{260}tgme_widget_message_photo.{520}", compact):
        print("MEDIA_WINDOW", m.group(0))
        shown += 1
        if shown >= 5:
            break


if __name__ == "__main__":
    main()
