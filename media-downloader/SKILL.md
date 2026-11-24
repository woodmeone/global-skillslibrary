---
name: "media-downloader"
description: "给一个视频链接就能把视频下载到工作区 media-downloads/。基于 media-downloader 项目的默认引擎 yt-dlp，支持 B站/YouTube 等上千站点、质量档位、仅音频、播放列表、浏览器 cookies 解锁高清。当用户说「下载这个视频/这个链接帮我下下来/扒个视频/下载B站视频」时调用。"
---

# 视频下载（media-downloader）

把任意视频链接落到工作区的一个固定位置。**一句话：给链接 → 文件出现在 `media-downloads/`。**

## 第一性原理：为什么不直接驱动 media-downloader 的 GUI

[mhogomchungu/media-downloader](https://github.com/mhogomchungu/media-downloader) 是一个 **Qt/C++ 图形界面外壳**，它自己不下载，而是把活转交给 `yt-dlp`、`aria2c`、`wget` 等 CLI 引擎，默认引擎就是 **yt-dlp**。

agent 无法可靠地点击 GUI，但可以直接调用 GUI 背后的引擎——效果完全一致，且可脚本化、可测试。因此本 skill 封装的是 yt-dlp，并复用 media-downloader 便携版自带的引擎与 ffmpeg。

## 已部署的资产（workspace 内）

| 资产 | 路径 | 作用 |
|---|---|---|
| yt-dlp 独立二进制 | `tools/bin/yt-dlp.exe` | 下载引擎（首选） |
| media-downloader 便携版 | `tools/media-downloader/MediaDownloaderQt6-5.6.6/` | GUI + 备用引擎 |
| ├ 备用 yt-dlp | `…/3rdParty/ytdlp/yt-dlp.exe` | 引擎兜底 |
| └ 内置 ffmpeg | `…/3rdParty/ffmpeg/bin/ffmpeg.exe` | DASH 音视频合并 |

引擎查找顺序：环境变量 `MEDIA_DOWNLOADER_YTDLP` → 上表路径 → PATH 上的 `yt-dlp`。

## 怎么用

一切通过 `scripts/download.py`。先定位本 skill 目录（记为 `$SKILL`）：

```bash
python "$SKILL/scripts/download.py" "<链接>"
```

常用形态：

```bash
# 1) 默认：最佳质量，落到 ./media-downloads/
python "$SKILL/scripts/download.py" "https://www.bilibili.com/video/BV1moCdYWEjQ"

# 2) 只要音频（转 mp3）——做字幕/剪辑素材时最省时间
python "$SKILL/scripts/download.py" "<链接>" -q audio

# 3) 限高 720P（未登录 B站 的上限，速度快）
python "$SKILL/scripts/download.py" "<链接>" -q 720

# 4) 解锁 1080P/更高：借用浏览器已登录的 cookies
python "$SKILL/scripts/download.py" "<链接>" -q 1080 --cookies-from-browser chrome

# 5) 指定目录 + 打印最终文件路径（agent 需要拿到路径时必加）
python "$SKILL/scripts/download.py" "<链接>" -o "media-downloads/bili" --print-path
```

`--print-path` 会让 yt-dlp 在结束时输出最终文件绝对路径，便于你直接把路径交给后续 skill（如 asr-subtitle）。

## 质量档位

| `-q` | 含义 |
|---|---|
| `best`（默认） | 可用最高质量 |
| `1080` / `720` / `480` | 限高，越小越快 |
| `audio` | 仅音频轨，自动转 mp3 |

## 执行守则（给 agent 的判断规则）

1. **先探测再下载。** 大文件耗时耗流量。不确定链接是否可下时，先跑 `yt-dlp -F "<链接>"` 看格式表，再决定档位。
2. **默认不下播放列表。** 脚本已强制 `--no-playlist`；用户明确要整列表时才加 `--playlist`。
3. **B站高清要登录。** 未登录最高 720P/1080P 视站点策略而定。报 `become a premium member` / `missing` 时，提示用户加 `--cookies-from-browser chrome`（需其浏览器已登录 B站），**不要**擅自替用户读取 cookies 而不告知。
4. **失败先看退出码与末行。** 常见三类：网络重置（重试）、需登录（走 cookies）、站点改版（升级 yt-dlp：`tools/bin/yt-dlp.exe -U`）。
5. **产物归位。** 一律落在工作区内，默认 `media-downloads/`；不要写到工作区外。
6. **合规边界。** 仅下载用户有权获取的内容，不绕过付费墙、不批量爬取他人作品。

## 依赖与故障排查

- 需要 Python 3.10+（脚本本身）、ffmpeg（合并分离流，已随便携版提供）。
- `未找到 yt-dlp 引擎` → 按上表确认 `tools/bin/yt-dlp.exe` 存在，或 `pip install yt-dlp`。
- 下载极慢/中断 → 用 `--ytdlp-args --limit-rate 5M` 把任意 yt-dlp 原生参数透传进去。
- 想以库形式复用：`import download; download.build_args(...)` 是纯函数，便于测试与二次编排。

## 测试

```bash
python -m pytest "$SKILL/tests" -q
```

覆盖：引擎查找优先级、输出目录解析、参数构造（含"默认禁播放列表"的逆向断言）、未知档位报错、退出码透传。全部离线，不触网。
