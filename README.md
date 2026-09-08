# tg-justsomecalls-reader

云端读取 `t.me/justsomecalls`（ALL CALLS，公开频道）的常驻任务（GitHub Actions）。

## 状态

- ✅ 已验证：GitHub Actions 云服务器可访问 t.me，频道公开网页预览开放。
- ✅ 常驻同步：每 30 分钟抓取一次，去重后写入 `data/`。
- ⏳ 下一步：翻译成中文 + 发布到用户新建的中文频道。

## 数据

- `data/latest.json`：最近一次抓取（最多 200 条）。
- `data/history.ndjson`：增量存档，每行一条 `{id, date, text}`。

## 本地用法

- `python3 tools/reader.py --probe`：摘要。
- `python3 tools/reader.py --json`：最新一页消息。
- `python3 tools/reader.py --before <id>`：向更早分页（做历史回填时用）。
