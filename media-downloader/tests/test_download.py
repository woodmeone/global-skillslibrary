"""media-downloader skill 离线单元测试。

测试哲学（对抗式审查 + 逆向思维）：
- 断言"必须发生什么"，也断言"绝不能发生什么"（如默认必须 --no-playlist，防误下整站）。
- 覆盖边界：未知质量档位、空 extra_args、模板注入、路径解析。
- 不依赖网络与真实引擎，全部纯函数 + monkeypatch。
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import download as dl  # noqa: E402


# ---------- find_engine ----------

def test_find_engine_env_var(tmp_path, monkeypatch):
    fake = tmp_path / "yt-dlp.exe"
    fake.write_text("x")
    monkeypatch.setenv("MEDIA_DOWNLOADER_YTDLP", str(fake))
    assert dl.find_engine() == str(fake)


def test_find_engine_env_var_missing_raises(tmp_path, monkeypatch):
    monkeypatch.setenv("MEDIA_DOWNLOADER_YTDLP", str(tmp_path / "nope.exe"))
    with pytest.raises(FileNotFoundError):
        dl.find_engine()


def test_find_engine_workspace_bundled(tmp_path, monkeypatch):
    monkeypatch.delenv("MEDIA_DOWNLOADER_YTDLP", raising=False)
    engine = tmp_path / "tools" / "bin" / "yt-dlp.exe"
    engine.parent.mkdir(parents=True)
    engine.write_text("x")
    assert dl.find_engine(workspace=tmp_path) == str(engine)


def test_find_engine_none_raises_with_guidance(tmp_path, monkeypatch):
    monkeypatch.delenv("MEDIA_DOWNLOADER_YTDLP", raising=False)
    monkeypatch.setattr(dl.shutil, "which", lambda _: None)
    with pytest.raises(FileNotFoundError) as ei:
        dl.find_engine(workspace=tmp_path)
    assert "yt-dlp" in str(ei.value)


# ---------- resolve_output_dir ----------

def test_resolve_output_default_uses_workspace(tmp_path):
    out = dl.resolve_output_dir(None, workspace=tmp_path)
    assert out == tmp_path / "media-downloads"


def test_resolve_output_explicit_wins(tmp_path):
    custom = tmp_path / "elsewhere"
    out = dl.resolve_output_dir(custom, workspace=tmp_path)
    assert out == custom


# ---------- build_args ----------

def test_build_args_default_no_playlist():
    args = dl.build_args("http://x/y", output_dir="out")
    assert "--no-playlist" in args  # 逆向：默认必须禁止播放列表
    assert args[-1] == "http://x/y"  # url 永远在最后


def test_build_args_quality_selector():
    assert "bv*[height<=720]+ba/b[height<=720]" in dl.build_args("u", quality="720", output_dir="o")


def test_build_args_unknown_quality_raises():
    with pytest.raises(ValueError):
        dl.build_args("u", quality="4k", output_dir="o")


def test_build_args_audio_extracts_mp3():
    args = dl.build_args("u", quality="audio", output_dir="o")
    assert "--extract-audio" in args and "--audio-format" in args


def test_build_args_playlist_flag_flips():
    args = dl.build_args("u", output_dir="o", playlist=True)
    assert "--no-playlist" not in args


def test_build_args_cookies():
    args = dl.build_args("u", output_dir="o", cookies_from_browser="chrome")
    i = args.index("--cookies-from-browser")
    assert args[i + 1] == "chrome"


def test_build_args_output_template_embeds_dir():
    args = dl.build_args("u", output_dir="D:/dl")
    i = args.index("-o")
    assert args[i + 1].startswith("D:\\dl" if sys.platform == "win32" else "D:/dl")


def test_build_args_extra_appended_before_url():
    args = dl.build_args("u", output_dir="o", extra_args=["--limit-rate", "1M"])
    assert args.index("--limit-rate") < args.index("u")


# ---------- run_download (monkeypatched, no real engine) ----------

def test_run_download_propagates_rc(monkeypatch):
    calls = {}

    def fake_run(cmd, **kw):
        calls["cmd"] = cmd
        return type("P", (), {"returncode": 0})()

    monkeypatch.setattr(dl.subprocess, "run", fake_run)
    rc = dl.run_download("engine", ["-f", "x", "url"])
    assert rc == 0 and calls["cmd"][0] == "engine"


# ---------- print-path 产物扫描（对抗式：中文文件名必须能被 diff 出） ----------

def test_new_files_detects_added(tmp_path):
    a = tmp_path / "旧文件.mp4"
    a.write_bytes(b"x")
    before = dl.snapshot_files(tmp_path)
    b = tmp_path / "【中文】新视频.mp4"  # 中文名 + 方括号
    b.write_bytes(b"y")
    fresh = dl.new_files(before, tmp_path)
    assert b in fresh and a not in fresh


def test_new_files_ignores_temp(tmp_path):
    before = dl.snapshot_files(tmp_path)
    (tmp_path / "v.mp4.part").write_bytes(b"x")
    (tmp_path / "v.mp4").write_bytes(b"y")
    fresh = dl.new_files(before, tmp_path)
    assert [p.name for p in fresh] == ["v.mp4"]


def test_snapshot_records_existing(tmp_path):
    f = tmp_path / "x.txt"
    f.write_bytes(b"x")
    snap = dl.snapshot_files(tmp_path)
    assert f in snap and snap[f] == f.stat().st_mtime


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
