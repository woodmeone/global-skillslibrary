"""CookieCloud 服务端端到端验证。

验证三件事：
  1. 能上传（POST /update）
  2. 能取回（GET /get/:uuid）
  3. 能按 CookieCloud 协议正确解密

解密算法（官方文档）：
  key = md5(uuid + '-' + password)[:16]
  AES.decrypt(encrypted, key)  → CryptoJS 格式（OpenSSL 兼容，Salted__ 前缀）

⚠ 本脚本会**往服务端写入**一份探针数据（域名为 .test.local）。
如果你只想确认「现有凭据能不能读」，用 `python cc_fetch.py show`，
那个是只读的，不会覆盖任何真实数据。

用法：
    python cc_verify.py                    # 验证默认 profile
    python cc_verify.py --profile edge-a
"""

from __future__ import annotations

import base64
import hashlib
import json
import sys

import cc_config


# ---- 加解密 ---------------------------------------------------------------

def evp_bytes_to_key(password: bytes, salt: bytes, key_len: int, iv_len: int) -> tuple[bytes, bytes]:
    """OpenSSL EVP_BytesToKey（MD5），CryptoJS AES 用的就是这个。"""
    derived = b""
    prev = b""
    while len(derived) < key_len + iv_len:
        prev = hashlib.md5(prev + password + salt).digest()
        derived += prev
    return derived[:key_len], derived[key_len:key_len + iv_len]


def crypto_js_decrypt(passphrase: str, ciphertext_b64: str) -> str:
    """解 CryptoJS.AES.encrypt(data, passphrase) 的输出。"""
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

    raw = base64.b64decode(ciphertext_b64)
    if not raw.startswith(b"Salted__"):
        raise ValueError("不是 CryptoJS 格式（缺 Salted__ 前缀）")
    salt = raw[8:16]
    body = raw[16:]
    key, iv = evp_bytes_to_key(passphrase.encode("utf-8"), salt, 32, 16)
    dec = Cipher(algorithms.AES(key), modes.CBC(iv)).decryptor()
    plain = dec.update(body) + dec.finalize()
    pad = plain[-1]
    if 1 <= pad <= 16:
        plain = plain[:-pad]
    return plain.decode("utf-8")


def crypto_js_encrypt(passphrase: str, data: dict) -> str:
    """按 CryptoJS 格式加密，用于测试上传。"""
    import os as _os

    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

    text = json.dumps(data, ensure_ascii=False)
    salt = _os.urandom(8)
    key, iv = evp_bytes_to_key(passphrase.encode("utf-8"), salt, 32, 16)
    raw = text.encode("utf-8")
    pad = 16 - (len(raw) % 16)
    raw += bytes([pad]) * pad
    enc = Cipher(algorithms.AES(key), modes.CBC(iv)).encryptor()
    body = enc.update(raw) + enc.finalize()
    return base64.b64encode(b"Salted__" + salt + body).decode("ascii")


# ---- HTTP -----------------------------------------------------------------

def post(url: str, fields: dict) -> tuple[int, str]:
    import urllib.parse
    import urllib.request

    data = urllib.parse.urlencode(fields).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.status, r.read().decode("utf-8", "replace")


def get(url: str) -> tuple[int, str]:
    import urllib.error
    import urllib.request

    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


def main() -> int:
    args = list(sys.argv[1:])
    want = None
    if "--profile" in args:
        i = args.index("--profile")
        want = args[i + 1] if i + 1 < len(args) else None

    try:
        prof = cc_config.select(want)
    except cc_config.CCConfigError as exc:
        print(f"✗ 凭据不可用：\n{exc}")
        return 2

    host = prof.host.rstrip("/")
    key_pass = prof.key_pass()
    # ⚠ 派生密钥等价于密码：知道 md5(uuid-password) 前 16 位就能解出全部 cookie。
    # 所以这里也不打全，只留前 4 位好让两边对得上「是不是同一个」。
    print(f"profile = {prof.name}")
    print(f"host    = {host}")
    print(f"uuid    = {prof.uuid[:8]}…（已隐去）")
    print(f"派生密钥 = {key_pass[:4]}…（已隐去）")

    # --- 1. 上传测试数据 ---
    payload = {
        "cookie_data": {
            ".test.local": [
                {
                    "domain": ".test.local", "name": "probe_cookie",
                    "value": "hello-cookiecloud", "path": "/",
                    "expirationDate": 1893456000, "secure": False,
                    "httpOnly": False, "sameSite": "Lax",
                }
            ]
        },
        "local_storage_data": {},
    }
    encrypted = crypto_js_encrypt(key_pass, payload)
    print("\n=== 1. POST /update ===")
    st, body = post(f"{host}/update", {"uuid": prof.uuid, "encrypted": encrypted})
    print(f"  status={st} body={body[:200]}")

    # --- 2. 取回 ---
    print(f"\n=== 2. GET /get/{prof.uuid[:8]}... ===")
    st, body = get(f"{host}/get/{prof.uuid}")
    print(f"  status={st} len={len(body)}")
    if st != 200:
        print(f"  body={body[:200]}")
        return 1

    j = json.loads(body)
    print(f"  字段: {list(j.keys())}")
    enc = j.get("encrypted")
    if not enc:
        print("  ✗ 响应里没有 encrypted 字段")
        return 1

    # --- 3. 解密 ---
    print("\n=== 3. 解密 ===")
    try:
        plain = crypto_js_decrypt(key_pass, enc)
        got = json.loads(plain)
        print("  ✓ 解密成功")
        print(f"  cookie_data 域名: {list(got.get('cookie_data', {}).keys())}")
        ck = got["cookie_data"][".test.local"][0]
        print(f"  cookie: {ck['name']}={ck['value']}")
        assert ck["value"] == "hello-cookiecloud", "值不匹配"
        print("\n✅ 端到端验证通过")
        print("\n⚠ 注意：刚才的 POST /update **覆盖**了这份 profile 在服务端的整份数据。")
        print("   若它本来存着真实 cookie，现在只剩这条探针——浏览器扩展下次同步会再覆盖回来，")
        print("   但中间这段时间抓取会拿不到 cookie。真正的只读检查请用 `cc_fetch.py show`。")
        return 0
    except Exception as exc:
        print(f"  ✗ 解密失败: {type(exc).__name__}: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
