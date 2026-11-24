"""dispatch.py 的回归测试。

每一条对应 2026-11-24 实测出来的一个真 bug。改 dispatch.py 之前先跑这个。

运行：
    cd <skill>/scripts
    python -m pytest ../tests -q
或（无 pytest 时）：
    python ../tests/test_dispatch.py
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))


@pytest.fixture()
def sandbox(monkeypatch, tmp_path):
    """每个测试一套独立的 workarea + 派单目录，**并且断言沙箱真的生效**。

    这条断言是血换来的：2026-11-24 我写测试时只清了 dispatch 模块缓存、
    没清 paths，于是 DISPATCH 还是旧值，apply 直接写到真实盘，
    回写了两份真源稿的 status。测试碰真实数据之前，先证明它碰的不是真实数据。

    另外**不读真实工作区**：待分流可能为 0（稿子都学完了），依赖真实数据
    会让测试随盘面状态时跳时过。样本一律自己造。
    """
    home = tmp_path / "workarea"
    staging = home / ".favorites-out" / "longterm-staging"
    staging.mkdir(parents=True)
    dispatch_dir = home / "dispatch"
    dispatch_dir.mkdir()

    monkeypatch.setenv("LEAD_LEARN_HOME", str(home))
    monkeypatch.setenv("LEAD_LEARN_DISPATCH", str(dispatch_dir))

    # 造 4 份样本稿，两种平台、三种初始状态
    samples = [
        ("bili:BVtest001", "样本甲", "bilibili", "staged_needs_review", "这是样本甲的正文，够判归属。"),
        ("bili:BVtest002", "样本乙", "bilibili", "staged_brief_needs_review", "乙。"),
        ("dy:1000000000000000001", "样本丙", "douyin", "staged_needs_review", "这是样本丙的正文。"),
        ("dy:1000000000000000002", "样本丁", "douyin", "dispatched:liangliang", "丁，已派过单。"),
    ]
    for key, title, plat, status, body in samples:
        (staging / f"{title}.staged.md").write_text(
            f"---\nkey: {key}\ntitle: {title}\nplatform: {plat}\n"
            f"chars: {len(body)}\nstatus: {status}\n---\n\n## 转录全文\n\n{body}\n",
            encoding="utf-8",
        )

    for mod in ("dispatch", "paths"):
        sys.modules.pop(mod, None)
    import importlib
    import dispatch as _d
    importlib.reload(_d)

    assert str(_d.DISPATCH) == str(dispatch_dir), (
        f"沙箱没生效！DISPATCH={_d.DISPATCH}，期望 {dispatch_dir}——"
        "此断言失败时必须停止，否则测试会污染真实盘"
    )
    assert str(_d.STAGING) == str(staging), f"STAGING 没指向沙箱：{_d.STAGING}"

    yield _d, dispatch_dir

    for mod in ("dispatch", "paths"):
        sys.modules.pop(mod, None)


def _backup_statuses(staging: Path) -> dict[Path, str]:
    """备份源稿 status 行。apply 会回写它，测完必须还原。"""
    import re
    backup = {}
    for f in staging.glob("*.staged.md"):
        raw = f.read_text(encoding="utf-8")
        m = re.search(r"(?m)^status:.*$", raw)
        if m:
            backup[f] = m.group(0)
    return backup


def _restore_statuses(backup: dict[Path, str]) -> None:
    import re
    for f, line in backup.items():
        raw = f.read_text(encoding="utf-8")
        f.write_text(re.sub(r"(?m)^status:.*$", line, raw, count=1), encoding="utf-8")


@pytest.fixture()
def staging_guard(sandbox):
    """自动备份/还原源稿 status，任何测试都不会留下污染。

    yield (dispatch 模块, 派单目录)，与 sandbox 同形状，测试里统一 `d, tmp = ...`。
    """
    d, tmp = sandbox
    backup = _backup_statuses(d.STAGING)
    yield d, tmp
    _restore_statuses(backup)


def _pending_keys(d) -> list[str]:
    return [i["key"] for i in d._items()]


def test_list_skips_dispatched(sandbox):
    """BUG#1：_items() 只跳过 routed:，apply 却写 dispatched:，一条都没跳过。

    症状：已派单 18 份仍被算成「待分流」，每晚重复派一遍。
    """
    d, _ = sandbox
    alln = len(list(d.STAGING.glob("*.staged.md")))
    pend = len(d._items())
    assert pend < alln, f"待分流 {pend} == 全部 {alln}，dispatched 没被跳过"
    # 逐条核：所有 dispatched 的都不该出现在待分流里
    for f in d.STAGING.glob("*.staged.md"):
        meta, _b = d._read_front(f.read_text(encoding="utf-8", errors="replace"))
        st = meta.get("status", "")
        if st.startswith(("dispatched", "dropped", "undecided", "routed")):
            assert meta["key"] not in _pending_keys(d), (
                f"{meta['key']} status={st} 却仍被当成待分流"
            )


def test_apply_same_agent_two_spellings(staging_guard):
    """BUG#3：plan 里一条写目录名、一条写显示名 → 撞同一文件，2 条只落 1 条。"""
    d, tmp = staging_guard
    keys = _pending_keys(d)[:2]
    if len(keys) < 2:
        pytest.skip("待分流不足 2 条，无法测")
    plan = {"round": "t", "items": [
        {"key": keys[0], "title": "甲", "url": "u1",
         "to": [{"agent": "liangliang", "reason": "r1"}]},
        {"key": keys[1], "title": "乙", "url": "u2",
         "to": [{"agent": "量量", "reason": "r2"}]},   # 显示名
    ]}
    pf = tmp / "plan.json"
    pf.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
    d.cmd_apply(pf, confirm=True)

    n = 0
    for f in tmp.glob("*_staging.md"):
        n += len([l for l in f.read_text(encoding="utf-8").splitlines()
                  if l.startswith("## ")])
    assert n == 2, f"plan 2 条只落盘 {n} 条（同名文件互相覆盖）"


