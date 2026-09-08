#!/usr/bin/env python3
"""
翻译并发布：读取 data/ 中新消息 -> 翻译为简体中文 -> 发到 Telegram 中文频道。

翻译引擎:
  DeepSeek API（OpenAI 兼容），环境变量 DEEPSEEK_API_KEY + DEEPSEEK_MODEL。

去重：data/published.ndjson 记录已发布消息 id。
"""

import json
import mimetypes
import os
import re
import sys
import time
import urllib.parse
import urllib.request

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHAT = os.environ.get("TARGET_CHAT", "@allcallsad")
DEEPSEEK_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")
DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"
USAGE = {"prompt_tokens": 0, "completion_tokens": 0}

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
HISTORY = os.path.join(DATA, "history.ndjson")
PUBLISHED = os.path.join(DATA, "published.ndjson")


def tg_api(method, params):
    data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{TOKEN}/{method}", data=data
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def tg_upload(method, fields, file_field, filename, filedata, content_type):
    """以 multipart/form-data 上传媒体文件到 Bot API。"""
    boundary = "----TgMirror" + os.urandom(8).hex()
    body = bytearray()

    def add_field(name, value):
        body.extend(
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n{value}\r\n".encode()
        )

    def add_file():
        body.extend(
            (
                f"--{boundary}\r\n"
                f"Content-Disposition: form-data; name=\"{file_field}\"; filename=\"{filename}\"\r\n"
                f"Content-Type: {content_type}\r\n\r\n"
            ).encode()
        )
        body.extend(filedata)
        body.extend(b"\r\n")

    for k, v in fields.items():
        add_field(k, str(v))
    add_file()
    body.extend(f"--{boundary}--\r\n".encode())

    req = urllib.request.Request(
        f"https://api.telegram.org/bot{TOKEN}/{method}",
        data=bytes(body),
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.loads(r.read().decode())


def fetch_media(url):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 Chrome/124.0 Safari/537.36"
            )
        },
    )
    with urllib.request.urlopen(req, timeout=90) as r:
        data = r.read()
        ctype = r.headers.get("Content-Type") or "image/jpeg"
    return data, ctype


def split_text(text, limit=900):
    chunks = []
    while text:
        chunks.append(text[:limit])
        text = text[limit:]
    return chunks


def translate_deepseek(text):
    body = {
        "model": DEEPSEEK_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "你是加密货币交易频道的中文翻译。把英文内容翻译成简体中文。"
                    "要求：通顺自然、保留全部事实与数字；代币符号($XXX)、"
                    "交易所/平台/项目专有名词、网址、@用户名、$TICKER 保留原文；"
                    "不要添加解释或建议；输出只给译文。"
                ),
            },
            {"role": "user", "content": text},
        ],
        "temperature": 0.3,
        "max_tokens": 4000,
    }
    req = urllib.request.Request(
        DEEPSEEK_URL,
        data=json.dumps(body).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {DEEPSEEK_KEY}",
        },
    )
    with urllib.request.urlopen(req, timeout=90) as r:
        result = json.loads(r.read().decode())
    usage = result.get("usage") or {}
    USAGE["prompt_tokens"] += int(usage.get("prompt_tokens", 0) or 0)
    USAGE["completion_tokens"] += int(usage.get("completion_tokens", 0) or 0)
    return result["choices"][0]["message"]["content"].strip()


def translate(text):
    return translate_deepseek(text)


def load_published():
    ids = set()
    if os.path.exists(PUBLISHED):
        for line in open(PUBLISHED, encoding="utf-8"):
            line = line.strip()
            if line:
                try:
                    ids.add(json.loads(line)["id"])
                except Exception:
                    pass
    return ids


def clean_text(text):
    text = re.sub(r"\s+", " ", text or "").strip()
    return text


def main():
    if not TOKEN:
        print("SKIP no bot token")
        return
    if not os.path.exists(HISTORY):
        print("SKIP no history yet")
        return

    published = load_published()
    pending = []
    for line in open(HISTORY, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        m = json.loads(line)
        if m["id"] not in published:
            pending.append(m)

    if not pending:
        print("NO_NEW")
        return

    pending.sort(key=lambda x: int(x["id"].split("/")[-1]))
    sent = 0
    failed = []
    for m in pending:
        raw = clean_text(m.get("text") or "")
        if not raw:
            # 无正文（纯图片/转发）时仍发原链接便于人工查看
            urls = re.findall(r"https?://[^\s]+", m.get("text") or "")
            if not urls:
                continue
            body = urls[0]
        else:
            try:
                body = translate(raw)
            except Exception as e:
                print("DEEPSEEK_FAIL", m["id"], type(e).__name__, e)
                failed.append({"id": m["id"], "error": f"{type(e).__name__}: {e}"})
                if len(failed) >= 3:
                    break
                continue
        body = (body or "").strip()
        chunks = split_text(body) if body else []
        media = m.get("media") or []
        print("TRANSLATED", m["id"], "|", body[:120].replace("\n", " ") if body else "(media only)", "media=", len(media))
        try:
            media_ok = 0
            if media:
                for idx, item in enumerate(media):
                    if item.get("type") != "photo":
                        continue
                    try:
                        filedata, ctype = fetch_media(item["url"])
                    except Exception as e:
                        print("MEDIA_DL_FAIL", m["id"], idx, type(e).__name__, e)
                        continue
                    if len(filedata) > 10 * 1024 * 1024:
                        print("MEDIA_TOO_BIG", m["id"], idx, len(filedata))
                        continue
                    ext = mimetypes.guess_extension(ctype.split(";")[0].strip()) or ".jpg"
                    filename = f"justsomecalls-{m['id'].split('/')[-1]}-{idx}{ext}"
                    fields = {"chat_id": CHAT, "disable_web_page_preview": True}
                    if idx == 0 and chunks:
                        fields["caption"] = chunks.pop(0)
                    tg_upload("sendPhoto", fields, "photo", filename, filedata, ctype)
                    media_ok += 1
                    time.sleep(3)
            for chunk in chunks:
                tg_api(
                    "sendMessage",
                    {
                        "chat_id": CHAT,
                        "text": chunk[:4000],
                        "disable_web_page_preview": True,
                    },
                )
                time.sleep(3)
            with open(PUBLISHED, "a", encoding="utf-8") as f:
                f.write(
                    json.dumps(
                        {
                            "id": m["id"],
                            "publishedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                            "mediaSent": media_ok,
                        }
                    )
                    + "\n"
                )
            published.add(m["id"])
            sent += 1
        except Exception as e:
            failed.append({"id": m["id"], "error": f"{type(e).__name__}: {e}"})
            print("FAIL", m["id"], type(e).__name__, e)
            if len(failed) >= 3:
                break

    print(
        json.dumps(
            {
                "ok": not failed,
                "new": len(pending),
                "sent": sent,
                "failed": failed,
                "deepseekUsage": USAGE,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
