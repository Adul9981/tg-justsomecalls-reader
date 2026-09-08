# tg-justsomecalls-reader

云端读取 `t.me/justsomecalls`（ALL CALLS，公开频道）的常驻任务（GitHub Actions）。

## 状态

- ✅ 已验证：GitHub Actions 云服务器可访问 t.me，频道公开网页预览开放。
- ✅ 常驻同步：每 15 分钟抓取一次，去重后写入 `data/`。
- ✅ 机器人验证：`Hermes07100710bot` 是 @allcallsad 管理员，可发消息。
- ✅ 翻译引擎：DeepSeek（`deepseek-chat`），key 存 GitHub Secret。
- ✅ 发布：仓库变量 `PUBLISH_ENABLED=true` 后自动翻译发布到 @allcallsad。

## 数据

- `data/latest.json`：最近一次抓取（最多 200 条）。
- `data/history.ndjson`：增量存档，每行一条 `{id, date, text}`。

## 本地用法

- `python3 tools/reader.py --probe`：摘要。
- `python3 tools/reader.py --json`：最新一页消息。
- `python3 tools/reader.py --before <id>`：向更早分页（做历史回填时用）。
