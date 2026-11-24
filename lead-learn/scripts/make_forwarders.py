"""生成工作区转发壳。

为什么需要这个脚本：

    2026-11-24 之前，工作区（`$LEAD_LEARN_HOME`）里躺着一份 `cc_fetch.py` 的
    旧副本，skill 里还有一份。凭据结构升级后只有 skill 版跟着改，于是同一个
    `python cc_fetch.py show` 在工作区崩、在 skill 目录正常——同一命令两个结果，
    最费时间。修法是工作区那三个文件改成 `runpy` 转发壳。

    但壳本身当时是**手工写的**，不在仓库里：谁把壳删了、或 skill 改名了，
    没有任何机制会响。所以壳的内容收敛到这里，可以用一行命令重新生成。

用法：

    python scripts/make_forwarders.py --out "D:\\Project\\Test"
    python scripts/make_forwarders.py --out <工作区> --check   # 只检查，不写

`--check` 供测试用：断言工作区里的壳与本脚本生成的内容一致。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# 要铺到工作区的三个入口。值 = 文件头的一句用途说明。
FORWARDED = {
    "cc_fetch.py": "看有哪些域名、多少 cookie / 导出 yt-dlp 与 Playwright 格式。",
    "health.py": "整条链路一键体检。",
    "cc_verify.py": (
        "端到端验证服务端。\n"
        "⚠ 它会 POST 一份探针数据**覆盖**该 profile 在服务端的真实 cookie。\n"
        "   只想确认现有凭据能读，用 `python cc_fetch.py show`（只读）。"
    ),
}

TEMPLATE = '''"""{purpose}的转发壳 —— 真正的实现在 skill 里。

    <skill>/scripts/{name}

为什么留壳而不是删掉：

    2026-11-24 之前，工作区里躺着一份旧副本。凭据结构改成 `profiles` 数组之后，
    skill 里的版本早就改了，工作区这份没跟上，于是

        D:/工作区>  python {name}      → KeyError: 'host'
        <skill>/scripts> python {name}  → 正常

    同一个命令两个结果，最难查。删掉也不行：run.ps1、"先跑 python {name}"
    这类肌肉记忆和老文档都还指向工作区。

    所以留一个壳，把参数原样转给 skill。**壳由
    `scripts/make_forwarders.py` 生成，不要手改。**

**不要在这里加逻辑。** 要改行为改 skill 那份。
"""

import runpy
import sys
from pathlib import Path

# 工作区路径解析：环境变量 > ~/.lead-learn/config.json > 读不到就用 skill 的
# 安装位置兜底。壳要能在「工作区已配好」和「只是敲错了目录」两种情况下都给
# 出可用结果，所以顺序不能反。
_SKILL = Path.home() / ".dsh" / "skills" / "lead-learn" / "scripts"
_TARGET = _SKILL / "{name}"

if not _TARGET.exists():
    sys.exit(
        "找不到 skill 里的 {name}：%s\\n"
        "  怎么办：确认 lead-learn skill 已安装（它通常是个 junction），"
        "或直接用 skill 目录下的脚本。" % _TARGET
    )

# 让被转发的脚本能 import 到它自己的同目录模块（paths / cc_config / cc_crypto）
sys.path.insert(0, str(_SKILL))
runpy.run_path(str(_TARGET), run_name="__main__")
'''


def render(name: str) -> str:
    return TEMPLATE.format(name=name, purpose=FORWARDED[name])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", required=True, help="工作区目录（$LEAD_LEARN_HOME）")
    ap.add_argument("--check", action="store_true",
                    help="只比对，不写。不一致时退出码 1")
    ap.add_argument("--force", action="store_true",
                    help="目标已存在且内容不同时覆盖。默认只在不存在时创建")
    a = ap.parse_args()

    out = Path(a.out).expanduser()
    if not out.is_dir():
        print(f"✗ 工作区不存在：{out}")
        return 2

    rc = 0
    for name in FORWARDED:
        dest = out / name
        want = render(name)
        if a.check:
            if not dest.exists():
                print(f"✗ 缺壳：{dest}")
                rc = 1
            elif dest.read_text(encoding="utf-8") != want:
                print(f"✗ 壳与模板不一致：{dest}")
                rc = 1
            else:
                print(f"✓ {dest}")
            continue

        if dest.exists() and dest.read_text(encoding="utf-8") != want:
            if not a.force:
                print(f"⚠ 已存在且内容不同，跳过（要覆盖加 --force）：{dest}")
                continue
        dest.write_text(want, encoding="utf-8")
        print(f"✓ 写入 {dest}")

    return rc


if __name__ == "__main__":
    sys.exit(main())
