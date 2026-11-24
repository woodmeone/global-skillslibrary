"""收藏夹增量检测 + 自动处理链路。

核心设计：
  1. 状态文件记录「已处理过的 bvid/aweme_id」，重复运行不会重复下载
  2. 每轮抓最新 N 条，与状态对比，只处理新增
  3. 新增条目按材料类型分流：
       有中文字幕 → yt-dlp 直接下字幕（2 秒，最准）
       无字幕     → asr-subtitle 转录（必剪 bcut）
       转录失败   → dsh-video-storyboard 抽帧（视频 >600s 跳过，太慢）
       纯配乐     → no_speech，不算失败
  4. 结果暂存到 .favorites-out/longterm-staging/，由 route_to_agents.py 分流

不再依赖 bili-humanism 插件。cookie 走 CookieCloud。

用法：
    python pipeline.py check                # 只看有哪些新增，不处理
    python pipeline.py run --limit 5        # 处理最多 5 条新增
    python pipeline.py status               # 看状态
    python pipeline.py retry [key...]       # 重试失败条目
    python pipeline.py stage                # 生成归档暂存
    python pipeline.py clean [--keep-mp4]   # 清 mp4，只留文本
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from paths import (  # noqa: E402
    HOME as BASE, STATE as STATE_FILE,
    BILI_FAV as FAV_BILI, DY_FAV as FAV_DOUYIN,
    MEDIA as OUT_ROOT, STAGING as STAGE_DIR,
    YTDLP, FFMPEG, FFPROBE,
    SKILL_DL, SKILL_ASR, STORYBOARD_BIN,
    BILI_COOKIES_TXT as BILI_COOKIES, CC_CONF,
)

# ⚠ 这里曾经把 YTDLP / FFMPEG / SKILL_DL / SKILL_ASR 又硬编码了一遍，
# 覆盖掉上面从 paths 导入的值 —— 等于 paths.py 的 MEDIA_DOWNLOADER_* 环境变量全部失效。
# 实测：设了 MEDIA_DOWNLOADER_FFMPEG=X:\custom\ffmpeg.exe，paths.FFMPEG 认新值，
#       pipeline.FFMPEG 还是旧的硬编码路径。换机器 / 换 ffmpeg 位置时静默用错。
# 现在一律以 paths.py 为准，本文件不再覆盖。
STORYBOARD_BIN = STORYBOARD_BIN  # 显式保留：供下面 storyboard() 用，值来自 paths


def log(m: str) -> None:
    print(f"[{datetime.now():%H:%M:%S}] {m}", flush=True)


def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {"processed": {}, "runs": []}


def save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(
        json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def load_candidates() -> list[dict]:
    """合并两平台的最新条目，统一成 {id, platform, title, url}。"""
    out: list[dict] = []
    if FAV_BILI.exists():
        for it in json.loads(FAV_BILI.read_text(encoding="utf-8")):
            if it.get("unavailable"):
                continue
            out.append({
                "key": f"bili:{it['bvid']}",
                "platform": "bilibili",
                "id": it["bvid"],
                "title": it.get("title") or "",
                "url": it["url"],
                "folder": it.get("folder"),
            })
    if FAV_DOUYIN.exists():
        for it in json.loads(FAV_DOUYIN.read_text(encoding="utf-8")):
            out.append({
                "key": f"dy:{it['aweme_id']}",
                "platform": "douyin",
                "id": it["aweme_id"],
                "title": it.get("title") or "",
                "url": it["url"],
                "folder": None,
            })
    return out


def detect_new(state: dict) -> list[dict]:
    processed = state.get("processed", {})
    return [c for c in load_candidates() if c["key"] not in processed]


# ---------- 处理动作 ----------

def _run(cmd: list[str], timeout: int = 900) -> tuple[int, str]:
    log(f"  $ {' '.join(str(c) for c in cmd)[:110]}")
    # 子进程要显式拿到引擎路径，否则 media-downloader 找不到 yt-dlp
    env = os.environ.copy()
    env["MEDIA_DOWNLOADER_YTDLP"] = str(YTDLP)
    env["MEDIA_DOWNLOADER_FFMPEG"] = str(FFMPEG)
    env["PYTHONIOENCODING"] = "utf-8"
    # ffmpeg 也要进 PATH（asr-subtitle 抽音轨要用）
    env["PATH"] = str(FFMPEG.parent) + os.pathsep + env.get("PATH", "")
    try:
        p = subprocess.run(
            [str(c) for c in cmd],
            capture_output=True, text=True, timeout=timeout,
            encoding="utf-8", errors="replace", env=env,
        )
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except subprocess.TimeoutExpired:
        return -1, "TIMEOUT"


def probe_subtitle(bvid: str) -> bool:
    """探测 B站视频有没有中文字幕轨。

    踩坑记录：原来的判断是 `"Language" in out and "zh" in out.lower()`，
    结果所有视频都判成「无字幕」。实际输出形如：

        [info] Available subtitles for BVxxx:
        Language Formats
        danmaku  xml
        ai-zh    srt
        ai-en    srt

    问题在于 "zh" 只出现在数据行（ai-zh），不在表头。所以必须直接找
    `ai-zh` / `zh-` / `zh_` 这类字幕语言标记，而不是找表头。
    """
    rc, out = _run([
        YTDLP, "--list-subs",
        "--cookies", str(BILI_COOKIES),
        f"https://www.bilibili.com/video/{bvid}",
    ], timeout=120)
    if rc != 0:
        return False
    low = out.lower()
    if "available subtitles" not in low:
        return False
    # 找真正的中文字幕语言行（ai-zh / zh-CN / zh-Hans / zh 单独一行）
    for line in out.splitlines():
        s = line.strip().lower()
        if not s or s.startswith("language") or s.startswith("["):
            continue
        lang = s.split()[0] if s.split() else ""
        if lang in ("ai-zh", "zh", "zh-cn", "zh-hans", "zh-hant", "zh-tw"):
            return True
    return False


def fetch_subtitle(video: Path, bvid: str) -> Path | None:
    """优先直接抓字幕（比 ASR 更准、免费、飞快）。

    用 yt-dlp 下载 ai-zh 字幕，转成纯文本。
    """
    outdir = video.parent
    template = str(outdir / f"{video.stem}.sub")
    rc, out = _run([
        YTDLP, "--skip-download", "--write-subs", "--write-auto-subs",
        "--sub-langs", "ai-zh,zh-CN,zh-Hans,zh",
        "--sub-format", "srt/vtt/best",
        "--convert-subs", "srt",
        "--cookies", str(BILI_COOKIES),
        "-o", template,
        f"https://www.bilibili.com/video/{bvid}",
    ], timeout=300)

    # 找产物
    cands = sorted(outdir.glob(f"{video.stem}.sub*.srt"))
    if not cands:
        log(f"  ✗ 字幕下载无产物: {out[-160:]}")
        return None

    raw = cands[0].read_text(encoding="utf-8", errors="replace")
    # SRT → 纯文本：去掉序号行、时间轴行、空行
    lines: list[str] = []
    for line in raw.splitlines():
        s = line.strip()
        if not s:
            continue
        if s.isdigit():
            continue
        if "-->" in s:
            continue
        if s.startswith("WEBVTT") or s.startswith("Kind:") or s.startswith("Language:"):
            continue
        lines.append(s)
    text = "\n".join(lines)
    if len(text) < 200:
        log(f"  ✗ 字幕内容过少（{len(text)} 字）")
        return None

    dest = video.with_suffix(".txt")
    dest.write_text(text, encoding="utf-8")
    try:
        cands[0].unlink()
    except OSError:
        pass
    return dest


BILI_COOKIES = BASE / ".favorites-out" / "bilibili-cookies.txt"
CC_CONF = BASE / ".favorites-out" / "cookiecloud.json"


def refresh_cookies_from_cloud() -> bool:
    """从 CookieCloud 拉最新 cookie。成功返回 True。

    阶段二的关键：登录态由浏览器扩展定时上传，pipeline 不再依赖
    「本地持久化 profile 还登着」。

    注意：CookieCloud 拉到的数据可能是几小时前的。如果比本地 cookies 还旧，
    就不要覆盖，避免用过期凭据把好的冲掉。
    """
    if not CC_CONF.exists():
        log("  CookieCloud 未配置，用本地 cookies")
        return False

    local_age = None
    if BILI_COOKIES.exists():
        local_age = time.time() - BILI_COOKIES.stat().st_mtime

    try:
        r = subprocess.run(
            [sys.executable, str(BASE / "cc_fetch.py"), "export", "bilibili"],
            capture_output=True, text=True, timeout=120,
            encoding="utf-8", errors="replace",
        )
        if r.returncode != 0:
            log(f"  CookieCloud 无可用数据，回退本地")
            return False

        # 比本地还旧就别用
        if local_age is not None and BILI_COOKIES.exists():
            cc_at = BILI_COOKIES.stat().st_mtime
            # export 刚写过，mtime 是现在；用大小和条目数做粗判更重要
            n = sum(1 for ln in BILI_COOKIES.read_text(
                encoding="utf-8", errors="replace").splitlines()
                if ln and not ln.startswith("#"))
            if n < 3:
                log(f"  CookieCloud 只拿到 {n} 条，可疑，回退本地")
                return False

        log("  ✓ CookieCloud 取到 bilibili cookie")
        subprocess.run(
            [sys.executable, str(BASE / "cc_fetch.py"), "export", "douyin"],
            capture_output=True, text=True, timeout=120,
            encoding="utf-8", errors="replace",
        )
        return True
    except Exception as exc:
        log(f"  CookieCloud 失败: {type(exc).__name__}，回退本地")
        return False


def download_bili(item: dict) -> Path | None:
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    before = {p.name for p in OUT_ROOT.glob("*.mp4")}
    # 用 best + 上限筛选：竖屏视频 height 是 852，用 height<=480 会筛不到任何格式。
    # 按「短边 <= 480」限，兼顾横竖屏。
    #
    # ⚠ 必须显式传 -o：media-downloader 的默认下载目录是 `<workspace>/media-downloads`，
    # 而 workspace 取自 **Path.cwd()**。谁调用它，产物就落在谁的当前目录下——
    # 2026-11-24 夜间任务从 skill 目录启动，20 条稿全下载进了 skill 自己的
    # media-downloads/ 里，还被 git 一起提交了。传 -o 把落点钉死在 OUT_ROOT。
    cmd = [
        sys.executable, SKILL_DL, item["url"], "-q", "best", "--print-path",
        "-o", str(OUT_ROOT),
    ]
    if BILI_COOKIES.exists():
        cmd.extend(["--cookies", str(BILI_COOKIES)])
    rc, out = _run(cmd)
    if rc != 0:
        log(f"  ✗ 下载失败 rc={rc}: {out[-300:]}")
        return None

    # 严格：只认本次新增的文件。不能用「目录里最新」，那会拿到别的视频。
    for line in reversed(out.strip().splitlines()):
        line = line.strip().strip('"')
        if line.lower().endswith(".mp4") and os.path.exists(line):
            p = Path(line)
            if p.name not in before:
                return p
            log(f"  ⚠ 打印路径是已有文件，忽略: {p.name}")

    after = {p.name: p for p in OUT_ROOT.glob("*.mp4")}

    # 用 bvid 兜底匹配本次下载的产物
    bv = item.get("id", "")
    hits = [p for n, p in after.items() if n not in before]
    if len(hits) == 1:
        return hits[0]
    if hits:
        hits.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        return hits[0]
    log("  ✗ 找不到本次下载产物")
    return None


def probe_duration(video: Path) -> float:
    """用 ffprobe 读时长（秒）。失败返回 0。"""
    ffprobe = FFMPEG.parent / "ffprobe.exe"
    if not ffprobe.exists():
        ffprobe = Path("ffprobe")
    rc, out = _run([
        ffprobe, "-v", "error", "-show_entries", "format=duration",
        "-of", "default=nw=1:nk=1", str(video),
    ], timeout=60)
    if rc != 0:
        return 0.0
    for line in out.splitlines():
        line = line.strip()
        try:
            return float(line)
        except ValueError:
            continue
    return 0.0


def has_video_stream(path: Path) -> bool:
    """用 ffprobe 判断是否含视频流。纯音频返回 False。"""
    ffprobe = FFMPEG.parent / "ffprobe.exe"
    if not ffprobe.exists():
        ffprobe = Path("ffprobe")
    rc, out = _run([
        ffprobe, "-v", "error",
        "-select_streams", "v",
        "-show_entries", "stream=codec_type",
        "-of", "default=nw=1:nk=1", str(path),
    ], timeout=60)
    return rc == 0 and "video" in out


def transcribe(video: Path) -> Path | None:
    """调 asr-subtitle 出 txt。必剪接口有 412 风控，退避重试。

    注意：短视频（10 秒级）译文可能只有几十字，属正常。
    原来用「> 200 字节」判有效太严，会把正常短片当失败。
    改为「存在且非空」，另外把字数记下来由调用方判断质量。
    """
    for attempt in range(3):
        rc, out = _run([sys.executable, SKILL_ASR, str(video), "-f", "txt"], timeout=1800)
        if rc == 0:
            cand = video.with_suffix(".txt")
            if cand.exists() and cand.stat().st_size > 0:
                return cand
            log("  ⚠ 转录产物为空")
            return None
        # 412 是必剪的瞬时限流，等一会儿再试
        if "412" in out:
            wait = 60 * (attempt + 1)
            log(f"  ⚠ 必剪 412，等待 {wait}s 后重试（{attempt+1}/3）")
            time.sleep(wait)
            continue
        log(f"  ✗ 转录失败 rc={rc}: {out[-200:]}")
        return None
    log("  ✗ 转录三次均失败")
    return None


def storyboard(video: Path) -> Path | None:
    """调 dsh-video-storyboard 出宫格图 + 文本索引。"""
    bin_js = STORYBOARD_BIN          # 由 paths.py 统一解析，别在函数里再写死绝对路径
    if not bin_js.exists():
        log(f"  ✗ 找不到 storyboard bin: {bin_js}")
        log("    提示：用 LEAD_LEARN_* / 本机实际安装位置覆盖，见 paths.py")
        return None
    out_png = OUT_ROOT / f"{video.stem}-storyboard.png"
    rc, out = _run(["node", str(bin_js), str(video), "--out", str(out_png)], timeout=1800)
    if rc != 0:
        log(f"  ✗ storyboard 失败 rc={rc}: {out[-200:]}")
        return None
    return out_png if out_png.exists() else None


def _norm_title(s: str) -> str:
    """归一化标题用于文件匹配。

    yt-dlp 会把 / : 等字符替换成全角符号（如 ⧸），所以直接比标题会失败。
    """
    import re

    return re.sub(r'[\\/:*?"<>|⧸｜\s]+', "", s or "")


def find_existing_video(item: dict) -> Path | None:
    """按标题找已下载的 mp4，避免重复下载。"""
    title = (item.get("title") or "").strip()
    if not title or not OUT_ROOT.exists():
        return None
    want = _norm_title(title)[:12]
    if not want:
        return None
    for p in OUT_ROOT.glob("*.mp4"):
        if want in _norm_title(p.stem):
            return p
    return None


def process_one(item: dict) -> dict:
    """处理单条：下载 → 判断走哪条路。已下载/已抽帧的会复用，不重复做。"""
    log(f"▶ {item['key']} | {item['title'][:50]}")
    result = {"key": item["key"], "title": item["title"], "platform": item["platform"]}

    if item["platform"] != "bilibili":
        # 抖音走 Playwright 拦媒体。注意：抖音没有公开字幕轨，
        # 所以下载后直接进 ASR，不存在「字幕优先」这一步。
        # 抖音合并长视频可能超过 10 分钟，给足时间
        rc, out = _run([sys.executable, BASE / "douyin_dl.py", item["id"]], timeout=1800)
        if rc != 0:
            result["download"] = f"fail({rc})"
            if rc == -1:
                log("  ✗ 下载超时（1800s），标记待重试")
            return result

        # 抖音会产出多个文件：合并后的 mp4（音视频全）、纯音频 m4a。
        # 优先选 mp4，因为它信息更全（storyboard 需要画面）。
        cand_mp4 = list(OUT_ROOT.glob(f"{item['id']}*.mp4"))
        cand_m4a = list(OUT_ROOT.glob(f"{item['id']}*.m4a"))
        files = sorted(
            cand_mp4 + cand_m4a,
            key=lambda p: (p.suffix.lower() != ".mp4", -p.stat().st_mtime),
        )
        if not files:
            result["download"] = "fail"
            log("  ✗ 找不到下载产物")
            return result

        video = files[0]
        result["download"] = "ok"
        result["file"] = str(video)
        log(f"  ✓ 下载 {video.name} ({video.stat().st_size/1024/1024:.1f} MB)")

        # 抖音没有字幕轨，直接进 ASR。图文笔记只有配乐时，ASR 可能拿不到词，
        # 那种情况标 no_speech，不算失败。
        txt = video.with_suffix(".txt")
        if txt.exists() and txt.stat().st_size > 200:
            result["route"] = "asr"
            result["transcript"] = str(txt)
            result["transcript_chars"] = len(
                txt.read_text(encoding="utf-8", errors="replace")
            )
            log(f"  ↻ 复用转录 {result['transcript_chars']} 字")
            return result

        got = transcribe(video)
        if got:
            result["route"] = "asr"
            result["transcript"] = str(got)
            result["transcript_chars"] = len(
                got.read_text(encoding="utf-8", errors="replace")
            )
            log(f"  ✓ 转录 {result['transcript_chars']} 字")
            return result

        # 音频且转录失败：多半是纯音乐，没有可用文字
        if video.suffix.lower() == ".m4a":
            result["route"] = "no_speech"
            result["note"] = "图文笔记的配乐，无可转录语音"
            log("  ⚠ 纯音频且无语音，标记 no_speech")
            return result

        # 转录失败：短素材才走 storyboard
        dur = probe_duration(video)
        result["duration_sec"] = dur
        if dur and dur > 600:
            result["route"] = "needs_manual"
            log(f"  ⚠ {dur:.0f}s 长视频，跳过 storyboard")
            return result
        png = storyboard(video)
        result["route"] = "storyboard" if png else "failed"
        if png:
            result["storyboard"] = str(png)
        return result

    # B站：字幕探测
    has_sub = probe_subtitle(item["id"])
    result["has_subtitle"] = has_sub
    log(f"  字幕: {'有' if has_sub else '无'}")

    # 复用已下载的产物（按标题前缀匹配，避免重复下载上百 MB）
    existing = find_existing_video(item)
    if existing:
        video = existing
        result["download"] = "reused"
        log(f"  ↻ 复用已有 {video.name} ({video.stat().st_size/1024/1024:.1f} MB)")
    else:
        video = download_bili(item)
        if not video:
            result["download"] = "fail"
            return result
        result["download"] = "ok"
        log(f"  ✓ 下载 {video.name} ({video.stat().st_size/1024/1024:.1f} MB)")
    result["file"] = str(video)

    # 优先：直接抓字幕（比 ASR 准、免费、快）
    if has_sub:
        log("  尝试直接取字幕...")
        sub = fetch_subtitle(video, item["id"])
        if sub:
            result["route"] = "subtitle"
            result["transcript"] = str(sub)
            result["transcript_chars"] = len(
                sub.read_text(encoding="utf-8", errors="replace")
            )
            log(f"  ✓ 字幕 {result['transcript_chars']} 字")
            return result
        log("  ⚠ 字幕取不到，回退转录")

    # 复用已有转录
    existing_txt = video.with_suffix(".txt")
    if existing_txt.exists() and existing_txt.stat().st_size > 200:
        result["route"] = "asr"
        result["transcript"] = str(existing_txt)
        result["transcript_chars"] = len(
            existing_txt.read_text(encoding="utf-8", errors="replace")
        )
        log(f"  ↻ 复用转录 {result['transcript_chars']} 字")
        return result

    txt = transcribe(video)
    if txt:
        result["route"] = "asr"
        result["transcript"] = str(txt)
        result["transcript_chars"] = len(txt.read_text(encoding="utf-8", errors="replace"))
        log(f"  ✓ 转录 {result['transcript_chars']} 字")
        return result

    # 复用已有 storyboard
    existing_png = OUT_ROOT / f"{video.stem}-storyboard-1.png"
    if existing_png.exists():
        result["route"] = "storyboard"
        result["storyboard"] = str(existing_png)
        log("  ↻ 复用已有 storyboard")
        return result

    # 转录确实失败才走 storyboard。长视频极慢（实测 39 分钟用了 17 分钟），设阈值。
    dur = probe_duration(video)
    result["duration_sec"] = dur
    if dur and dur > 600:
        result["route"] = "needs_manual"
        result["note"] = f"转录失败且视频 {dur:.0f}s 过长；storyboard 预计 >15 分钟，留待人工决定"
        log(f"  ⚠ {dur:.0f}s 长视频，跳过 storyboard")
        return result

    # 纯音频容器没有视频流，storyboard 无从抽帧
    if not has_video_stream(video):
        result["route"] = "no_speech"
        result["note"] = "无视频流且无可转录语音"
        log("  ⚠ 无视频流，标记 no_speech")
        return result

    png = storyboard(video)
    result["route"] = "storyboard" if png else "failed"
    if png:
        result["storyboard"] = str(png)
        log(f"  ✓ storyboard {png.name}")
    return result


def cmd_check() -> int:
    state = load_state()
    new = detect_new(state)
    print(f"已处理: {len(state.get('processed', {}))} 条")
    print(f"当前候选: {len(load_candidates())} 条")
    print(f"新增: {len(new)} 条\n")
    for it in new:
        print(f"  [{it['platform']:8}] {it['id']} | {(it.get('title') or '')[:56]}")
    return 0


def cmd_run(limit: int) -> int:
    # 先刷新 cookie（阶段二：走 CookieCloud）
    refresh_cookies_from_cloud()

    state = load_state()
    new = detect_new(state)
    if not new:
        log("没有新增，跳过")
        return 0
    log(f"发现 {len(new)} 条新增，本轮处理 {min(limit, len(new))} 条")

    done = 0
    for it in new[:limit]:
        try:
            r = process_one(it)
        except Exception as exc:
            r = {"key": it["key"], "error": f"{type(exc).__name__}: {exc}"}
            log(f"  ✗ 异常: {r['error']}")
        state.setdefault("processed", {})[it["key"]] = {
            "at": datetime.now().isoformat(timespec="seconds"),
            **r,
        }
        save_state(state)
        done += 1

    state.setdefault("runs", []).append({
        "at": datetime.now().isoformat(timespec="seconds"),
        "processed": done,
    })
    save_state(state)
    log(f"本轮完成 {done} 条")
    return 0


def cmd_retry(keys: list[str] | None) -> int:
    """把指定条目（或所有非成功的）从状态里移除，下次 run 会重新处理。"""
    state = load_state()
    proc = state.get("processed", {})
    targets = []
    if keys:
        targets = [k for k in keys if k in proc]
        missing = [k for k in keys if k not in proc]
        if missing:
            log(f"状态里没有这些 key: {missing}")
    else:
        for k, v in proc.items():
            ok = v.get("route") in ("subtitle", "asr", "storyboard")
            if not ok:
                targets.append(k)
    if not targets:
        log("没有需要重试的条目")
        return 0
    for k in targets:
        proc.pop(k, None)
        log(f"  移除 {k}")
    save_state(state)
    log(f"已移除 {len(targets)} 条，下次 run 会重新处理")
    return 0


def cmd_export_longterm(agent: str = "kaibian") -> int:
    """把已转录成功的稿件整理成 longterm 可归档的 markdown。

    不直接写进 longterm，先产出到 .favorites-out/longterm-staging/，
    由 agent 判断该进哪个类目。
    """
    state = load_state()
    proc = state.get("processed", {})
    stage = BASE / ".favorites-out" / "longterm-staging"
    stage.mkdir(parents=True, exist_ok=True)

    made = 0
    for key, v in proc.items():
        # 字幕和 ASR 都是有效文本产物，都要归档
        if v.get("route") not in ("asr", "subtitle"):
            continue
        tp = v.get("transcript")
        if not tp or not Path(tp).exists():
            continue
        src = Path(tp)
        text = src.read_text(encoding="utf-8", errors="replace")
        # 短文本也有价值（一条短视频的金句可能就是 40 字），
        # 但要标出来让审阅者知道这是短素材。
        if len(text) < 20:
            continue
        brief = len(text) < 300

        # 文件名过滤：换行、斜杠、引号都要清掉，否则写盘报 Errno 22
        safe = re.sub(r'[\\/:*?"<>|\r\n\t]+', "_", v.get("title") or key).strip()
        safe = re.sub(r"\s+", " ", safe)[:48].strip("._ ")
        if not safe:
            safe = key.replace(":", "-")
        dest = stage / f"{safe}.staged.md"
        if dest.exists():
            continue
        dest.write_text(
            "\n".join([
                "---",
                f"source: {v.get('file', '')}",
                f"title: {v.get('title', '')}",
                f"platform: {v.get('platform', '')}",
                f"key: {key}",
                f"chars: {len(text)}",
                f"processed_at: {v.get('at', '')}",
                f"status: {'staged_brief_needs_review' if brief else 'staged_needs_review'}",
                f"brief: {'true' if brief else 'false'}",
                "---",
                "",
                "## 转录全文",
                "",
                text,
            ]),
            encoding="utf-8",
        )
        made += 1
        log(f"  staged: {dest.name} ({len(text)} 字)")

    log(f"共 {made} 篇待审 → {stage}")
    return 0


def cmd_clean(keep_mp4: bool = False, orphans: bool = True) -> int:
    """清理已完成条目的媒体文件，只留可再读的产物。

    两段，判据不同：

    **A. 有文本的（route in subtitle/asr）** —— 文本已落盘，媒体是纯中间产物，删。
       判据：`transcript` 文件存在。一条合集能占 1.4 GB。

    **B. 孤儿媒体（route in storyboard/no_speech/fail 等）** —— 早期版本完全不管，
       于是盘上永久留着 40 MB 拉不掉的 mp4/m4a。判据一律是「删了之后还有没有别的东西」：
         - 有 storyboard png（同名 `-storyboard*.png`）→ 画面已固化，删
         - no_speech（ASR 确认无人声）→ 没有可学内容，删
         - 下载失败 → 没产出，删
         - **storyboard 但没有 png → 留**。抽帧失败了，素材可能真有内容，
           删掉它这份唯一副本就没了（抖音链接还会失效）。归 `retry` 管，不归 clean。

    ⚠ dry-run 必须 continue，不许落到删除分支——pitfall #24 就是真删过文件。
    """
    state = load_state()
    proc = state.get("processed", {})
    freed = 0
    removed = 0
    planned = 0

    def _has_storyboard(media: Path) -> bool:
        """这条素材有没有留在盘上的宫格抽帧。"""
        stem = media.stem
        return any(OUT_ROOT.glob(f"{stem}-storyboard*.png"))

    def _try_remove(p: Path, v: dict, why: str) -> None:
        nonlocal freed, removed, planned
        try:
            size = p.stat().st_size
        except OSError:
            return
        if keep_mp4:
            planned += 1
            freed += size
            log(f"  · [{why}] {p.name} ({size/1024/1024:.0f} MB)")
            return
        try:
            p.unlink()
            freed += size
            removed += 1
            v["media_removed"] = why
            log(f"  − [{why}] {p.name} ({size/1024/1024:.0f} MB)")
        except OSError as exc:
            log(f"  ✗ {p.name}: {exc}")

    for key, v in proc.items():
        fp = v.get("file")
        if not fp:
            continue
        p = Path(fp)
        if not p.exists() or p.suffix.lower() not in (".mp4", ".m4a"):
            continue
        route = v.get("route")

        # A. 有文本 → 媒体是中间产物
        if route in ("subtitle", "asr"):
            tp = v.get("transcript")
            if tp and Path(tp).exists():
                _try_remove(p, v, "有文本")
            continue

        # B. 孤儿媒体（无文本产物）。判据两极，不许含糊：
        if not orphans:
            continue
        if _has_storyboard(p):
            # 画面已固化成 png，媒体是纯中间产物
            _try_remove(p, v, f"{route}·有抽帧")
        elif (v.get("download") or "").startswith("fail"):
            # 下载失败，本来就没产出（多半也没文件）
            _try_remove(p, v, "fail·无产出")
        elif route == "no_speech":
            # 已确认无人声 → 这段素材没有可学的东西，留着只是占盘
            _try_remove(p, v, "no_speech·确定无内容")
        # route == storyboard 但没有 png —— **必须留**：
        # 抽帧失败了，这条素材可能真有内容（只是没处理成），
        # 删了它就是唯一副本消失，将来想重做得重新下载（抖音链接还会失效）。
        # 交给 `pipeline.py retry` 重试，不是交给 clean 删。

    if removed:
        save_state(state)
    verb = "[dry-run] 将删除" if keep_mp4 else "删除"
    n = planned if keep_mp4 else removed
    log(f"{verb} {n} 个媒体文件，释放 {freed/1024/1024:.0f} MB")
    return 0


def cmd_status() -> int:
    state = load_state()
    proc = state.get("processed", {})
    print(f"已处理总数: {len(proc)}")
    routes: dict[str, int] = {}
    for v in proc.values():
        r = v.get("route") or v.get("download") or "unknown"
        routes[r] = routes.get(r, 0) + 1
    for k, v in sorted(routes.items(), key=lambda x: -x[1]):
        print(f"  {k}: {v}")
    runs = state.get("runs", [])
    if runs:
        print(f"\n最近运行: {runs[-1]['at']} (处理 {runs[-1]['processed']} 条)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check")
    r = sub.add_parser("run")
    r.add_argument("--limit", type=int, default=5)
    sub.add_parser("status")
    rt = sub.add_parser("retry")
    rt.add_argument("keys", nargs="*", help="要重试的 key；留空则重试所有非成功条目")
    sub.add_parser("stage")
    cl = sub.add_parser("clean")
    cl.add_argument("--keep-mp4", action="store_true", help="只报告不删除（真 dry-run）")
    cl.add_argument("--no-orphans", action="store_true",
                    help="只清有文本的条目，不碰 storyboard/no_speech 的孤儿媒体")
    a = ap.parse_args()

    if a.cmd == "check":
        return cmd_check()
    if a.cmd == "run":
        return cmd_run(a.limit)
    if a.cmd == "status":
        return cmd_status()
    if a.cmd == "retry":
        return cmd_retry(a.keys or None)
    if a.cmd == "stage":
        return cmd_export_longterm()
    if a.cmd == "clean":
        return cmd_clean(a.keep_mp4, orphans=not a.no_orphans)
    return 64


if __name__ == "__main__":
    sys.exit(main())
