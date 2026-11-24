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
    """masked() 不许露出密码的任何长度≥2 的连续片段。

    短密码的「尾 4 位」就是全文，而日志会被贴进对话/issue/git。
    这条早先的写法是 `assert "ge" not in s.split("host=")[0]`，
    而 `split("host=")[0]` 恒为 `'default  '`，永远不含 "ge" —— 空洞断言，
    masked() 全量泄露它也照样绿。现在逐段穷举密码的所有 2 字子串。
    """
    c, conf, _ = cc

    def leaks(pw: str) -> str:
        # uuid 故意不用密码里的字母，否则 uuid 前缀与密码撞车会误报
        write(conf, {"host": "https://h", "uuid": "zzzz-9999-yyyy", "password": pw})
        return c.select(path=conf).masked()

    for pw in ("edge", "abcdef", "a<b>C9", "my-pass-2026"):
        s = leaks(pw)
        # 只看密码那一段（`pw=<...>`），别拿 name/host/[preferred] 里的
        # 普通字母当泄露——'ed' 会命中 '[preferred]'，那是误报。
        assert "pw=" in s
        pw_part = s.split("pw=", 1)[1].split("platforms=", 1)[0]
        for i in range(len(pw) - 1):
            frag = pw[i:i + 2]
            assert frag not in pw_part, f"masked() 密码段泄露了 {frag!r}: {pw_part}"

    # 长度要露出来，用来让人判断「有没有抄全」
    assert "4位" in leaks("edge")


# ---- 写回 -----------------------------------------------------------------

def test_set_credentials_updates_and_verifies(cc):
    """改口令：本地回读 + 另一份不受影响 + 非 profile 字段不丢。

    这里关掉 verify_remote（离线）。远端验证本身另有专门的测试。
    """
    c, conf, _ = cc
    write(conf, {"profiles": [
        {"name": "edge-a", "host": "https://h", "uuid": "u1", "password": "old"},
        {"name": "chrome-b", "host": "https://h", "uuid": "u2", "password": "old2",
         "preferred": True},
    ]})
    got = c.set_credentials("edge-a", password="new", path=conf,
                            make_preferred=False, verify_remote=False)
    assert got.password == "new"
    # 回读确实落盘
    back = c.select("edge-a", path=conf)
    assert back.password == "new"
    # 另一份没被动
    assert c.select("chrome-b", path=conf).password == "old2"
    # _README 之类的非 profile 字段不能被写没
    raw = json.loads(conf.read_text(encoding="utf-8"))
    assert isinstance(raw.get("profiles"), list)
    # 临时文件不许残留
    assert not list(conf.parent.glob("*.tmp"))


def test_set_credentials_preserves_extra_keys(cc):
    c, conf, _ = cc
    write(conf, {"profiles": [
        {"name": "edge-a", "host": "https://h", "uuid": "u1", "password": "old",
         "account": "主号"},
    ], "_README": ["别丢我"]})
    c.set_credentials("edge-a", password="new", path=conf,
                      make_preferred=False, verify_remote=False)
    raw = json.loads(conf.read_text(encoding="utf-8"))
    assert raw["_README"] == ["别丢我"]
    assert raw["profiles"][0]["account"] == "主号"


def test_flat_writeback_keeps_extra_keys(cc):
    """扁平格式写回不许丢字段。

    早先白名单只留 account，platforms / _note 读写一轮就静默消失。
    """
    c, conf, _ = cc
    write(conf, {"host": "https://h", "uuid": "u1", "password": "old",
                 "platforms": ["bili", "dy"], "_note": "别丢我"})
    c.set_credentials("default", password="new", path=conf, verify_remote=False)
    raw = json.loads(conf.read_text(encoding="utf-8"))
    assert raw["platforms"] == ["bili", "dy"], "platforms 被写没了"
    assert raw["_note"] == "别丢我"
    assert raw["password"] == "new"


def test_set_credentials_makes_backup(cc):
    c, conf, tmp_path = cc
    write(conf, {"host": "https://h", "uuid": "u1", "password": "old"})
    c.set_credentials("default", password="new", path=conf, verify_remote=False)
    baks = list(tmp_path.glob("cookiecloud.bak-*.json"))
    assert baks, "写凭据前必须留备份"


def test_set_credentials_rejects_placeholder(cc):
    c, conf, _ = cc
    write(conf, {"host": "https://h", "uuid": "u1", "password": "old"})
    with pytest.raises(c.CCConfigError) as ei:
        c.set_credentials("default", password="TODO-后填", path=conf,
                          verify_remote=False)
    assert "没有写入" in str(ei.value)
    # 原文件不能被写脏
    assert json.loads(conf.read_text(encoding="utf-8"))["password"] == "old"


def test_duplicate_names_rejected_before_write(cc):
    """同名 profile 必须在读入时就拦，不许等到写盘之后。

    放过去的后果（实测过）：set_credentials 按名字把所有同名项都置
    preferred=True → 写盘 → 之后任何 select() 都报「2 份都标了 preferred」，
    用户只能手改文件。
    """
    c, conf, _ = cc
    write(conf, {"profiles": [
        {"name": "dup", "host": "https://h", "uuid": "AAAA1111", "password": "p1"},
        {"name": "dup", "host": "https://h", "uuid": "BBBB2222", "password": "p2"},
    ]})
    with pytest.raises(c.CCConfigError) as ei:
        c.load_profiles(conf)
    assert "重名" in str(ei.value)


