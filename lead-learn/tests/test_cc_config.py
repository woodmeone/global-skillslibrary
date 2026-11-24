"""cc_config.py 的凭据解析回归测试。

背景（2026-11-24）：cookiecloud.json 从扁平结构改成 `profiles` 数组后，
cc_fetch.py / health.py 还在按 conf["host"] 取值，全部崩在 KeyError。
本文件把那次的每个坑固定成测试。

**测试不碰真实盘、不发网络请求。** 全部用 tmp_path 造凭据文件。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))


@pytest.fixture()
def cc(tmp_path, monkeypatch):
    """干净的 cc_config 环境：工作区指到 tmp，不读本机 config.json。"""
    for k in ("LEAD_LEARN_HOME", "LEAD_LEARN_CC_PROFILE", "BILI_UID",
              "LEAD_LEARN_AGENT", "LEAD_LEARN_DISPATCH", "MIDNIGHT_BASE_DIR"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("LEAD_LEARN_HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "nouser"))
    monkeypatch.setenv("HOME", str(tmp_path / "nouser"))

    for mod in ("paths", "cc_config"):
        sys.modules.pop(mod, None)
    import importlib
    import cc_config
    importlib.reload(cc_config)

    conf = tmp_path / "cookiecloud.json"
    yield cc_config, conf, tmp_path

    for mod in ("paths", "cc_config"):
        sys.modules.pop(mod, None)


def write(conf: Path, data: dict) -> None:
    conf.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


# ---- 两种格式都要认 -------------------------------------------------------

def test_flat_format_still_works(cc):
    """旧扁平格式不能被升级搞坏（向后兼容）。"""
    c, conf, _ = cc
    write(conf, {"host": "https://cc.example.com", "uuid": "abc-123",
                 "password": "secret"})
    got = c.select(path=conf)
    assert got.name == "default"
    assert got.uuid == "abc-123"


def test_profiles_format_works(cc):
    c, conf, _ = cc
    write(conf, {"profiles": [
        {"name": "edge-a", "host": "https://h", "uuid": "u1", "password": "p1"},
        {"name": "chrome-b", "host": "https://h", "uuid": "u2", "password": "p2",
         "preferred": True},
    ]})
    assert c.select(path=conf).name == "chrome-b"


def test_explicit_name_beats_preferred(cc):
    c, conf, _ = cc
    write(conf, {"profiles": [
        {"name": "edge-a", "host": "https://h", "uuid": "u1", "password": "p1"},
        {"name": "chrome-b", "host": "https://h", "uuid": "u2", "password": "p2",
         "preferred": True},
    ]})
    assert c.select("edge-a", path=conf).name == "edge-a"


# ---- 不许猜 ---------------------------------------------------------------

def test_ambiguous_without_preferred_raises(cc):
    """多份都没 preferred → 报错，不许替用户挑。

    挑错了就是拿 A 账号 cookie 抓 B 账号收藏夹，静默污染。
    """
    c, conf, _ = cc
    write(conf, {"profiles": [
        {"name": "a", "host": "https://h", "uuid": "u1", "password": "p1"},
        {"name": "b", "host": "https://h", "uuid": "u2", "password": "p2"},
    ]})
    with pytest.raises(c.CCConfigError) as ei:
        c.select(path=conf)
    assert "不替你挑" in str(ei.value)


def test_multiple_preferred_raises(cc):
    c, conf, _ = cc
    write(conf, {"profiles": [
        {"name": "a", "host": "https://h", "uuid": "u1", "password": "p1",
         "preferred": True},
        {"name": "b", "host": "https://h", "uuid": "u2", "password": "p2",
         "preferred": True},
    ]})
    with pytest.raises(c.CCConfigError) as ei:
        c.select(path=conf)
    assert "preferred" in str(ei.value)


def test_placeholder_not_treated_as_configured(cc):
    """占位值必须当「没填」，不能拿去请求服务端。"""
    c, conf, _ = cc
    write(conf, {"host": "https://h",
                 "uuid": "TODO-在Chrome扩展里生成后填这里",
                 "password": "TODO-在Chrome扩展里设置后填这里"})
    with pytest.raises(c.CCConfigError) as ei:
        c.select(path=conf)
    assert "占位" in str(ei.value)


# ---- 形状不校验（2026-11-24 的误伤）--------------------------------------

def test_non_uuid_shaped_uuid_is_accepted(cc):
    """自定义 uuid 形状必须放行。

    实测那个 20 字符的 base64 风格 uuid 在服务端返回 200 + 605KB 真实数据，
    初版按 36 位 UUID 写死正则把它判成非法，是纯误伤。
    （真实 uuid 是凭据，测试里用同形状的假值。）
    """
    c, conf, _ = cc
    fake = "Zx9QwErTyUiOpAsDfGhJ2"
    write(conf, {"host": "https://h", "uuid": fake, "password": "dummy"})
    got = c.select(path=conf)          # 不抛错
    assert got.uuid == fake
    # 但要有「形状不常见」的提示
    assert any("不是标准 UUID 形状" in w for w in got.warnings())


def test_standard_uuid_has_no_warning(cc):
    c, conf, _ = cc
    write(conf, {"host": "https://h",
                 "uuid": "00000000-1111-2222-3333-444444444444",
                 "password": "x"})
    assert c.select(path=conf).warnings() == []


# ---- 脱敏 -----------------------------------------------------------------

def test_masked_never_leaks_password(cc):
    """masked() 不许露出密码的任何片段。

    短密码的「尾 4 位」就是全文；日志会被贴进对话/issue/git。
    只查子串——逐字符查会误伤 host/name 里的普通字母。
    """
    c, conf, _ = cc
    write(conf, {"host": "https://h", "uuid": "abcdefgh-1234", "password": "edge"})
    s = c.select(path=conf).masked()
    assert "edge" not in s
    # 尾 2 位也不许露（"ge"），那是旧实现漏的
    assert "ge" not in s.split("host=")[0]
    # 长度可以露，用来让人判断「抄没抄全」
    assert "4" in s


# ---- 写回 -----------------------------------------------------------------

def test_set_credentials_updates_and_verifies(cc):
    c, conf, _ = cc
    write(conf, {"profiles": [
        {"name": "edge-a", "host": "https://h", "uuid": "u1", "password": "old"},
        {"name": "chrome-b", "host": "https://h", "uuid": "u2", "password": "old2",
         "preferred": True},
    ]})
    got = c.set_credentials("edge-a", password="new", path=conf, make_preferred=False)
    assert got.password == "new"
    # 回读确实落盘
    back = c.select("edge-a", path=conf)
    assert back.password == "new"
    # 另一份没被动
    assert c.select("chrome-b", path=conf).password == "old2"
    # _README 之类的非 profile 字段不能被写没
    raw = json.loads(conf.read_text(encoding="utf-8"))
    assert isinstance(raw.get("profiles"), list)


def test_set_credentials_preserves_extra_keys(cc):
    c, conf, _ = cc
    write(conf, {"profiles": [
        {"name": "edge-a", "host": "https://h", "uuid": "u1", "password": "old",
         "account": "主号"},
    ], "_README": ["别丢我"]})
    c.set_credentials("edge-a", password="new", path=conf, make_preferred=False)
    raw = json.loads(conf.read_text(encoding="utf-8"))
    assert raw["_README"] == ["别丢我"]
    assert raw["profiles"][0]["account"] == "主号"


def test_set_credentials_makes_backup(cc):
    c, conf, tmp_path = cc
    write(conf, {"host": "https://h", "uuid": "u1", "password": "old"})
    c.set_credentials("default", password="new", path=conf)
    baks = list(tmp_path.glob("cookiecloud.bak-*.json"))
    assert baks, "写凭据前必须留备份"


def test_set_credentials_rejects_placeholder(cc):
    c, conf, _ = cc
    write(conf, {"host": "https://h", "uuid": "u1", "password": "old"})
    with pytest.raises(c.CCConfigError) as ei:
        c.set_credentials("default", password="TODO-后填", path=conf)
    assert "没有写入" in str(ei.value)


# ---- 报错要说人话 ---------------------------------------------------------

def test_missing_file_says_what_to_do(cc):
    c, conf, _ = cc
    with pytest.raises(c.CCConfigError) as ei:
        c.select(path=conf)
    assert "怎么办" in str(ei.value)


def test_broken_json_says_what_to_do(cc):
    c, conf, _ = cc
    conf.write_text("{ not json", encoding="utf-8")
    with pytest.raises(c.CCConfigError) as ei:
        c.select(path=conf)
    assert "怎么办" in str(ei.value)


def test_keypass_is_md5_prefix(cc):
    """派生口令必须严格是 md5(uuid-password)[:16]。"""
    import hashlib
    c, conf, _ = cc
    write(conf, {"host": "https://h", "uuid": "abc", "password": "def"})
    got = c.select(path=conf)
    want = hashlib.md5(b"abc-def").hexdigest()[:16]
    assert got.key_pass() == want


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
