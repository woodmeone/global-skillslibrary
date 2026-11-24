"""CookieCloud 服务端端到端验证。

验证三件事：
  1. 能上传（POST /update）
  2. 能取回（GET /get/:uuid）
  3. 能按 CookieCloud 协议正确解密

解密算法（官方文档）：
  key = md5(uuid + '-' + password)[:16]
  AES.decrypt(encrypted, key)  → CryptoJS 格式（OpenSSL 兼容，Salted__ 前缀）
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import urllib.request
from pathlib import Path

from paths import CC_CONF as CONF  # noqa: E402


def load_conf() -> dict:
    # 该文件由 PowerShell 写成，带 UTF-8 BOM
    return json.loads(CONF.read_text(encoding="utf-8-sig"))


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

    raw = __import__("base64").b64decode(ciphertext_b64)
    if not raw.startswith(b"Salted__"):
        raise ValueError("不是 CryptoJS 格式（缺 Salted__ 前缀）")
    salt = raw[8:16]
    body = raw[16:]
    key, iv = evp_bytes_to_key(passphrase.encode("utf-8"), salt, 32, 16)
    dec = Cipher(algorithms.AES(key), modes.CBC(iv)).decryptor()
    plain = dec.update(body) + dec.finalize()
    # 去 PKCS7 padding
    pad = plain[-1]
    if 1 <= pad <= 16:
        plain = plain[:-pad]
    return plain.decode("utf-8")


def crypto_js_encrypt(passphrase: str, data: dict) -> str:
    """按 CryptoJS 格式加密，用于测试上传。"""
    import base64
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


def post(url: str, fields: dict) -> tuple[int, str]:
    data = urllib.parse.urlencode(fields).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.status, r.read().decode("utf-8", "replace")


def get(url: str) -> tuple[int, str]:
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


def main() -> int:
    import urllib.parse

    conf = load_conf()
    host = conf["host"].rstrip("/")
    uuid = conf["uuid"]
    password = conf["password"]
    key_pass = hashlib.md5(f"{uuid}-{password}".encode()).hexdigest()[:16]
    print(f"host={host}")
    print(f"uuid={uuid}")
    print(f"派生密钥={key_pass}")

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
    print(f"\n=== 1. POST /update ===")
    st, body = post(f"{host}/update", {"uuid": uuid, "encrypted": encrypted})
    print(f"  status={st} body={body[:200]}")

    # --- 2. 取回 ---
    print(f"\n=== 2. GET /get/{uuid[:8]}... ===")
    st, body = get(f"{host}/get/{uuid}")
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
    print(f"\n=== 3. 解密 ===")
    try:
        plain = crypto_js_decrypt(key_pass, enc)
        got = json.loads(plain)
        print(f"  ✓ 解密成功")
        print(f"  cookie_data 域名: {list(got.get('cookie_data', {}).keys())}")
        ck = got["cookie_data"][".test.local"][0]
        print(f"  cookie: {ck['name']}={ck['value']}")
        assert ck["value"] == "hello-cookiecloud", "值不匹配"
        print(f"\n✅ 端到端验证通过")
        return 0
    except Exception as exc:
        print(f"  ✗ 解密失败: {type(exc).__name__}: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
