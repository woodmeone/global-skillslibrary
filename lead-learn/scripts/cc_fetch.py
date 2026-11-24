"""从 CookieCloud 服务端拉取 cookie，转成 Playwright / yt-dlp 能用的格式。

为什么需要这个：
  持久化 profile 的登录态会过期。CookieCloud 由浏览器扩展定时上传，
  我们从服务端拉最新的一份，pipeline 就不依赖「本地浏览器还登着」。

三层分工，依赖单向（本文件 → cc_config → cc_crypto）：
  cc_crypto.py   纯加解密 + HTTP，不认识配置
  cc_config.py   凭据解析与校验，不认识 cookie 格式
  本文件          取数 + 转 Netscape / Playwright 格式

用法：
    python cc_fetch.py show                       # 看有哪些域名、多少 cookie
    python cc_fetch.py profiles                   # 看有几份账号、哪些可用
    python cc_fetch.py export bilibili            # 导出 Netscape cookies.txt
    python cc_fetch.py export bilibili --profile edge-a
"""

from __future__ import annotations

import json
import sys

from paths import OUT as OUT_DIR
import cc_config
import cc_crypto


# ---- 取数 -----------------------------------------------------------------

def fetch_payload(profile: str | None = None) -> dict:
    """拉一份并解密。profile 名字可指定，缺省走 cc_config 的默认选择。

    加解密本身在 cc_crypto 里——这里只负责「先选账号，再取数」。
    """
    prof = cc_config.select(profile)
    return cc_crypto.fetch_payload(prof.host, prof.uuid, prof.password)


# 兼容旧调用点：health.py / 诊断脚本用过 cc_fetch._get
_get = cc_crypto.get


def all_cookies(payload: dict) -> dict[str, list[dict]]:
    """按域名分组。"""
    data = payload.get("cookie_data") or {}
    return {k: v for k, v in data.items() if isinstance(v, list) and v}


# ---- 格式转换 -------------------------------------------------------------

def to_netscape(cookies: list[dict]) -> str:
    lines = ["# Netscape HTTP Cookie File", "# from CookieCloud", ""]
    for c in cookies:
        domain = c.get("domain") or ""
        if not domain:
            continue
        include_sub = "TRUE" if domain.startswith(".") else "FALSE"
        path = c.get("path") or "/"
        secure = "TRUE" if c.get("secure") else "FALSE"
        exp = c.get("expirationDate") or c.get("expires")
        try:
            exp = int(float(exp)) if exp else 0
        except (TypeError, ValueError):
            exp = 0
        name = c.get("name") or ""
        value = c.get("value") or ""
        if not name:
            continue
        lines.append(f"{domain}\t{include_sub}\t{path}\t{secure}\t{exp}\t{name}\t{value}")
    return "\n".join(lines) + "\n"


def to_playwright(cookies: list[dict]) -> list[dict]:
    """转 Playwright add_cookies 格式。"""
    out = []
    for c in cookies:
        domain = c.get("domain") or ""
        name = c.get("name") or ""
        if not domain or not name:
            continue
        item = {
            "name": name,
            "value": c.get("value") or "",
            "domain": domain,
            "path": c.get("path") or "/",
            "secure": bool(c.get("secure")),
            "httpOnly": bool(c.get("httpOnly")),
        }
        ss = (c.get("sameSite") or "").lower()
        if ss in ("lax", "strict", "none"):
            item["sameSite"] = ss.capitalize()
        else:
            item["sameSite"] = "Lax"
        exp = c.get("expirationDate") or c.get("expires")
        if exp:
            try:
                item["expires"] = float(exp)
            except (TypeError, ValueError):
                pass
        out.append(item)
    return out


# ---- 命令 -----------------------------------------------------------------