def test_apply_appends_not_overwrites(staging_guard):
    """BUG#2：apply 整份覆盖 → 上一轮没学完的派单静默消失。"""
    d, tmp = staging_guard
    keys = _pending_keys(d)[:2]
    if len(keys) < 2:
        pytest.skip("待分流不足 2 条")

    p1 = {"round": "r1", "items": [
        {"key": keys[0], "title": "丙", "url": "u3",
         "to": [{"agent": "量量", "reason": "r1"}]}]}
    (tmp / "p1.json").write_text(json.dumps(p1, ensure_ascii=False), encoding="utf-8")
    d.cmd_apply(tmp / "p1.json", confirm=True)

    p2 = {"round": "r2", "items": [
        {"key": keys[1], "title": "丁", "url": "u4",
         "to": [{"agent": "量量", "reason": "r2"}]}]}
    (tmp / "p2.json").write_text(json.dumps(p2, ensure_ascii=False), encoding="utf-8")
    d.cmd_apply(tmp / "p2.json", confirm=True)

    txt = next(tmp.glob("量量_staging.md")).read_text(encoding="utf-8")
    assert keys[0] in txt, "上一轮派单被覆盖掉了"
    assert keys[1] in txt, "本轮派单没写进去"


def test_apply_marks_dropped(staging_guard):
    """BUG#5（本轮新发现）：plan 的 dropped 不回写 status → 丢弃稿每晚被重新捞出。"""
    d, tmp = staging_guard
    keys = _pending_keys(d)[:1]
    if not keys:
        pytest.skip("没有可测的待分流条目")
    k = keys[0]
    plan = {"round": "t", "items": [], "dropped": [{"key": k, "title": "x", "why": "纯歌词"}]}
    pf = tmp / "plan.json"
    pf.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
    d.cmd_apply(pf, confirm=True)

    for f in d.STAGING.glob("*.staged.md"):
        meta, _b = d._read_front(f.read_text(encoding="utf-8", errors="replace"))
        if meta.get("key") == k:
            assert meta.get("status") == "dropped", f"丢弃稿 status 是 {meta.get('status')}"
            break
    else:
        pytest.skip("找不到该 key")


def test_pending_count_ignores_struck_entries(sandbox, tmp_path):
    """BUG#6：status 读 frontmatter 的 count，划掉条目不改它 → 永远显示旧数字。"""
    d, tmp = sandbox
    f = tmp / "量量_staging.md"
    f.write_text(
        "---\ncount: 2\n---\n\n## 1. 甲\n\n## 2. 乙\n",
        encoding="utf-8",
    )
    assert d._pending_count(f) == 2
    # 模拟子智能体划掉第 1 条
    f.write_text(f.read_text(encoding="utf-8").replace("## 1. 甲", "## ~~1. 甲~~"),
                 encoding="utf-8")
    assert d._pending_count(f) == 1, "划掉的条目仍被算进待消化数"


def test_status_reports_count_drift(sandbox, capsys):
    """count 字段与实际条数不符时要明确报漂移，不许静默。"""
    d, tmp = sandbox
    f = tmp / "量量_staging.md"
    f.write_text("---\ncount: 5\n---\n\n## 1. 甲\n", encoding="utf-8")
    d.cmd_status()
    out = capsys.readouterr().out
    assert "漂移" in out, f"count=5 但实际 1 条，status 没报漂移：\n{out}"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