def test_preferred_must_be_json_true(cc):
    """`"preferred": "false"`（字符串）不许被当成 True。

    手写 JSON 里这错误极常见，而 bool("false") == True。
    """
    c, conf, _ = cc
    write(conf, {"profiles": [
        {"name": "a", "host": "https://h", "uuid": "u1", "password": "p1"},
        {"name": "b", "host": "https://h", "uuid": "u2", "password": "p2",
         "preferred": "false"},
    ]})
    # 两份都不算 preferred → 报「不替你挑」，而不是选中 b
    with pytest.raises(c.CCConfigError) as ei:
        c.select(path=conf)
    assert "不替你挑" in str(ei.value)


def test_root_not_object_gives_ccerror(cc):
    """根节点是数组/null 时给 CCConfigError，不是 AttributeError。"""
    c, conf, _ = cc
    for bad in ("[1,2,3]", "null", '"str"'):
        conf.write_text(bad, encoding="utf-8")
        with pytest.raises(c.CCConfigError):
            c.load_profiles(conf)


def test_host_placeholder_rejected(cc):
    """host 还是模板占位值时必须拦住。

    否则 health/cc_fetch 会拿 https://<your-domain> 去请求，
    然后被误诊成「服务端挂了」。
    """
    c, conf, _ = cc
    write(conf, {"host": "https://<your-domain>", "uuid": "realuuid",
                 "password": "realpass"})
    with pytest.raises(c.CCConfigError) as ei:
        c.select(path=conf)
    assert "占位" in str(ei.value)


def test_host_without_scheme_rejected(cc):
    c, conf, _ = cc
    write(conf, {"host": "cc.example", "uuid": "u", "password": "p"})
    with pytest.raises(c.CCConfigError) as ei:
        c.select(path=conf)
    assert "http://" in str(ei.value)


def test_placeholder_matching_is_prefix_not_substring(cc):
    """合法密码里含 '<' 或 'todo' 不许被误伤。

    子串匹配实测会把 `a<b>C9!xyz`、`PassTODOword9` 判成「没填」，
    而它们完全合法——和「不校验 uuid 形状」是同一条教训。
    """
    c, conf, _ = cc
    for pw in ("a<b>C9!xyz", "PassTODOword9", "my-todo-list"):
        write(conf, {"host": "https://h", "uuid": "realuuid", "password": pw})
        got = c.select(path=conf)      # 不抛错
        assert got.password == pw


def test_safe_uuid_never_leaks_any_char(cc):
    """safe_uuid() 一个字都不给，只给长度。

    uuid 是服务端路径键（/get/<uuid>），泄露前缀等于缩小爆破空间；
    而日志会被贴进对话/issue/git。区分「哪份 profile」靠 name，不靠 uuid。
    """
    c, conf, _ = cc
    # 测试 uuid 里避开数字，否则「长度」那几个数字会和 uuid 片段撞车
    for u in ("abc-def", "abcdwxyz", "pqrstuvw", "abcdefgh-ijkl-mnop-qrst"):
        p = c.Profile(name="t", host="https://h", uuid=u, password="secret")
        s = p.safe_uuid()
        # 任何长度 ≥2 的连续片段都不许出现
        for i in range(len(u) - 1):
            assert u[i:i + 2] not in s, f"safe_uuid 泄露了 {u[i:i+2]!r}: {s}"
        assert u not in s
        assert "位" in s, "要给出长度，方便判断有没有抄全"
        assert u not in p.masked()


# ---- 远端验证（set_credentials 的 verify_remote）--------------------------

def test_verify_remote_rejects_wrong_password(cc, monkeypatch):
    """新口令解不开服务端 → 必须拒绝写入，原文件不动。"""
    c, conf, tmp_path = cc
    write(conf, {"host": "https://h", "uuid": "u1", "password": "good"})
    before = conf.read_text(encoding="utf-8")

    import cc_crypto

    def boom(host, uuid, password, timeout=30):
        raise PermissionError("解密失败：password 与上传时用的不一致")
    monkeypatch.setattr(cc_crypto, "fetch_payload", boom)

    with pytest.raises(c.CCConfigError) as ei:
        c.set_credentials("default", password="wrong", path=conf)
    assert "解不开" in str(ei.value) or "没有写入" in str(ei.value)
    assert conf.read_text(encoding="utf-8") == before, "失败时原文件被改了"


def test_verify_remote_accepts_correct_password(cc, monkeypatch):
    c, conf, tmp_path = cc
    write(conf, {"host": "https://h", "uuid": "u1", "password": "old"})

    import cc_crypto
    monkeypatch.setattr(
        cc_crypto, "fetch_payload",
        lambda host, uuid, password, timeout=30: {
            "cookie_data": {"bilibili": [1, 2, 3]}, "local_storage_data": {}})

    got = c.set_credentials("default", password="new", path=conf)
    assert got.password == "new"


def test_verify_remote_404_is_refused(cc, monkeypatch):
    """服务端 404（还没同步过）也要拒绝写入并说明怎么办。"""
    c, conf, _ = cc
    write(conf, {"host": "https://h", "uuid": "u1", "password": "old"})
    before = conf.read_text(encoding="utf-8")

    import cc_crypto

    def nf(host, uuid, password, timeout=30):
        raise LookupError("服务端没有这个 uuid 的数据（404）")
    monkeypatch.setattr(cc_crypto, "fetch_payload", nf)

    with pytest.raises(c.CCConfigError) as ei:
        c.set_credentials("default", password="new", path=conf)
    assert "没有写入" in str(ei.value)
    assert conf.read_text(encoding="utf-8") == before


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
