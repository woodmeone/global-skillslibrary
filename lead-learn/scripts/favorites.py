"""收藏夹摄取器 —— 阶段一：Playwright 持久化登录 + 抓取收藏夹。

设计要点：
1. 用 persist 目录保存登录态，登录一次长期复用（不是明文 storage_state 快照）
2. 无头=False，窗口留给人类手动登录
3. 登录检测靠页面信号，不靠猜
4. 拿到链接就落盘 JSON，方便下一步交给 media-downloader

用法：
    python favorites.py login bilibili
    python favorites.py login douyin
    python favorites.py grab bilibili
    python favorites.py grab douyin
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import sys
from pathlib import Path

from playwright.async_api import async_playwright

# ---- 常量 ----

from paths import CHROMIUM  # noqa: E402

# 登录态持久化目录（每个平台独立，避免 cookie 互相污染）
PROFILE_ROOT = Path(
    os.path.expandvars(r"%LOCALAPPDATA%\dsh-bili-humanism\browser-profiles")
)

from paths import OUT as OUT_DIR  # noqa: E402
from paths import FAV_LIMIT  # noqa: E402  ← 抓取窗口的唯一出处
from paths import BILI_UID  # noqa: E402  ← 不设默认值，没配就明确报错

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)

TARGETS = {
    "bilibili": {
        "login_url": "https://www.bilibili.com/",
        # 收藏页 URL 由 BILI_UID 拼，不写死任何人的账号（2026-11-24 脱敏）
        "fav_url": "https://space.bilibili.com/{uid}/favlist",
        # 登录成功后左上角会出现头像元素
        "logged_in": ".header-avatar-wrap, .bili-avatar, .avatar",
        "fav_api": "/x/v3/fav/resource/list",
    },
    "douyin": {
        "login_url": "https://www.douyin.com/",
        "fav_url": "https://www.douyin.com/user/self?showTab=favorite_collection",
        "logged_in": "div[data-e2e='user-avatar'], .avatar",
        "fav_api": "/aweme/v1/web/aweme/listcollection",
    },
}


def log(msg: str) -> None:
    print(msg, flush=True)


# ---- 浏览器 ----

async def open_context(pw, platform: str, headless: bool = False):
    """打开带持久化 profile 的浏览器上下文。"""
    profile = PROFILE_ROOT / platform
    profile.mkdir(parents=True, exist_ok=True)
    ctx = await pw.chromium.launch_persistent_context(
        user_data_dir=str(profile),
        executable_path=CHROMIUM,
        headless=headless,
        viewport={"width": 1440, "height": 900},
        user_agent=UA,
        locale="zh-CN",
        args=["--disable-blink-features=AutomationControlled"],
    )
    return ctx


async def is_logged_in(page, platform: str) -> bool:
    """检测是否已登录。用可见性 + cookie 双判据。"""
    sel = TARGETS[platform]["logged_in"]
    try:
        el = await page.query_selector(sel)
        if el and await el.is_visible():
            return True
    except Exception:
        pass

    cookies = await page.context.cookies()
    names = {c["name"] for c in cookies}
    if platform == "bilibili":
        return "SESSDATA" in names
    if platform == "douyin":
        # 抖音登录态 cookie 名之一
        return bool({"sessionid", "sessionid_ss", "sid_tt"} & names)
    return False


# ---- 抓取：拦截 XHR ----

async def grab_bilibili(ctx, page) -> list[dict]:
    """B站：直接调收藏夹 API（同一登录态），取每个夹子最新 N 条。

    默认只取最新 40 条，不翻全量。B站收藏 API 按收藏时间倒序返回，
    所以第 1 页前若干条就是「最新收藏」。
    """
    uid = BILI_UID
    if not uid:
        log("  ✗ 没设 BILI_UID —— 不知道该抓谁的收藏夹")
        log("    设法：环境变量 BILI_UID，或 ~/.lead-learn/config.json 里写 \"bili_uid\": \"你的UID\"")
        return []
    limit = FAV_LIMIT
    found: list[dict] = []

    folders = []
    try:
        resp = await page.request.get(
            f"https://api.bilibili.com/x/v3/fav/folder/created/list-all?up_mid={uid}"
        )
        data = await resp.json()
        folders = (data.get("data") or {}).get("list") or []
        log(f"  收藏夹数量: {len(folders)}，目标取最新 {limit} 条")
    except Exception as exc:
        log(f"  拿收藏夹列表失败: {type(exc).__name__}: {exc}")

    if not folders:
        log("  !! 收藏夹列表为空 —— 未登录或收藏夹私密")
        return found

    # 按各夹子的「最近更新时间」排序，先取更新最频繁的
    # 兼容 mtime 缺失的情况
    folders.sort(key=lambda f: f.get("mtime") or 0, reverse=True)

    taken = 0
    for f in folders:
        if taken >= limit:
            break
        media_id = f.get("id")
        if not (f.get("media_count") or 0):
            continue
        try:
            medias = []
            # 同一页面连续打 API 会被限流（返回空/非 JSON），加节流 + 单次重试
            for attempt in range(2):
                r = await page.request.get(
                    "https://api.bilibili.com/x/v3/fav/resource/list"
                    f"?media_id={media_id}&pn=1&ps=20&platform=web"
                )
                txt = await r.text()
                try:
                    j = json.loads(txt)
                except json.JSONDecodeError:
                    # 限流：退避后重试一次
                    await page.wait_for_timeout(1200 * (attempt + 1))
                    continue
                medias = (j.get("data") or {}).get("medias") or []
                break
            else:
                log(f"    夹={f.get('title')} 限流跳过（重试后仍非 JSON）")
                await page.wait_for_timeout(800)
                continue
        except Exception as exc:
            log(f"    夹={f.get('title')} 读取失败: {type(exc).__name__}")
            continue

        for m in medias:
            if taken >= limit:
                break
            found.append({
                "platform": "bilibili",
                "folder": f.get("title"),
                "bvid": m.get("bvid"),
                "title": m.get("title"),
                "author": (m.get("upper") or {}).get("name"),
                "duration": m.get("duration"),
                # fav_time 是收藏时间戳，用它排「最新」
                "fav_time": m.get("fav_time"),
                "url": f"https://www.bilibili.com/video/{m.get('bvid')}",
            })
            taken += 1
        log(f"    夹={f.get('title')} +{len(medias)} 累计={taken}/{limit}")
        # 夹子之间留间隔，避免限流
        await page.wait_for_timeout(700)

    # 再按收藏时间倒序排一次，确保真的是「最新 N 条」
    found.sort(key=lambda x: x.get("fav_time") or 0, reverse=True)
    return found[:limit]


async def grab_douyin(ctx, page) -> list[dict]:
    """抖音：打开收藏页，拦截 XHR 收集 aweme 列表，取最新 N 条。"""
    limit = FAV_LIMIT
    found: list[dict] = []
    seen: set[str] = set()
    api_hits: list[str] = []

    async def on_response(resp):
        url = resp.url
        if "listcollection" not in url and "aweme/v1/web/aweme" not in url:
            return
        api_hits.append(url[:160])
        try:
            j = await resp.json()
        except Exception:
            return
        rows = j.get("aweme_list") or j.get("data") or []
        if not isinstance(rows, list):
            return
        for r in rows:
            if not isinstance(r, dict):
                continue
            aid = str(r.get("aweme_id") or "")
            if not aid or aid in seen:
                continue
            seen.add(aid)
            desc = (r.get("desc") or "")[:80]
            found.append({
                "platform": "douyin",
                "aweme_id": aid,
                "title": desc,
                "collect_time": r.get("collect_time") or r.get("create_time"),
                "url": f"https://www.douyin.com/video/{aid}",
            })

    page.on("response", lambda r: asyncio.create_task(on_response(r)))

    await page.goto(TARGETS["douyin"]["fav_url"], wait_until="domcontentloaded")
    await page.wait_for_timeout(4000)

    # 滚到拿够为止。屏数按 limit 推，不再写死 8 屏。
    # 实测每屏约 2.5 条（一次 wheel 1800px + 1.5s 等待），取保守值 2 条/屏，
    # 再留 50% 余量。写死 8 屏时，limit=100 永远只拿得到 ~20 条且不报错。
    max_scrolls = max(8, int(limit / 2 * 1.5))
    for i in range(max_scrolls):
        if len(found) >= limit:
            break
        await page.mouse.wheel(0, 1800)
        await page.wait_for_timeout(1500)
        log(f"    scroll {i+1}/{max_scrolls}  collected={len(found)}/{limit}")

    log(f"  命中 API 次数: {len(api_hits)}")
    if len(found) < limit:
        log(f"  ⚠ 只拿到 {len(found)} 条（目标 {limit}）—— 收藏总数可能就这么多，"
            f"或滚动到第 {max_scrolls} 屏仍未加载完")
    # 按收藏时间倒序（缺字段的排后面）
    found.sort(key=lambda x: x.get("collect_time") or 0, reverse=True)
    return found[:limit]


# ---- 命令 ----

async def cmd_login(platform: str) -> int:
    async with async_playwright() as pw:
        ctx = await open_context(pw, platform, headless=False)
        page = await ctx.new_page()
        await page.goto(TARGETS[platform]["login_url"], wait_until="domcontentloaded")

        log(f"[{platform}] 浏览器已打开，请手动登录。")
        log(f"[{platform}] 登录完成后保持页面，等待检测（最多 300 秒）...")

        for i in range(60):
            await page.wait_for_timeout(5000)
            if await is_logged_in(page, platform):
                log(f"[{platform}] ✓ 检测到登录态（{i*5+5}s）")
                cookies = await ctx.cookies()
                names = sorted({c["name"] for c in cookies if platform.split(".")[0][:3] in c["domain"] or True})
                log(f"[{platform}] cookie 数量: {len(cookies)}")
                keep = [n for n in names if any(k in n.lower() for k in ("sess", "sid", "token", "uid"))]
                log(f"[{platform}] 关键 cookie 名: {keep[:10]}")
                await ctx.close()
                return 0
            if i % 6 == 5:
                log(f"  等待中... {i*5+5}s")

        log(f"[{platform}] ✗ 超时未检测到登录")
        await ctx.close()
        return 1


async def cmd_grab(platform: str) -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as pw:
        ctx = await open_context(pw, platform, headless=False)
        page = await ctx.new_page()

        # 先开首页确认登录态
        await page.goto(TARGETS[platform]["login_url"], wait_until="domcontentloaded")
        await page.wait_for_timeout(2000)
        if not await is_logged_in(page, platform):
            log(f"[{platform}] ✗ 未登录，请先跑 login")
            await ctx.close()
            return 2
        log(f"[{platform}] ✓ 登录态有效")

        if platform == "bilibili":
            items = await grab_bilibili(ctx, page)
        else:
            items = await grab_douyin(ctx, page)

        out = OUT_DIR / f"{platform}-favorites.json"
        out.write_text(
            json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        log(f"[{platform}] 共 {len(items)} 条 → {out}")
        for it in items[:5]:
            log(f"   {it.get('bvid') or it.get('aweme_id')} | {it.get('title')}")

        await ctx.close()
    return 0 if items else 3


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__)
        return 64
    action, platform = sys.argv[1], sys.argv[2]
    if platform not in TARGETS:
        print(f"未知平台: {platform}，可选 {list(TARGETS)}")
        return 64
    if action == "login":
        return asyncio.run(cmd_login(platform))
    if action == "grab":
        return asyncio.run(cmd_grab(platform))
    print(__doc__)
    return 64


if __name__ == "__main__":
    sys.exit(main())
