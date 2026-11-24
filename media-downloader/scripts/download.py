#!/usr/bin/env python3
"""media-downloader skill 核心脚本：给链接 → 下载视频到工作区。

第一性原理：media-downloader 项目本质是 yt-dlp 等 CLI 引擎的 GUI 壳，
agent 无法无头驱动 GUI，故 skill 直接封装其默认引擎 yt-dlp。

纯函数（find_engine / build_args / resolve_output_dir）与执行分离，便于离线测试。
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

# 质量档位 → yt-dlp format 选择器
QUALITY_FORMATS = {
    "best": "bv*+ba/b",
    "1080": "bv*[height<=1080]+ba/b[height<=1080]",
    "720": "bv*[height<=720]+ba/b[height<=720]",
    "480": "bv*[height<=480]+ba/b[height<=480]",
    "audio": "ba",
}

# 工作区默认下载目录名（相对当前工作目录）
DEFAULT_OUTPUT_DIRNAME = "media-downloads"

# 引擎候选路径（相对 workspace 根），按优先级排列
_ENGINE_REL_PATHS = [
    Path("tools") / "bin" / "yt-dlp.exe",
    Path("tools") / "media-downloader" / "MediaDownloaderQt6-5.6.6" / "3rdParty" / "ytdlp" / "yt-dlp.exe",
    Path("tools") / "media-downloader" / "MediaDownloaderQt6-5.6.6" / "3rdParty" / "ytdlp" / "yt-dlp_x86.exe",
]


def find_engine(workspace: str | Path | None = None) -> str:
    """定位 yt-dlp 引擎。

    优先级：环境变量 MEDIA_DOWNLOADER_YTDLP > workspace 内置便携版 > PATH 上的 yt-dlp。
    找不到时抛 FileNotFoundError，错误信息带部署指引。
    """
    env = os.environ.get("MEDIA_DOWNLOADER_YTDLP")
    if env:
        p = Path(env)
        if p.exists():
            return str(p)
        raise FileNotFoundError(f"MEDIA_DOWNLOADER_YTDLP 指向不存在的文件: {env}")

    ws = Path(workspace) if workspace else Path.cwd()
    for rel in _ENGINE_REL_PATHS:
        cand = ws / rel
        if cand.exists():
            return str(cand)

    on_path = shutil.which("yt-dlp")
    if on_path:
        return on_path

    raise FileNotFoundError(
        "未找到 yt-dlp 引擎。请确认已部署 media-downloader 便携版到 tools/，"
        "或 pip install yt-dlp，或设置环境变量 MEDIA_DOWNLOADER_YTDLP 指向 yt-dlp 可执行文件。"
    )


def resolve_output_dir(output: str | Path | None, workspace: str | Path | None = None) -> Path:
    """解析下载目录：显式 --output 优先，否则 <workspace>/media-downloads/。"""
    if output:
        return Path(output)
    ws = Path(workspace) if workspace else Path.cwd()
    return ws / DEFAULT_OUTPUT_DIRNAME


def find_ffmpeg(workspace: str | Path | None = None) -> str | None:
    """定位 ffmpeg（B站等 DASH 分离流需要合并）。找不到返回 None，交给 yt-dlp 自行探测。"""
    env = os.environ.get("MEDIA_DOWNLOADER_FFMPEG")
    if env and Path(env).exists():
        return env
    ws = Path(workspace) if workspace else Path.cwd()
    bundled = (
        ws
        / "tools"
        / "media-downloader"
        / "MediaDownloaderQt6-5.6.6"
        / "3rdParty"
        / "ffmpeg"
        / "bin"
        / "ffmpeg.exe"
    )
    if bundled.exists():
        return str(bundled)
    return shutil.which("ffmpeg")


def build_args(
    url: str,
    quality: str = "best",
    output_dir: str | Path = ".",
    playlist: bool = False,
    cookies_from_browser: str | None = None,
    cookies_file: str | None = None,
    filename_template: str = "%(title)s.%(ext)s",
    extra_args: list[str] | None = None,
) -> list[str]:
    """构造 yt-dlp 命令行参数（纯函数，可离线断言）。"""
    if quality not in QUALITY_FORMATS:
        raise ValueError(f"未知质量档位: {quality}，可选 {sorted(QUALITY_FORMATS)}")
    args = [
        "-f",
        QUALITY_FORMATS[quality],
        "--no-warnings",
        "-o",
        str(Path(output_dir) / filename_template),
    ]
    if quality == "audio":
        args += ["--extract-audio", "--audio-format", "mp3"]
    if not playlist:
        args.append("--no-playlist")
    if cookies_from_browser:
        args += ["--cookies-from-browser", cookies_from_browser]
    if cookies_file:
        args += ["--cookies", cookies_file]
    if extra_args:
        args += list(extra_args)
    args.append(url)
    return args


def run_download(engine: str, args: list[str]) -> int:
    """执行下载，透传输出。返回退出码。"""
    proc = subprocess.run([engine, *args], text=True, encoding="utf-8", errors="replace")
    return proc.returncode


def snapshot_files(out_dir: Path) -> dict[Path, float]:
    """记录输出目录现有文件及其修改时间，用于事后 diff 出新产物。"""
    return {p: p.stat().st_mtime for p in out_dir.rglob("*") if p.is_file()}


def new_files(before: dict[Path, float], out_dir: Path) -> list[Path]:
    """返回下载后新增/被写入的文件（排除 .part/.ytdl 临时文件）。"""
    fresh = []
    for p in out_dir.rglob("*"):
        if not p.is_file():
            continue
        if p.suffix.lower() in (".part", ".ytdl", ".temp"):
            continue
        if p not in before or p.stat().st_mtime > before.get(p, 0):
            fresh.append(p)
    return fresh


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="按链接下载视频到工作区 media-downloads/")
    parser.add_argument("url", help="视频链接（支持 yt-dlp 覆盖的站点）")
    parser.add_argument(
        "-q", "--quality", default="best", choices=sorted(QUALITY_FORMATS),
        help="质量档位：best/1080/720/480/audio（默认 best；audio 仅音频并转 mp3）",
    )
    parser.add_argument("-o", "--output", default=None, help=f"下载目录（默认 ./{DEFAULT_OUTPUT_DIRNAME}）")
    parser.add_argument("--playlist", action="store_true", help="允许下载整个播放列表（默认关闭）")
    parser.add_argument("--cookies-from-browser", default=None,
                        help="从浏览器取 cookies 以解锁高清晰度，如 chrome/edge/firefox")
    parser.add_argument("--cookies", default=None, help="cookies.txt 文件路径")
    parser.add_argument("--template", default="%(title)s.%(ext)s", help="输出文件名模板")
    parser.add_argument("--print-path", action="store_true",
                        help="下载完成后打印最终文件路径（供 agent 解析）")
    parser.add_argument("--ytdlp-args", nargs=argparse.REMAINDER, default=[],
                        help="透传给 yt-dlp 的额外参数，如 --ytdlp-args --limit-rate 5M")
    ns = parser.parse_args(argv)

    try:
        engine = find_engine()
    except FileNotFoundError as e:
        print(f"[media-downloader] 错误：{e}", file=sys.stderr)
        return 2

    out_dir = resolve_output_dir(ns.output)
    out_dir.mkdir(parents=True, exist_ok=True)

    args = build_args(
        ns.url,
        quality=ns.quality,
        output_dir=out_dir,
        playlist=ns.playlist,
        cookies_from_browser=ns.cookies_from_browser,
        cookies_file=ns.cookies,
        filename_template=ns.template,
        extra_args=ns.ytdlp_args,
    )
    ffmpeg = find_ffmpeg()
    if ffmpeg:
        args = ["--ffmpeg-location", str(Path(ffmpeg).parent), *args]

    print(f"[media-downloader] 引擎: {engine}")
    print(f"[media-downloader] 输出目录: {out_dir}")

    before = snapshot_files(out_dir) if ns.print_path else {}
    rc = run_download(engine, args)
    if rc == 0:
        print(f"[media-downloader] 下载完成 → {out_dir}")
        if ns.print_path:
            time.sleep(0.1)  # 让 mtime 稳定
            for f in new_files(before, out_dir):
                print(str(f.resolve()))
    else:
        print(f"[media-downloader] 下载失败（退出码 {rc}）。B站 1080P 需登录：加 --cookies-from-browser chrome 重试。",
              file=sys.stderr)
    return rc


if __name__ == "__main__":
    sys.exit(main())
