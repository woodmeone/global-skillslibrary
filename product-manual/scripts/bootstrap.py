# -*- coding: utf-8 -*-
"""本地起站体检与启动辅助。

截图前必须确认站点真的能跑。踩过的坑都固化在这里：

1. pnpm 全局 shim 可能失效（报 "...\\pnpm\\pnpm" is not recognized）。
   → 绕过 pnpm，直接用 node 调 next 的 bin。
2. Google Fonts 拉不到时 `next build` 直接失败。
   → 别浪费时间走生产构建，用 dev 模式截图。
3. dev 模式下 Cookie 若为 SameSite=None 且无 Secure，浏览器静默丢弃，
   → 购物车 / 登录态看起来"不生效"。解法见 references/pitfalls.md，
     用 Playwright 注入 Cookie 绕过，不要改项目代码。

用法：
    python bootstrap.py --dir D:/path/to/repo --check
    python bootstrap.py --dir D:/path/to/repo --start --port 3000
    python bootstrap.py --dir D:/path/to/repo --migrate --database-url postgres://...
"""
import argparse
import json
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


def find_next_bin(repo):
    """优先用项目内 next，规避 pnpm / npx 的 shim 问题。"""
    cand = repo / "node_modules" / "next" / "dist" / "bin" / "next"
    return cand if cand.exists() else None


def find_package_manager(repo):
    for name in ("pnpm-lock.yaml", "package-lock.json", "yarn.lock", "bun.lockb"):
        if (repo / name).exists():
            return {"pnpm-lock.yaml": "pnpm", "package-lock.json": "npm",
                    "yarn.lock": "yarn", "bun.lockb": "bun"}[name]
    return None


def probe(url, timeout=30):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return r.status, len(r.read())
    except urllib.error.HTTPError as e:
        return e.code, 0
    except Exception as e:
        return None, str(e)


def check(repo, port):
    print(f"仓库: {repo}")
    print(f"  存在 package.json: {(repo / 'package.json').exists()}")
    print(f"  包管理器: {find_package_manager(repo)}")
    next_bin = find_next_bin(repo)
    print(f"  next bin: {next_bin or '未找到（需先安装依赖）'}")
    print(f"  node_modules: {(repo / 'node_modules').exists()}")
    env_file = repo / ".env"
    if env_file.exists():
        keys = [ln.split("=")[0] for ln in env_file.read_text(encoding="utf-8", errors="replace").splitlines()
                if "=" in ln and not ln.strip().startswith("#")]
        print(f"  .env 变量: {', '.join(keys)}")
    chrome = find_chrome()
    print(f"  Chrome: {chrome or '未找到'}")
    status, info = probe(f"http://127.0.0.1:{port}/")
    print(f"  端口 {port}: {status or info}")
    return next_bin


def find_chrome():
    import os
    cands = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    ]
    pw = Path(os.environ.get("LOCALAPPDATA", "")) / "ms-playwright"
    if pw.exists():
        cands += [str(p) for p in sorted(pw.glob("chromium-*/chrome-win64/chrome.exe"))]
    for c in cands:
        if Path(c).exists():
            return c
    return None


def migrate(repo, database_url):
    script = repo / "scripts" / "migrate.mjs"
    if not script.exists():
        print("未找到 scripts/migrate.mjs，跳过迁移")
        return
    env = {**os.environ, "DATABASE_URL": database_url}
    r = subprocess.run(["node", str(script)], cwd=str(repo), env=env,
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    print(r.stdout.strip())
    if r.returncode != 0:
        print(r.stderr.strip())


def start(repo, port):
    next_bin = find_next_bin(repo)
    if not next_bin:
        print("缺少 node_modules/next，先安装依赖")
        return None
    log = repo / f".manual-dev-{port}.log"
    f = open(log, "w", encoding="utf-8")
    proc = subprocess.Popen(
        ["node", str(next_bin), "dev", "-p", str(port)],
        cwd=str(repo), stdout=f, stderr=subprocess.STDOUT,
    )
    for _ in range(60):
        time.sleep(1)
        status, _info = probe(f"http://127.0.0.1:{port}/", timeout=3)
        if status:
            print(f"站点已就绪 http://127.0.0.1:{port}/  (pid={proc.pid}, log={log})")
            return proc
    print(f"启动超时，检查日志: {log}")
    return proc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--port", type=int, default=3000)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--start", action="store_true")
    ap.add_argument("--migrate", action="store_true")
    ap.add_argument("--database-url")
    args = ap.parse_args()

    repo = Path(args.dir).resolve()
    if args.check:
        check(repo, args.port)
    if args.migrate:
        if not args.database_url:
            print("--migrate 需要 --database-url")
            return 1
        migrate(repo, args.database_url)
    if args.start:
        start(repo, args.port)
    return 0


if __name__ == "__main__":
    sys.exit(main())
