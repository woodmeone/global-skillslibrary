"""CookieCloud 的加解密与 HTTP。独立成模块，**不依赖 paths / cc_config**。

为什么要单独一层：

    `cc_config.set_credentials()` 需要在写盘前验证「新口令能不能解开服务端
    数据」。而解密的实现在 `cc_fetch.py`，`cc_fetch` 又要 `import cc_config`
    来选 profile——两者直接互相 import 就成了循环。

    把纯粹的密码学与 HTTP 放进这里（不碰任何配置解析、不碰路径），
    `cc_config` 和 `cc_fetch` 都向下依赖它，依赖方向单向。

协议（官方文档）：
    key = md5(uuid + '-' + password)[:16]
    AES.decrypt(encrypted, key)  → CryptoJS 格式（OpenSSL 兼容，Salted__ 前缀）
"""

from __future__ import annotations

import base64
import hashlib
import json


def key_pass(uuid: str, password: str) -> str:
    """CookieCloud 的 AES 口令：md5(uuid-password)[:16]。"""
    return hashlib.md5(f"{uuid}-{password}".encode()).hexdigest()[:16]


def evp_bytes_to_key(password: bytes, salt: bytes,
                     key_len: int, iv_len: int) -> tuple[bytes, bytes]:
    """OpenSSL EVP_BytesToKey（MD5），CryptoJS AES 用的就是这个。"""
    derived = b""
    prev = b""
    while len(derived) < key_len + iv_len:
        prev = hashlib.md5(prev + password + salt).digest()
        derived += prev
    return derived[:key_len], derived[key_len:key_len + iv_len]


def decrypt(key_password: str, ciphertext_b64: str) -> dict:
    """解 CryptoJS.AES.encrypt 的输出。

    口令不对时会抛 UnicodeDecodeError 或 json.JSONDecodeError（乱码恰好
    可 utf-8 解码时会走到后者）——调用方要同时处理这两种。
    """
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

    raw = base64.b64decode(ciphertext_b64)
    if not raw.startswith(b"Salted__"):
        raise ValueError("非 CryptoJS 格式（缺 Salted__ 前缀）")
    salt, body = raw[8:16], raw[16:]
    key, iv = evp_bytes_to_key(key_password.encode(), salt, 32, 16)
    d = Cipher(algorithms.AES(key), modes.CBC(iv)).decryptor()
    plain = d.update(body) + d.finalize()
    pad = plain[-1]
    if 1 <= pad <= 16:
        plain = plain[:-pad]
    return json.loads(plain.decode("utf-8"))


def encrypt(key_password: str, data: dict) -> str:
    """按 CryptoJS 格式加密，用于测试上传。"""
    import os as _os

    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

    text = json.dumps(data, ensure_ascii=False)
    salt = _os.urandom(8)
    key, iv = evp_bytes_to_key(key_password.encode("utf-8"), salt, 32, 16)
    raw = text.encode("utf-8")
    pad = 16 - (len(raw) % 16)
    raw += bytes([pad]) * pad
    enc = Cipher(algorithms.AES(key), modes.CBC(iv)).encryptor()
    body = enc.update(raw) + enc.finalize()
    return base64.b64encode(b"Salted__" + salt + body).decode("ascii")


def get(url: str, timeout: int = 30) -> tuple[int, str]:
    """GET，返回 (状态码, 文本)。HTTP 错误码不抛异常，直接返回。"""
    import urllib.error
    import urllib.request

    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


def fetch_payload(host: str, uuid: str, password: str,
                  timeout: int = 30) -> dict:
    """拉一份并解密。返回解码后的 payload。

    各类失败都用**可读的中文**区分，不把裸异常抛给上层——
    「服务端没数据(404)」和「口令不对(解不开)」是两种完全不同的故障，
    混成一句「CookieCloud 失败」会让排查从头开始。
    """
    st, body = get(f"{host.rstrip('/')}/get/{uuid}", timeout=timeout)
    if st == 404:
        raise LookupError(
            f"服务端没有这个 uuid 的数据（404）。\n"
            f"  可能：①扩展还没同步过 ②uuid 填错了 ③服务器数据被清了\n"
            f"  怎么办：在浏览器 CookieCloud 扩展里点「立即同步」，再跑一次。"
        )
    if st != 200:
        raise ConnectionError(f"CookieCloud 返回 {st}: {body[:200]}")
    import json as _json
    j = _json.loads(body)
    enc = j.get("encrypted")
    if not enc:
        raise LookupError("响应无 encrypted 字段（可能扩展还没上传过）")
    try:
        return decrypt(key_pass(uuid, password), enc)
    except (UnicodeDecodeError, ValueError) as exc:
        raise PermissionError(
            f"解密失败：password 与上传时用的不一致（{type(exc).__name__}）。\n"
            f"  你改了扩展里的密码，但配置里还是旧的？\n"
            f"  怎么办：把扩展设置页里的 password 抄进配置，两边必须一模一样。"
        ) from None
