# -*- coding: utf-8 -*-
"""通用手册截图器：按配置批量截取角色页面，自动隐藏开发浮标、压缩体积。

用法：
    python shoot.py --config shots.json --base http://localhost:3000 \
                    --out docs/manual-shots --chrome "C:\\path\\chrome.exe"

配置格式（shots.json）：
{
  "viewport": [1440, 900],
  "accounts": {
    "admin":    {"email": "a@x.com", "password": "***", "login": "/sign-in"},
    "merchant": {"email": "m@x.com", "password": "***", "login": "/sign-in"}
  },
  "anon": [                                  # 非登录态，按顺序截
    {"name": "u01-home", "url": "/", "full": true},
    {"name": "u02-search", "url": "/search"}
  ],
  "sessions": {                              # 每个角色一个独立浏览器上下文
    "merchant": [
      {"name": "m01-overview", "url": "/console"},
      {"name": "m02-detail", "follow": "a[href^='/console/orders/']",
       "from": "/console/orders"}
    ]
  },
  "compress": 1240                           # 长边像素，0 = 不压缩
}

关键设计：
- 每个角色独立 context，登录态互不污染。
- follow：先访问 from 页，取第一个匹配选择器的 href 再跳转，用于详情页。
- 隐藏 nextjs-portal 等开发浮标，否则每张图左下角都有 "N Insight"。
- 压缩成 JPEG，长边 1240px 足够 15.5cm 宽印刷，体积从数百 KB 降到几十 KB。
"""
import argparse
import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright
from PIL import Image

HIDE_CSS = """
nextjs-portal, [data-nextjs-toast], [data-nextjs-dev-tools-button],
#__next-build-watcher, nextjs-dev-tools-indicator { display: none !important; }
"""


def load_config(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def prepare(page):
    """注入隐藏开发浮标的样式。每次导航后都要重新注入。"""
    try:
        page.add_style_tag(content=HIDE_CSS)
    except Exception:
        pass


def save(page, out_dir, name, full=True, wait=900, compress=1240):
    page.wait_for_timeout(wait)
    raw = out_dir / f"{name}.png"
    page.screenshot(path=str(raw), full_page=full)
    if compress:
        im = Image.open(raw).convert("RGB")
        w, h = im.size
        if w > compress:
            im = im.resize((compress, int(h * compress / w)), Image.LANCZOS)
        target = out_dir / f"{name}.jpg"
        im.save(target, "JPEG", quality=86, optimize=True, progressive=True)
        raw.unlink()
        print(f"  {name}.jpg  {target.stat().st_size // 1024}KB")
    else:
        print(f"  {name}.png  {raw.stat().st_size // 1024}KB")


def login(page, base, account):
    page.goto(base + account.get("login", "/sign-in"), wait_until="networkidle", timeout=60000)
    prepare(page)
    page.fill('input[name="email"]', account["email"])
    page.fill('input[name="password"]', account["password"])
    page.click('button[type="submit"]')
    page.wait_for_timeout(account.get("settle_ms", 2800))
    prepare(page)


def shoot_anon(page, base, items, out_dir, compress):
    for item in items:
        page.goto(base + item["url"], wait_until="networkidle", timeout=60000)
        prepare(page)
        if item.get("fill"):
            for sel, val in item["fill"].items():
                page.fill(sel, val)
        save(page, out_dir, item["name"], item.get("full", True),
             item.get("wait", 900), compress)


def shoot_session(page, base, items, out_dir, compress):
    for item in items:
        if item.get("follow"):
            page.goto(base + item["from"], wait_until="networkidle", timeout=60000)
            prepare(page)
            page.wait_for_timeout(1200)
            el = page.query_selector(item["follow"])
            if not el:
                print(f"  [跳过] {item['name']}：选择器未命中 {item['follow']}")
                continue
            page.goto(base + el.get_attribute("href"), wait_until="networkidle", timeout=60000)
            prepare(page)
        else:
            page.goto(base + item["url"], wait_until="networkidle", timeout=60000)
            prepare(page)
        if item.get("scroll") is not None:
            page.evaluate(f"window.scrollTo(0,{item['scroll']})")
            page.wait_for_timeout(400)
        save(page, out_dir, item["name"], item.get("full", True),
             item.get("wait", 1200), compress)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--base", required=True, help="站点根地址，如 http://localhost:3000")
    ap.add_argument("--out", required=True)
    ap.add_argument("--chrome", help="Chrome/Chromium 可执行文件路径")
    args = ap.parse_args()

    cfg = load_config(args.config)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    compress = cfg.get("compress", 1240)
    vw, vh = cfg.get("viewport", [1440, 900])

    launch_kw = {}
    if args.chrome:
        launch_kw["executable_path"] = args.chrome

    with sync_playwright() as p:
        browser = p.chromium.launch(**launch_kw)

        if cfg.get("anon"):
            print("=== 非登录态 ===")
            ctx = browser.new_context(viewport={"width": vw, "height": vh},
                                      device_scale_factor=2, locale=cfg.get("locale", "zh-TW"))
            shoot_anon(ctx.new_page(), args.base, cfg["anon"], out_dir, compress)
            ctx.close()

        for role, items in (cfg.get("sessions") or {}).items():
            print(f"=== {role} ===")
            ctx = browser.new_context(viewport={"width": vw, "height": vh}, device_scale_factor=2)
            page = ctx.new_page()
            if role in (cfg.get("accounts") or {}):
                login(page, args.base, cfg["accounts"][role])
            shoot_session(page, args.base, items, out_dir, compress)
            ctx.close()

        browser.close()
    print("DONE")


if __name__ == "__main__":
    sys.exit(main())
