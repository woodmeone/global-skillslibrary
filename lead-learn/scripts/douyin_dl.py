"""抖音视频下载 —— 走 Playwright 拦媒体请求。

为什么不走 yt-dlp：
  yt-dlp 的 Douyin extractor 需要 msToken 等运行时 token，403 无法绕过。
  但我们有登录态的浏览器，直接拦它自己发出的媒体请求即可。

产物落到 media-downloads/，与 media-downloader skill 一致。
"""

from __future__ import annotations

import asyncio
import os
import re
import sys
from pathlib import Path

from playwright.async_api import async_playwright

from paths import CHROMIUM  # noqa: E402
PROFILE = Path(
    os.path.expandvars(r"%LOCALAPPDATA%\dsh-bili-humanism\browser-profiles\douyin")
)
from paths import MEDIA as OUT_DIR  # noqa: E402


def safe_name(s: str, limit: int = 60) -> str:
    s = re.sub(r'[\\/:*?"<>|\r\n\t#]+', "_", s or "")
    s = re.sub(r"\s+", " ", s).strip()
    return (s[:limit] or "douyin").strip("._ ")


def merge_av(video_path: Path, audio_path: Path, dest: Path) -> bool:
    """用 ffmpeg 合并音视频轨。失败返回 False。"""
    import shutil
    import subprocess

    ffmpeg = os.environ.get("MEDIA_DOWNLOADER_FFMPEG") or shutil.which("ffmpeg")
    if not ffmpeg:
        # 兜底：paths.py 解析出的 FFMPEG（它自己能读环境变量与默认位置）。
        # 不要在这里写死绝对路径——skill 会装到别人机器上。
        try:
            from paths import FFMPEG as _FF
            if _FF.exists():
                ffmpeg = str(_FF)
        except Exception:
            pass
    if not ffmpeg:
        print("    ✗ 找不到 ffmpeg（设 MEDIA_DOWNLOADER_FFMPEG 或把它放进 PATH）")
        return False

    cmd = [
        ffmpeg, "-y", "-loglevel", "error",
        "-i", str(video_path), "-i", str(audio_path),
        "-c", "copy", "-shortest", str(dest),
    ]
    p = subprocess.run(cmd, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if p.returncode != 0 or not dest.exists():
        print(f"    ✗ ffmpeg 合并失败: {(p.stderr or '')[-200:]}")
        return False
    return True


async def download_one(aweme_id: str) -> Path | None:
    url = f"https://www.douyin.com/video/{aweme_id}"
    media_urls: list[str] = []
    title_holder = {"t": ""}

    async with async_playwright() as pw:
        ctx = await pw.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE),
            executable_path=CHROMIUM,
            headless=True,
            viewport={"width": 1440, "height": 900},
            locale="zh-CN",
            args=["--disable-blink-features=AutomationControlled", "--mute-audio"],
        )
        page = await ctx.new_page()

        def on_response(resp):
            u = resp.url
            # douyinvod 是视频流；douyinstatic 是图文笔记里的视频/图集素材
            if any(k in u for k in ("douyinvod.com", "douyinstatic.com",
                                    "aweme/v1/play", ".mp4")):
                if u not in media_urls:
                    media_urls.append(u)

        page.on("response", on_response)

        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=45000)
            await page.wait_for_timeout(6000)
            title_holder["t"] = await page.title()

            # 抖音视频不一定自动加载媒体流，要多路触发。
            # 踩坑：只按 Space 时有的页面拦不到任何请求（实测 0 个候选地址）。
            triggers = [
                lambda: page.keyboard.press("Space"),
                lambda: page.mouse.click(720, 450),          # 点播放器中心
                lambda: page.click("video", timeout=3000),   # 点 video 元素
                lambda: page.mouse.wheel(0, 400),            # 轻微滚动触发懒加载
                lambda: page.keyboard.press("Space"),
            ]
            for trig in triggers:
                if media_urls:
                    break
                try:
                    await trig()
                except Exception:
                    pass
                await page.wait_for_timeout(2500)

            # 最后再等一会儿，给媒体请求发出去的时间
            for _ in range(6):
                if media_urls:
                    break
                await page.wait_for_timeout(1500)
        except Exception as exc:
            print(f"  页面异常: {type(exc).__name__}: {exc}")

        print(f"  拦截到 {len(media_urls)} 个候选媒体地址")

        # 抖音长视频是 blob: 包装的 DASH 流，<video>.src 只是 blob:，
        # 真实地址必须从 performance 资源里读。
        # 关键：media-video-xxx 和 media-audio-xxx 是两个独立 URL。
        try:
            perf = await page.evaluate(
                """() => {
                    const vids = [], auds = [];
                    performance.getEntriesByType('resource').forEach(e => {
                        const u = e.name;
                        if (u.includes('media-video-')) vids.push(u);
                        else if (u.includes('media-audio-')) auds.push(u);
                        else if (u.includes('douyinvod') && /mime_type=video/.test(u)) {
                            vids.push(u);
                        }
                    });
                    const uniq = a => Array.from(new Set(a));
                    return { video: uniq(vids), audio: uniq(auds) };
                }"""
            )
            if perf.get("video"):
                media_urls = perf["video"] + perf["audio"] + media_urls
                print(f"  ↻ performance 取到 {len(perf['video'])} 视频轨 "
                      f"+ {len(perf['audio'])} 音频轨（优先）")
        except Exception as exc:
            print(f"  读 performance 失败: {exc}")

        # 按可信度排序：真视频流 > 静态资源 CDN > 其他
        def rank(u: str) -> int:
            if "media-video-" in u or "media-audio-" in u:
                return 0
            if "douyinvod.com" in u:
                return 1
            if "aweme/v1/play" in u:
                return 2
            if "tos-cn" in u or "/obj/tos" in u:
                return 3
            low = u.lower()
            if any(k in low for k in (".js", ".css", ".png", ".jpg", ".svg", ".woff")):
                return 99
            if "douyinstatic.com" in u:
                return 6
            return 9

        media_urls = [u for u in media_urls if rank(u) < 99]
        media_urls.sort(key=rank)
        # 去重后保留前 8
        seen_u: set[str] = set()
        uniq: list[str] = []
        for u in media_urls:
            if u not in seen_u:
                seen_u.add(u)
                uniq.append(u)
        media_urls = uniq[:8]
        print(f"  筛后 {len(media_urls)} 个候选")

        # 图集类笔记（纯图片）不是视频，明确报出来
        if not media_urls:
            try:
                imgs = await page.evaluate(
                    "document.querySelectorAll('img[src*=\"aweme\"]').length"
                )
                if imgs:
                    print(f"  ⚠ 疑似图文笔记（{imgs} 张图，无视频流）")
            except Exception:
                pass
            await ctx.close()
            return None

        # 用页面上下文带 cookie 逐个尝试候选地址。
        # 关键发现：抖音是 DASH 分离流 —— 视频轨和音频轨是两个独立 URL。
        # 只取一个候选会得到「有画面没声音」或「有声音没画面」的残缺文件。
        # 所以要分别收集音频轨和视频轨，最后用 ffmpeg 合并。
        best_video: tuple[bytes, str] | None = None
        best_audio: tuple[bytes, str] | None = None
        plain_av: tuple[bytes, str] | None = None   # 音视频合一的 mp4

        for target in media_urls:
            print(f"  尝试: {target[:96]}...")
            try:
                resp = await page.request.get(
                    target,
                    headers={
                        "Referer": "https://www.douyin.com/",
                        "User-Agent": (
                            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) "
                            "Chrome/131.0.0.0 Safari/537.36"
                        ),
                        "Accept": "*/*",
                        "Accept-Language": "zh-CN,zh;q=0.9",
                        "Range": "bytes=0-",
                    },
                )
            except Exception as exc:
                print(f"    ✗ 请求异常 {type(exc).__name__}")
                continue

            if resp.status not in (200, 206):
                print(f"    ✗ status={resp.status}")
                continue
            ct = (resp.headers.get("content-type") or "").lower()
            raw = await resp.body()
            if ct and not any(k in ct for k in ("video", "audio", "octet-stream")):
                print(f"    ✗ 非媒体 {ct}")
                continue
            if len(raw) < 100 * 1024:
                print(f"    ✗ 过小 {len(raw)} bytes")
                continue

            print(f"    ✓ {len(raw)/1024/1024:.2f} MB ({ct or 'unknown'})")
            # 关键：媒体轨类型看 URL 标记，不看 content-type。
            # 抖音的 media-audio-* 也返回 video/mp4，靠 content-type 无法区分。
            is_audio_track = "media-audio-" in target
            if is_audio_track:
                if best_audio is None or len(raw) > len(best_audio[0]):
                    best_audio = (raw, ".m4a")
                continue
            if ct.startswith("audio"):
                if best_audio is None or len(raw) > len(best_audio[0]):
                    best_audio = (raw, ".m4a")
                continue
            # 视频轨
            if best_video is None or len(raw) > len(best_video[0]):
                best_video = (raw, ".mp4")
            # 候选都试完了

        # 决定产物
        if best_video and best_audio:
            # DASH 分离流：先落盘再 ffmpeg 合并
            OUT_DIR.mkdir(parents=True, exist_ok=True)
            base = safe_name(aweme_id + "_" + title_holder["t"])
            vtmp = OUT_DIR / f".{base}.v.mp4"
            atmp = OUT_DIR / f".{base}.a.m4a"
            vtmp.write_bytes(best_video[0])
            atmp.write_bytes(best_audio[0])
            dest = OUT_DIR / f"{base}.mp4"
            ok = merge_av(vtmp, atmp, dest)
            vtmp.unlink(missing_ok=True)
            atmp.unlink(missing_ok=True)
            if ok:
                print(f"  ✓ 合并音视频 → {dest.name}")
                await ctx.close()
                return dest
            print("  ⚠ 合并失败，退回单选产物")
            body, ext = (best_video if len(best_video[0]) >= len(best_audio[0])
                         else best_audio)
        elif best_video:
            body, ext = best_video
        elif best_audio:
            body, ext = best_audio
        else:
            print("  ✗ 所有候选地址都失败")
            await ctx.close()
            return None

        await ctx.close()
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        dest = OUT_DIR / f"{safe_name(aweme_id + '_' + title_holder['t'])}{ext}"
        dest.write_bytes(body)
        print(f"  ✓ {dest}")
        return dest


async def main(ids: list[str]) -> int:
    ok = 0
    for aid in ids:
        print(f"=== {aid} ===")
        try:
            r = await download_one(aid)
            if r:
                ok += 1
        except Exception as exc:
            print(f"  FAIL {type(exc).__name__}: {exc}")
    print(f"\n完成 {ok}/{len(ids)}")
    return 0 if ok else 1


if __name__ == "__main__":
    ids = sys.argv[1:] or ["7614221080818896166"]
    sys.exit(asyncio.run(main(ids)))
