"""CookieCloud 服务端端到端验证。

验证三件事：
  1. 能上传（POST /update）
  2. 能取回（GET /get/:uuid）
  3. 能按 CookieCloud 协议正确解密

加解密与 HTTP 在 cc_crypto.py（唯一出处），本文件只编排验证流程。

⚠ 本脚本会**往服务端写入**一份探针数据（域名为 .test.local）。
如果你只想确认「现有凭据能不能读」，用只读的 `python cc_fetch.py show`。

用法：
    python cc_verify.py                    # 验证默认 profile
    python cc_verify.py --profile edge-a
"""

from __future__ import annotations

import json
import sys
import urllib.parse
import urllib.request

import cc_config
import cc_crypto


def post(url: str, fields: dict) -> tuple[int, str]:
    data = urllib.parse.urlencode(fields).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.status, r.read().decode("utf-8", "replace")


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
    kp = prof.key_pass()
    # ⚠ 派生密钥等价于密码：知道 md5(uuid-password)[:16] 就能解出全部 cookie。
    # 所以这里也不打全，只留前 4 位——够判断「两次跑的是不是同一份凭据」。
    print(f"profile = {prof.name}")
    print(f"host    = {host}")
    print(f"uuid    = {prof.safe_uuid()}")
    print(f"派生密钥 = {kp[:4]}…（已隐去）")

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
    encrypted = cc_crypto.encrypt(kp, payload)
    print("\n=== 1. POST /update ===")
    st, body = post(f"{host}/update", {"uuid": prof.uuid, "encrypted": encrypted})
    print(f"  status={st} body={body[:200]}")

    # --- 2. 取回 ---
    print(f"\n=== 2. GET /get/{prof.safe_uuid()} ===")
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
        got = cc_crypto.decrypt(kp, enc)
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


# 兼容旧调用点
get = cc_crypto.get


if __name__ == "__main__":
    sys.exit(main())
