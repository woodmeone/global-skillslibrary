"""B站 UID 与 CookieCloud profile 的绑定回归测试。

为什么单独测这个：
    这是**最阴的一类错**——cookie 和 UID 两个值各自都合法，配错了哪儿都不报错，
    只是抓回来的收藏夹悄悄换了个人，而且下次还会覆盖掉同名 JSON。

    实测（2026-11-24）：Chrome 那份 cookie 的 DedeUserID 与 Edge 那份不是同一个号，
    而配置里写的还是 Edge 的。不校验的话，B站收藏数据会一直是「另一个人的」，
    而日志里一切正常。

    （真实 UID 是账号标识，不入库。测试里用同形状的假值。）
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))


@pytest.fixture()
def env(tmp_path, monkeypatch):
    """干净环境：工作区在 tmp，用户配置也在 tmp。"""
    for k in ("LEAD_LEARN_HOME", "LEAD_LEARN_CC_PROFILE", "BILI_UID",
              "LEAD_LEARN_AGENT", "LEAD_LEARN_DISPATCH", "MIDNIGHT_BASE_DIR",
              "FAV_LIMIT"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("LEAD_LEARN_HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "nouser"))
    monkeypatch.setenv("HOME", str(tmp_path / "nouser"))

    for mod in ("paths", "cc_config"):
        sys.modules.pop(mod, None)
    import importlib
    import paths
    importlib.reload(paths)
    yield paths, tmp_path
    for mod in ("paths", "cc_config"):
        sys.modules.pop(mod, None)


def mk_config(tmp_path: Path, data: dict) -> Path:
    userdir = tmp_path / "user"
    (userdir / ".lead-learn").mkdir(parents=True, exist_ok=True)
    p = userdir / ".lead-learn" / "config.json"
    p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return userdir


def reload_paths(monkeypatch, tmp_path, data: dict):
    import importlib
    userdir = mk_config(tmp_path, data)
    monkeypatch.setenv("USERPROFILE", str(userdir))
    monkeypatch.setenv("HOME", str(userdir))
    sys.modules.pop("paths", None)
    import paths
    importlib.reload(paths)
    return paths


# ---- 绑定 -----------------------------------------------------------------

def test_uid_follows_profile(env, monkeypatch, tmp_path):
    """cc_profile 指哪份账号，BILI_UID 就必须跟着指哪个。"""
    p = reload_paths(monkeypatch, tmp_path, {
        "home": str(tmp_path),
        "cc_profile": "edge-a",
        "bili_uid_by_profile": {
            "edge-a": "1234567890",
            "chrome-b": "9876543210987654",
        },
    })
    assert p.CC_PROFILE == "edge-a"
    assert p.BILI_UID == "1234567890"


def test_switching_profile_switches_uid(env, monkeypatch, tmp_path):
    """切 profile 时 UID 必须一起切——这条断了就会抓错人。"""
    p = reload_paths(monkeypatch, tmp_path, {
        "home": str(tmp_path),
        "cc_profile": "chrome-b",
        "bili_uid_by_profile": {
            "edge-a": "1234567890",
            "chrome-b": "9876543210987654",
        },
    })
    assert p.CC_PROFILE == "chrome-b"
    assert p.BILI_UID == "9876543210987654"


def test_env_uid_wins(env, monkeypatch, tmp_path):
    """显式 BILI_UID 最高优先（临时抓别人的号时用）。"""
    p = reload_paths(monkeypatch, tmp_path, {
        "home": str(tmp_path),
        "cc_profile": "edge-a",
        "bili_uid_by_profile": {"edge-a": "111"},
        "bili_uid": "999",
    })
    monkeypatch.setenv("BILI_UID", "777")
    sys.modules.pop("paths", None)
    import importlib
    import paths
    importlib.reload(paths)
    assert paths.BILI_UID == "777"


def test_falls_back_to_generic_uid(env, monkeypatch, tmp_path):
    """没绑 profile 时退回通用 bili_uid（单账号老配置仍可用）。"""
    p = reload_paths(monkeypatch, tmp_path, {
        "home": str(tmp_path),
        "bili_uid": "1234567890",
    })
    assert p.BILI_UID == "1234567890"


def test_no_uid_configured_is_empty(env, monkeypatch, tmp_path):
    """什么都不配时必须是空字符串，不许有内置默认值。"""
    p = reload_paths(monkeypatch, tmp_path, {"home": str(tmp_path)})
    assert p.BILI_UID == ""


# ---- 交叉校验 -------------------------------------------------------------

def _load_cc():
    sys.modules.pop("cc_config", None)
    import importlib
    import cc_config
    importlib.reload(cc_config)
    return cc_config


def test_cross_check_detects_mismatch(env, monkeypatch, tmp_path):
    """显式 profile 与 UID 绑定来源不一致时要点出来。"""
    reload_paths(monkeypatch, tmp_path, {
        "home": str(tmp_path),
        "cc_profile": "edge-a",
        "bili_uid_by_profile": {"edge-a": "1234567890", "chrome-b": "3546"},
    })
    cc = _load_cc()
    prof = cc.Profile(name="chrome-b", host="https://h", uuid="u", password="p")
    warns = cc.check_bili_uid_binding(prof)
    assert warns, "跨账号时必须警告"
    assert "收藏夹" in warns[0]


def test_cross_check_ok_when_same(env, monkeypatch, tmp_path):
    reload_paths(monkeypatch, tmp_path, {
        "home": str(tmp_path),
        "cc_profile": "edge-a",
        "bili_uid_by_profile": {"edge-a": "1234567890"},
    })
    cc = _load_cc()
    prof = cc.Profile(name="edge-a", host="https://h", uuid="u", password="p")
    assert cc.check_bili_uid_binding(prof) == []


# ---- 运行时校验（bili_grab3.check_uid_match）-----------------------------
#
# 这两条锁住「两层校验不重复、但都生效」：配置层来自 cc_config，
# 运行时层来自导出的 cookie。合并前两处各写一遍，容易漂移。


def _load_grab(monkeypatch, tmp_path, uid, cookie_ids=None):
    """加载 bili_grab3，把 OUT/COOKIE_JSON/UID 指到 tmp，不发网络。"""
    reload_paths(monkeypatch, tmp_path, {"home": str(tmp_path)})
    monkeypatch.setenv("BILI_UID", uid)

    out = tmp_path / ".favorites-out"
    out.mkdir(parents=True, exist_ok=True)
    cj = out / "bilibili-cookies.json"
    if cookie_ids is not None:
        cj.write_text(json.dumps(
            [{"name": "DedeUserID", "value": v, "domain": ".bilibili.com"}
             for v in cookie_ids] +
            [{"name": "SESSDATA", "value": "x", "domain": ".bilibili.com"}]
        ), encoding="utf-8")

    for mod in ("paths", "cc_config", "bili_grab3"):
        sys.modules.pop(mod, None)
    import importlib
    import paths
    importlib.reload(paths)
    # 覆盖 paths 里的产物路径到 tmp
    paths.OUT = out
    paths.BILI_COOKIES_JSON = cj
    import cc_config
    importlib.reload(cc_config)
    import bili_grab3
    importlib.reload(bili_grab3)
    # reload 会从 paths 再取一次，这里再钉一次防止落回真实盘
    bili_grab3.COOKIE_JSON = cj
    bili_grab3.UID = uid
    return bili_grab3


def test_runtime_check_ok(env, monkeypatch, tmp_path):
    g = _load_grab(monkeypatch, tmp_path, "1234567890", ["1234567890"])
    assert g.check_uid_match() == []


def test_runtime_check_detects_wrong_account(env, monkeypatch, tmp_path):
    """cookie 是别人的号 → 必须报，这是防「抓错人」的最后一道。"""
    g = _load_grab(monkeypatch, tmp_path, "1234567890", ["9876543210987654"])
    warns = g.check_uid_match()
    assert warns, "cookie 与 UID 不同号却没报"
    assert any("别人的收藏夹" in w for w in warns)


def test_runtime_check_missing_dedeuserid(env, monkeypatch, tmp_path):
    """没有 DedeUserID = 未登录态，要提示而不是静默。"""
    g = _load_grab(monkeypatch, tmp_path, "1234567890", [])
    warns = g.check_uid_match()
    assert any("未登录" in w for w in warns)


def test_runtime_check_does_not_double_report_missing_uid(env, monkeypatch, tmp_path):
    """没配 UID 时只由配置层报一次，运行时层不重复。"""
    g = _load_grab(monkeypatch, tmp_path, "", ["1234567890"])
    warns = g.check_uid_match()
    # 配置层会报「没配 BILI_UID」，但不许出现两条一样的
    assert len([w for w in warns if "没配 BILI_UID" in w]) <= 1


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