def cmd_profiles() -> int:
    print(f"凭据文件：{cc_config.CC_CONF}\n")
    print(cc_config.summary())
    try:
        got = cc_config.select()
        print(f"\n默认使用：{got.name}")
        return 0
    except cc_config.CCConfigError as e:
        print(f"\n⚠ {e}")
        return 2


def cmd_show(profile: str | None = None) -> int:
    p = fetch_payload(profile)
    groups = all_cookies(p)
    if not groups:
        print("CookieCloud 里没有 cookie_data —— 扩展可能还没上传")
        return 1
    print(f"共 {len(groups)} 个域名：\n")
    for dom in sorted(groups):
        cks = groups[dom]
        names = sorted({c.get("name", "") for c in cks})
        print(f"  {dom:32} {len(cks):3} 个  {names[:5]}")
    ls = p.get("local_storage_data") or {}
    if ls:
        print(f"\nlocal_storage 域名: {list(ls.keys())}")
    return 0


def cmd_export(platform: str, profile: str | None = None) -> int:
    p = fetch_payload(profile)
    groups = all_cookies(p)

    # CookieCloud 的域名键不一定等于真实域名。
    # 设了「同步域名关键词 bilibili」后，扩展回传的键就是 "bilibili" 本身，
    # 而不是 ".bilibili.com"。所以按子串匹配，不要写死域名列表。
    needle = platform
    picked: list[dict] = []
    matched_keys: list[str] = []
    for dom, cks in groups.items():
        if needle in dom:
            picked.extend(cks)
            matched_keys.append(dom)

    # 若键名不含平台名（比如键是真实域名但平台名不同拼法），
    # 再看 cookie 自身的 domain 字段
    if not picked:
        for dom, cks in groups.items():
            if any(needle in (c.get("domain") or "") for c in cks):
                picked.extend(cks)
                matched_keys.append(dom)

    if not picked:
        print(f"CookieCloud 里没有 {platform} 的 cookie")
        print(f"已有域名键: {sorted(groups)}")
        return 3

    print(f"匹配到的键: {matched_keys}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    txt = OUT_DIR / f"{platform}-cookies.txt"
    txt.write_text(to_netscape(picked), encoding="utf-8")

    js = OUT_DIR / f"{platform}-cookies.json"
    js.write_text(
        json.dumps(to_playwright(picked), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"[{platform}] {len(picked)} 个 cookie")
    names = sorted({c.get("name", "") for c in picked})
    important = [n for n in names if any(k in n.lower() for k in ("sess", "sid", "uid", "ttwid"))]
    print(f"  关键项: {important[:8]}")
    print(f"  → {txt}")
    print(f"  → {js}")
    return 0


def _pop_opt(args: list[str], flag: str) -> tuple[list[str], str | None]:
    """摘出 `--flag value`，返回剩余参数和值。"""
    if flag in args:
        i = args.index(flag)
        if i + 1 >= len(args):
            raise SystemExit(f"{flag} 后面要跟一个值")
        val = args[i + 1]
        del args[i:i + 2]
        return args, val
    return args, None


def main() -> int:
    args = list(sys.argv[1:])
    args, prof = _pop_opt(args, "--profile")
    if not args:
        print(__doc__)
        return 64
    cmd = args[0]
    try:
        if cmd == "show":
            return cmd_show(prof)
        if cmd == "profiles":
            return cmd_profiles()
        if cmd == "export":
            plat = args[1] if len(args) > 1 else "bilibili"
            return cmd_export(plat, prof)
    except cc_config.CCConfigError as e:
        print(f"✗ 凭据不可用：\n{e}", file=sys.stderr)
        return 2
    except (LookupError, PermissionError, ConnectionError) as e:
        # cc_crypto 抛的这三类都是「能说人话」的故障，不该变成裸 traceback
        print(f"✗ {e}", file=sys.stderr)
        return 1
    except RuntimeError as e:
        print(f"✗ {e}", file=sys.stderr)
        return 1
    print(__doc__)
    return 64


if __name__ == "__main__":
    sys.exit(main())
