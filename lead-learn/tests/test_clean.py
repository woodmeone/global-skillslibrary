"""pipeline.cmd_clean 的回归测试。

对应 2026-11-24 实测：盘上 40 MB 媒体永远清不掉，因为 clean 只认
route in (subtitle, asr) 且 transcript 存在的 mp4。含 pitfall #24
（dry-run 曾真删文件）的守卫。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))


@pytest.fixture()
def sandbox(monkeypatch, tmp_path):
    """独立 workarea + 真实小文件，断言沙箱生效。"""
    home = tmp_path / "workarea"
    media = home / "media-downloads"
    media.mkdir(parents=True)
    out = home / ".favorites-out"
    out.mkdir(parents=True)

    monkeypatch.setenv("LEAD_LEARN_HOME", str(home))

    # ---- 造 5 种典型产物 ----
    # 1) 有文本 + mp4 → 该删
    (media / "a.mp4").write_bytes(b"x" * 100)
    (media / "a.txt").write_text("转录文本" * 20, encoding="utf-8")
    # 2) storyboard 有抽帧 + mp4 → 该删
    (media / "b.mp4").write_bytes(b"x" * 100)
    (media / "b-storyboard-1.png").write_bytes(b"p" * 50)
    # 3) no_speech 无产出 + m4a → 该删
    (media / "c.m4a").write_bytes(b"x" * 100)
    # 4) storyboard 失败、无抽帧、无文本 → **必须保留**（唯一副本，归 retry 管）
    (media / "d.mp4").write_bytes(b"x" * 100)
    # 5) 有文本 + m4a → 该删（旧版只认 .mp4，m4a 漏清）
    (media / "e.m4a").write_bytes(b"x" * 100)
    (media / "e.txt").write_text("音轨转录" * 20, encoding="utf-8")

    state = {
        "processed": {
            "k1": {"route": "asr", "file": str(media / "a.mp4"), "transcript": str(media / "a.txt")},
            "k2": {"route": "storyboard", "file": str(media / "b.mp4")},
            "k3": {"route": "no_speech", "file": str(media / "c.m4a")},
            "k4": {"route": "storyboard", "file": str(media / "d.mp4")},
            "k5": {"route": "asr", "file": str(media / "e.m4a"), "transcript": str(media / "e.txt")},
        },
        "runs": [],
    }
    (out / "pipeline-state.json").write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")

    for mod in ("pipeline", "paths"):
        sys.modules.pop(mod, None)
    import importlib
    import pipeline as _p
    importlib.reload(_p)

    assert str(_p.OUT_ROOT) == str(media), f"沙箱没生效：OUT_ROOT={_p.OUT_ROOT}"
    assert str(_p.STATE_FILE) == str(out / "pipeline-state.json"), (
        f"STATE_FILE 没指向沙箱：{_p.STATE_FILE}"
    )

    yield _p, media

    for mod in ("pipeline", "paths"):
        sys.modules.pop(mod, None)


def test_dry_run_deletes_nothing(sandbox):
    """pitfall #24：dry-run 分支曾写在删除之后，真删过文件。"""
    p, media = sandbox
    before = {f.name for f in media.iterdir()}
    p.cmd_clean(keep_mp4=True)
    after = {f.name for f in media.iterdir()}
    assert before == after, f"dry-run 删了文件：少了 {before - after}"


def test_clean_removes_media_with_transcript(sandbox):
    """有文本的条目，媒体是中间产物，该删。"""
    p, media = sandbox
    p.cmd_clean()
    assert not (media / "a.mp4").exists(), "有文本的 mp4 没删"
    assert (media / "a.txt").exists(), "文本被误删"


def test_clean_removes_m4a_too(sandbox):
    """纯音频产物旧版漏清（只认 .mp4）。"""
    p, media = sandbox
    p.cmd_clean()
    assert not (media / "e.m4a").exists(), "有文本的 m4a 没删（旧版只认 mp4）"


def test_clean_removes_orphan_with_storyboard(sandbox):
    """storyboard 条目有抽帧留底 → 媒体可删。旧版完全不管这类，永久占盘。"""
    p, media = sandbox
    p.cmd_clean()
    assert not (media / "b.mp4").exists(), "有抽帧留底的孤儿媒体没删"


def test_clean_removes_no_speech_without_output(sandbox):
    """no_speech 且无任何产出 → 媒体可删。"""
    p, media = sandbox
    p.cmd_clean()
    assert not (media / "c.m4a").exists(), "no_speech 无产出的媒体没删"


def test_clean_keeps_ambiguous_media(sandbox):
    """既无文本、又无抽帧、也没标失败 → 不猜，留着。"""
    p, media = sandbox
    p.cmd_clean()
    assert (media / "d.mp4").exists(), "可疑媒体被误删了——判据不允许靠猜"


def test_no_orphans_flag_restores_old_behaviour(sandbox):
    """--no-orphans 应退回旧行为：只清有文本的。"""
    p, media = sandbox
    p.cmd_clean(orphans=False)
    assert not (media / "a.mp4").exists(), "有文本的没清"
    assert (media / "b.mp4").exists(), "--no-orphans 仍删了孤儿媒体"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
