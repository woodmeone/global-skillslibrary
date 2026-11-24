"""从 CookieCloud 服务端拉取 cookie，转成 Playwright / yt-dlp 能用的格式。

为什么需要这个：
  持久化 profile 的登录态会过期。CookieCloud 由浏览器扩展定时上传，
  我们从服务端拉最新的一份，pipeline 就不依赖「本地浏览器还登着」。

用法：
    python cc_fetch.py show              # 看有哪些域名、多少 cookie
    python cc_fetch.py export bilibili   # 导出 Netscape cookies.txt
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

from paths import CC_CONF as CONF, OUT as OUT_DIR  # noqa: E402


def load_conf() -> dict:
    return json.loads(CONF.read_text(encoding="utf-8-sig"))


def evp_bytes_to_key(password: bytes, salt: bytes, key_len: int, iv_len: int) -> tuple[bytes, bytes]:
    derived = b""
    prev = b""
    while len(derived) < key_len + iv_len:
        prev = hashlib.md5(prev + password + salt).digest()
        derived += prev
    return derived[:key_len], derived[key_len:key_len + iv_len]


def decrypt(key_pass: str, ciphertext_b64: str) -> dict:
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

    raw = base64.b64decode(ciphertext_b64)
    if not raw.startswith(b"Salted__"):
        raise ValueError("非 CryptoJS 格式")
    salt, body = raw[8:16], raw[16:]
    key, iv = evp_bytes_to_key(key_pass.encode(), salt, 32, 16)
    d = Cipher(algorithms.AES(key), modes.CBC(iv)).decryptor()
    plain = d.update(body) + d.finalize()
    pad = plain[-1]
    if 1 <= pad <= 16:
        plain = plain[:-pad]
    return json.loads(plain.decode("utf-8"))


def fetch_payload() -> dict:
    conf = load_conf()
    host = conf["host"].rstrip("/")
    uuid = conf["uuid"]
    password = conf["password"]
    key_pass = hashlib.md5(f"{uuid}-{password}".encode()).hexdigest()[:16]

    st, body = _get(f"{host}/get/{uuid}")
    if st != 200:
        raise RuntimeError(f"CookieCloud 返回 {st}: {body[:200]}")
    j = json.loads(body)
    enc = j.get("encrypted")
    if not enc:
        raise RuntimeError("响应无 encrypted 字段（可能扩展还没上传过）")
    return decrypt(key_pass, enc)


def _get(url: str) -> tuple[int, str]:
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


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


def all_cookies(payload: dict) -> dict[str, list[dict]]:
    """按域名分组。"""
    data = payload.get("cookie_data") or {}
    return {k: v for k, v in data.items() if isinstance(v, list) and v}


def cmd_show() -> int:
    p = fetch_payload()
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


def cmd_export(platform: str) -> int:
    p = fetch_payload()
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


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 64
    cmd = sys.argv[1]
    if cmd == "show":
        return cmd_show()
    if cmd == "export":
        plat = sys.argv[2] if len(sys.argv) > 2 else "bilibili"
        return cmd_export(plat)
    print(__doc__)
    return 64


if __name__ == "__main__":
    sys.exit(main())
