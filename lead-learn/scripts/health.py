"""整条链路的一键体检。

检查项：
  1. CookieCloud 服务端健康（HTTPS 可达 + 数据文件存在）
  2. CookieCloud 里有哪些域名（bilibili / douyin 到位没）
  3. 本地 cookies 是否可用
  4. 收藏数据文件是否新鲜
  5. 流水线状态

用法：
    python health.py
"""

from __future__ import annotations

import json
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

from paths import HOME as BASE, OUT, STATE, CC_CONF  # noqa: E402

OK = "✓"
BAD = "✗"
WARN = "⚠"


def line(label: str, ok: bool, detail: str = "") -> None:
    mark = OK if ok else BAD
    print(f"  {mark} {label:26} {detail}")


def warn(label: str, detail: str = "") -> None:
    print(f"  {WARN} {label:26} {detail}")


def check_cc_server() -> bool:
    if not CC_CONF.exists():
        line("CookieCloud 配置", False, "缺 cookiecloud.json")
        return False
    conf = json.loads(CC_CONF.read_text(encoding="utf-8-sig"))
    host = conf["host"].rstrip("/")
    try:
        req = urllib.request.Request(f"{host}/get/__health_probe__")
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                code = r.status
        except urllib.error.HTTPError as e:
            code = e.code
        # 404 说明服务活着（uuid 不存在），任何 2xx/4xx 都算通
        line("CookieCloud 服务", code < 500, f"{host} → {code}")
        return code < 500
    except Exception as exc:
        line("CookieCloud 服务", False, f"{type(exc).__name__}")
        return False


def check_cc_data() -> dict[str, int]:
    """返回 CookieCloud 里的域名 → cookie 数。"""
    sys.path.insert(0, str(BASE))
    try:
        import cc_fetch

        p = cc_fetch.fetch_payload()
        groups = cc_fetch.all_cookies(p)
        doms = {d: len(c) for d, c in groups.items()}
        has_bili = any("bilibili" in d for d in doms)
        has_dy = any("douyin" in d for d in doms)
        line("CookieCloud bilibili", has_bili,
             f"{sum(v for k,v in doms.items() if 'bilibili' in k)} 个 cookie")
        line("CookieCloud douyin", has_dy,
             f"{sum(v for k,v in doms.items() if 'douyin' in k)} 个 cookie")
        if not has_bili and not has_dy:
            warn("CookieCloud 内容", f"只有 {list(doms)}，扩展可能还没同步")
        return doms
    except Exception as exc:
        line("CookieCloud 取数", False, f"{type(exc).__name__}: {str(exc)[:60]}")
        return {}


def check_local_cookies() -> None:
    for plat in ("bilibili", "douyin"):
        p = OUT / f"{plat}-cookies.txt"
        if not p.exists():
            line(f"本地 {plat} cookies", False, "缺文件")
            continue
        n = sum(1 for ln in p.read_text(encoding="utf-8", errors="replace").splitlines()
                if ln and not ln.startswith("#"))
        line(f"本地 {plat} cookies", n > 0, f"{n} 条")


def check_fav_files() -> None:
    for name, label in (
        ("bilibili-latest40.json", "B站收藏数据"),
        ("douyin-favorites.json", "抖音收藏数据"),
    ):
        p = OUT / name
        if not p.exists():
            line(label, False, "缺文件")
            continue
        age_h = (datetime.now().timestamp() - p.stat().st_mtime) / 3600
        try:
            n = len(json.loads(p.read_text(encoding="utf-8-sig")))
        except Exception:
            n = -1
        fresh = age_h < 24
        (line if fresh else warn)(label, fresh, f"{n} 条，{age_h:.1f} 小时前")


def check_pipeline() -> None:
    if not STATE.exists():
        line("流水线状态", False, "还没跑过")
        return
    s = json.loads(STATE.read_text(encoding="utf-8-sig"))
    proc = s.get("processed", {})
    routes: dict[str, int] = {}
    for v in proc.values():
        r = v.get("route") or v.get("download") or "unknown"
        routes[r] = routes.get(r, 0) + 1
    line("已处理条目", True, f"{len(proc)} 条  {routes}")


def check_media() -> None:
    d = BASE / "media-downloads"
    if not d.exists():
        line("下载目录", False, "不存在")
        return
    files = list(d.glob("*.mp4"))
    total = sum(f.stat().st_size for f in files) / 1024 / 1024
    line("下载目录", True, f"{len(files)} 个 mp4，{total:.0f} MB")


def main() -> int:
    print(f"=== 链路体检 {datetime.now():%Y-%m-%d %H:%M} ===\n")
    print("[1] CookieCloud")
    check_cc_server()
    check_cc_data()
    print("\n[2] 本地凭据")
    check_local_cookies()
    print("\n[3] 收藏数据")
    check_fav_files()
    print("\n[4] 流水线")
    check_pipeline()
    check_media()
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
