# tg-justsomecalls-reader

云端读取 `t.me/justsomecalls` 公开预览的常驻任务（GitHub Actions）。

## 已确认

- 频道为公开频道 @justsomecalls（ALL CALLS）。

## 用法

- `python3 tools/reader.py --probe`：摘要，验证网页预览是否开放。
- `python3 tools/reader.py --json`：输出最新一页消息。
- `python3 tools/reader.py --before <id>`：分页向历史方向抓取。

后续阶段：加翻译 + 发布到中文频道（新频道 + Bot），再接入本仓库 Actions。
