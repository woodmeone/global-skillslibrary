"""转发壳一致性测试。

背景：工作区（`$LEAD_LEARN_HOME`）里的 `cc_fetch.py` / `health.py` / `cc_verify.py`
曾经是手工写的壳，不在仓库里。谁删了壳、或模板漂移了，没有任何机制会响——
而壳一旦缺失或过期，"同一命令两个结果"那个 bug 就回来了。

`scripts/make_forwarders.py` 是壳的唯一生成源。这里守住两件事：

  1. 生成器本身能跑、且 `--check` 对刚生成的内容判定一致（幂等）
  2. 壳的内容包含关键要素（runpy 转发、sys.path 指向 skill、不在壳里写逻辑）
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))


@pytest.fixture()
def gen():
    sys.modules.pop("make_forwarders", None)
    import importlib
    import make_forwarders
    importlib.reload(make_forwarders)
    return make_forwarders


def test_all_entrypoints_have_templates(gen):
    """三个入口都要有模板，且顺序稳定。"""
    assert set(gen.FORWARDED) == {"cc_fetch.py", "health.py", "cc_verify.py"}


def test_rendered_shell_is_valid_python(gen):
    """壳必须是合法 Python 且无 SyntaxWarning。"""
    import ast
    import warnings

    for name in gen.FORWARDED:
        src = gen.render(name)
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            ast.parse(src)          # 有 \s 这类非法转义会抛 SyntaxWarning


def test_shell_forwards_via_runpy(gen):
    """壳必须真的把参数转给 skill，且把 skill 目录放进 sys.path。"""
    for name in gen.FORWARDED:
        src = gen.render(name)
        assert "runpy.run_path" in src, f"{name} 没转发"
        assert 'run_name="__main__"' in src, f"{name} 不以 __main__ 执行，参数不会透传"
        assert "sys.path.insert" in src, (
            f"{name} 没把 skill 目录加进 sys.path，"
            f"被转发的脚本 import 不到 paths/cc_config"
        )
        # 目标必须指向 skill 里的同名文件
        assert f'"{name}"' in src


def test_shell_has_no_business_logic(gen):
    """壳里不许长逻辑——它只该转发。"""
    for name in gen.FORWARDED:
        src = gen.render(name)
        # 除了 import / runpy / sys.path / sys.exit，不该出现函数定义
        assert "def " not in src.replace("def render", ""), f"{name} 壳里出现了函数定义"
        assert "class " not in src, f"{name} 壳里出现了类"
        # 不许自己解析参数（那是被转发脚本的活）
        assert "argparse" not in src, f"{name} 壳里在解析参数"


def test_warns_about_destructive_verify(gen):
    """cc_verify 的壳必须提醒它会覆盖服务端数据。"""
    src = gen.render("cc_verify.py")
    assert "覆盖" in src, "cc_verify 壳没提醒会 POST 覆盖真实 cookie"


def test_generator_check_mode_on_fresh_output(gen, tmp_path):
    """生成到空目录后，--check 必须判定一致（幂等）。"""
    r = subprocess.run(
        [sys.executable, str(SCRIPTS / "make_forwarders.py"),
         "--out", str(tmp_path)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    assert r.returncode == 0, r.stderr
    for name in gen.FORWARDED:
        assert (tmp_path / name).exists()

    r2 = subprocess.run(
        [sys.executable, str(SCRIPTS / "make_forwarders.py"),
         "--out", str(tmp_path), "--check"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    assert r2.returncode == 0, r2.stdout + r2.stderr


def test_check_detects_drift(gen, tmp_path):
    """壳被改坏后，--check 必须报不一致（退回码 1）。"""
    r = subprocess.run(
        [sys.executable, str(SCRIPTS / "make_forwarders.py"), "--out", str(tmp_path)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    assert r.returncode == 0, r.stderr

    # 模拟「有人手工改了壳」
    target = tmp_path / "cc_fetch.py"
    target.write_text("# 被手改过\n", encoding="utf-8")

    r2 = subprocess.run(
        [sys.executable, str(SCRIPTS / "make_forwarders.py"),
         "--out", str(tmp_path), "--check"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    assert r2.returncode == 1, "漂移没被发现：" + r2.stdout


def test_check_detects_missing_shell(gen, tmp_path):
    """壳缺失时 --check 必须报错。"""
    r = subprocess.run(
        [sys.executable, str(SCRIPTS / "make_forwarders.py"),
         "--out", str(tmp_path), "--check"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    assert r.returncode == 1


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
