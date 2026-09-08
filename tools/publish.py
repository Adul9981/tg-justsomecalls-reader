#!/usr/bin/env python3
"""
翻译并发布：读取 data/ 中新消息 -> 翻译为简体中文 -> 发到 Telegram 中文频道。

翻译引擎（自动选择）:
  1) 环境变量 OPENAI_API_KEY 存在 -> OpenAI 兼容 chat completions（质量优先）
  2) 否则 -> Google 免费翻译接口（无需密钥，质量一般）

去重：data/published.ndjson 记录已发布消息 id。
"""

import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHAT = os.environ.get("TARGET_CHAT", "@allcallsad")
OPENAI_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

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


def translate_openai(text):
    body = {
        "model": OPENAI_MODEL,
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
        "temperature": 0.2,
    }
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps(body).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {OPENAI_KEY}",
        },
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        result = json.loads(r.read().decode())
    return result["choices"][0]["message"]["content"].strip()


def translate_google(text):
    url = (
        "https://translate.googleapis.com/translate_a/single"
        "?client=gtx&sl=en&tl=zh-CN&dt=t&q="
        + urllib.parse.quote(text)
    )
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        result = json.loads(r.read().decode())
    return "".join(part[0] for part in result[0])


def translate(text):
    if not text or not text.strip():
        return ""
    if OPENAI_KEY:
        try:
            return translate_openai(text)
        except Exception as e:
            print("OPENAI_FAIL fallback-to-google", type(e).__name__, e)
    return translate_google(text)


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
            body = translate(raw)
        body = (body or "").strip()
        if not body:
            continue
        try:
            tg_api(
                "sendMessage",
                {
                    "chat_id": CHAT,
                    "text": body[:4000],
                    "disable_web_page_preview": True,
                },
            )
            with open(PUBLISHED, "a", encoding="utf-8") as f:
                f.write(json.dumps({"id": m["id"], "publishedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}) + "\n")
            published.add(m["id"])
            sent += 1
            time.sleep(3)  # 频道限流保护
        except Exception as e:
            failed.append({"id": m["id"], "error": f"{type(e).__name__}: {e}"})
            print("FAIL", m["id"], type(e).__name__, e)
            if len(failed) >= 3:
                break

    print(json.dumps({"ok": not failed, "new": len(pending), "sent": sent, "failed": failed}, ensure_ascii=False))


if __name__ == "__main__":
    main()
