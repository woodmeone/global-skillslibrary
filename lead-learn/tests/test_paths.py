"""paths.py 的解耦回归测试。

对应 2026-11-24 的架构调整：派单落在工作区，**不跟 recall 记忆区绑定**。
改 paths.py 或 dispatch.py 的落盘逻辑之前先跑这个。
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))


@pytest.fixture()
def clean_env(monkeypatch, tmp_path):
    """清掉所有相关环境变量与用户配置影响，返回一台干净的解析环境。"""
    for k in ("LEAD_LEARN_HOME", "LEAD_LEARN_AGENT", "LEAD_LEARN_DISPATCH",
              "MIDNIGHT_BASE_DIR", "BILI_UID", "FAV_LIMIT"):
        monkeypatch.delenv(k, raising=False)

    home = tmp_path / "work"
    home.mkdir()
    monkeypatch.setenv("LEAD_LEARN_HOME", str(home))
    # 把用户级配置指到不存在的路径，避免本机 ~/.lead-learn/config.json 干扰
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "nouser"))
    monkeypatch.setenv("HOME", str(tmp_path / "nouser"))

    for mod in ("paths", "dispatch", "pipeline"):
        sys.modules.pop(mod, None)
    import importlib
    import paths
    importlib.reload(paths)
    yield paths, home
    for mod in ("paths", "dispatch", "pipeline"):
        sys.modules.pop(mod, None)


def test_dispatch_in_workarea_not_recall(clean_env):
    """核心不变量：派单目录在工作区，不在 recall 记忆区。

    这是 2026-11-24 架构调整的验收点。原来 AGENT 一设就把 DISPATCH 指到
    <RECALL>/<agent>/longterm/dispatch，把过程状态塞进了长期记忆。
    """
    p, home = clean_env
    assert p.DISPATCH == home / "dispatch", f"落到实处了：{p.DISPATCH}"


def test_agent_env_does_not_move_dispatch(clean_env, monkeypatch):
    """设了 LEAD_LEARN_AGENT 也不许改变落盘位置。"""
    p, home = clean_env
    monkeypatch.setenv("LEAD_LEARN_AGENT", "lead")
    for mod in ("paths",):
        sys.modules.pop(mod, None)
    import importlib
    import paths
    importlib.reload(paths)

    assert paths.AGENT == "lead", "AGENT 应被读到（用于登记 LONGTERM）"
    assert paths.DISPATCH == home / "dispatch", (
        f"AGENT=lead 把派单目录带跑了：{paths.DISPATCH}——这等于又绑回记忆区"
    )


def test_explicit_dispatch_still_wins(clean_env, monkeypatch, tmp_path):
    """显式 LEAD_LEARN_DISPATCH 仍然最高优先（这条没被动过）。"""
    p, home = clean_env
    custom = tmp_path / "custom"
    custom.mkdir()
    monkeypatch.setenv("LEAD_LEARN_DISPATCH", str(custom))
    for mod in ("paths",):
        sys.modules.pop(mod, None)
    import importlib
    import paths
    importlib.reload(paths)
    assert paths.DISPATCH == custom


def test_recall_optional_missing_ok(clean_env, monkeypatch, tmp_path):
    """recall 不存在时，整条链路照跑（skill 不依赖它）。"""
    p, home = clean_env
    monkeypatch.setenv("MIDNIGHT_BASE_DIR", str(tmp_path / "no_recall_here"))
    for mod in ("paths", "dispatch"):
        sys.modules.pop(mod, None)
    import importlib
    import dispatch
    importlib.reload(dispatch)

    assert not dispatch.RECALL.exists()
    # 关键：不抛异常，且派单目录仍然可算出来
    assert dispatch.DISPATCH == home / "dispatch"
    assert dispatch._roster() == [], "没有 recall 时花名册应为空，不该崩"


def test_bili_uid_has_no_default(clean_env):
    """BILI_UID 不许内置任何人的账号（公开仓库里那是隐私）。"""
    p, _ = clean_env
    assert p.BILI_UID == "", f"BILI_UID 有默认值：{p.BILI_UID!r}"


def test_config_file_is_read(clean_env, monkeypatch, tmp_path):
    """用户级配置文件生效（env 未设时）。"""
    p, home = clean_env
    userdir = tmp_path / "user2"
    (userdir / ".lead-learn").mkdir(parents=True)
    (userdir / ".lead-learn" / "config.json").write_text(
        json.dumps({"home": str(tmp_path / "cfg_home"), "bili_uid": "42"}, ensure_ascii=False),
        encoding="utf-8",
    )
    monkeypatch.delenv("LEAD_LEARN_HOME")
    monkeypatch.setenv("USERPROFILE", str(userdir))
    monkeypatch.setenv("HOME", str(userdir))

    for mod in ("paths",):
        sys.modules.pop(mod, None)
    import importlib
    import paths
    importlib.reload(paths)

    assert paths.HOME == (tmp_path / "cfg_home").resolve() or str(paths.HOME) == str(tmp_path / "cfg_home")
    assert paths.BILI_UID == "42"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
