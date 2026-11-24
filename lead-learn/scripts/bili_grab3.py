"""B站收藏抓取 v3 —— 优先用 CookieCloud 的 cookie，不依赖持久化 profile。

变化：
  v2 用 launch_persistent_context 读本地浏览器 profile
  v3 改成普通 launch + add_cookies，cookie 来自 CookieCloud（cc_fetch.py 导出）
      profile 只是兜底

这样就不再依赖 bili-humanism 插件目录了。
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

from playwright.async_api import async_playwright

from paths import (  # noqa: E402
    CHROMIUM,
    BILI_COOKIES_JSON as COOKIE_JSON,
    OUT as OUT_DIR,
    BILI_UID as UID,
    FAV_LIMIT,          # 抓取窗口的唯一出处（paths.py）
)


def log(m: str) -> None:
    print(m, flush=True)


async def fetch_json(page, url: str) -> dict:
    js = """
    async (u) => {
        try {
            const r = await fetch(u, { credentials: "include" });
            const t = await r.text();
            return { status: r.status, body: t };
        } catch (e) { return { status: -1, body: String(e) }; }
    }
    """
    out = await page.evaluate(js, url)
    if out["status"] != 200:
        return {"__status": out["status"], "__head": out["body"][:150]}
    try:
        return json.loads(out["body"])
    except json.JSONDecodeError:
        return {"__status": 200, "__head": out["body"][:150]}


async def main(limit: int = FAV_LIMIT) -> int:
    if not COOKIE_JSON.exists():
        log(f"✗ 缺 {COOKIE_JSON}")
        log("  先跑：python cc_fetch.py export bilibili")
        return 2

    cookies = json.loads(COOKIE_JSON.read_text(encoding="utf-8-sig"))
    if not any(c.get("name") == "SESSDATA" for c in cookies):
        log("✗ cookie 里没有 SESSDATA，登录态无效")
        return 2

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            executable_path=CHROMIUM, headless=True
        )
        ctx = await browser.new_context(
            viewport={"width": 1440, "height": 900},
            locale="zh-CN",
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
            ),
        )
        try:
            await ctx.add_cookies(cookies)
        except Exception as exc:
            log(f"✗ 注入 cookie 失败: {type(exc).__name__}: {exc}")
            await browser.close()
            return 2

        page = await ctx.new_page()
        # 先落在目标站，fetch 才是同源
        await page.goto("https://space.bilibili.com/", wait_until="domcontentloaded")
        await page.wait_for_timeout(2500)

        log(f"✓ 注入 {len(cookies)} 个 CookieCloud cookie")

        # --- 收藏夹列表 ---
        j = await fetch_json(
            page,
            f"https://api.bilibili.com/x/v3/fav/folder/created/list-all?up_mid={UID}",
        )
        folders = ((j or {}).get("data") or {}).get("list") or []
        if not folders:
            log(f"✗ 拿不到收藏夹列表: {str(j)[:200]}")
            await browser.close()
            return 3
        folders = [f for f in folders if (f.get("media_count") or 0) > 0]
        folders.sort(key=lambda f: f.get("mtime") or 0, reverse=True)
        log(f"✓ {len(folders)} 个非空收藏夹，目标取最新 {limit} 条")

        # --- 两轮取 bvid：先每夹 2 条铺开，再补齐 ---
        bvids: list[tuple[str, str]] = []
        seen: set[str] = set()

        async def pull(folder, cap: int) -> int:
            mid = folder.get("id")
            r = await fetch_json(
                page,
                "https://api.bilibili.com/x/v3/fav/resource/ids"
                f"?media_id={mid}&platform=web",
            )
            if "__status" in r:
                log(f"  ⚠ 夹={folder.get('title')} status={r.get('__status')}")
                await page.wait_for_timeout(4000)
                return 0
            rows = r.get("data") or []
            if not isinstance(rows, list):
                return 0
            got = 0
            for it in rows:
                if len(bvids) >= limit or got >= cap:
                    break
                bv = it.get("bvid") or it.get("bv_id")
                if bv and bv not in seen:
                    seen.add(bv)
                    bvids.append((bv, folder.get("title")))
                    got += 1
            return got

        for f in folders:
            if len(bvids) >= limit:
                break
            got = await pull(f, 2)
            if got:
                log(f"  ✓ 夹={f.get('title')} +{got} 累计={len(bvids)}/{limit}")
            await page.wait_for_timeout(900)

        if len(bvids) < limit:
            for f in folders:
                if len(bvids) >= limit:
                    break
                got = await pull(f, 99)
                if got:
                    log(f"  +  补 夹={f.get('title')} +{got} 累计={len(bvids)}/{limit}")
                    await page.wait_for_timeout(900)

        # --- 取详情 ---
        log(f"\n取详情 {len(bvids)} 条...")
        items: list[dict] = []
        for i, (bv, folder) in enumerate(bvids):
            r = await fetch_json(
                page, f"https://api.bilibili.com/x/web-interface/view?bvid={bv}"
            )
            if "__status" in r or not r.get("data"):
                items.append({
                    "platform": "bilibili", "folder": folder, "bvid": bv,
                    "title": "", "author": "", "duration": None,
                    "unavailable": True,
                    "url": f"https://www.bilibili.com/video/{bv}",
                })
                continue
            d = r["data"]
            items.append({
                "platform": "bilibili",
                "folder": folder,
                "bvid": bv,
                "title": d.get("title"),
                "author": (d.get("owner") or {}).get("name"),
                "duration": d.get("duration"),
                "pubdate": d.get("pubdate"),
                "url": f"https://www.bilibili.com/video/{bv}",
            })
            if (i + 1) % 10 == 0:
                log(f"  ... {i+1}/{len(bvids)}")
            await page.wait_for_timeout(600)

        OUT_DIR.mkdir(parents=True, exist_ok=True)
        dest = OUT_DIR / "bilibili-latest40.json"
        dest.write_text(
            json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        ok = sum(1 for it in items if it.get("title"))
        log(f"\n共 {len(items)} 条（可用 {ok}，失效 {len(items)-ok}）→ {dest}")

        await browser.close()
    return 0


if __name__ == "__main__":
    # 不传参就用 FAV_LIMIT（默认 100）；传了就以命令行为准
    n = int(sys.argv[1]) if len(sys.argv) > 1 else FAV_LIMIT
    sys.exit(asyncio.run(main(n)))
