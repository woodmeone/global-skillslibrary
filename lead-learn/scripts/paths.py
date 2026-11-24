"""lead-learn 的路径解析。所有脚本共用这一处。

三个位置互相独立，各由各自的变量控制：

  工作区 HOME       LEAD_LEARN_HOME     默认 ./lead-learn-data
  派单目录 DISPATCH LEAD_LEARN_DISPATCH 默认 见下
  recall 区 RECALL  MIDNIGHT_BASE_DIR   默认 ~/.midnight/recall

**派单目录不与 recall 绑定。** 优先级：

  1. LEAD_LEARN_DISPATCH 显式指定 → 就用它（可以是任何目录）
  2. 设了 LEAD_LEARN_AGENT（派单者的 recall 身份）→
     <RECALL>/<agent>/longterm/dispatch
  3. 都没有 → <HOME>/dispatch

所以没有 recall 也能跑完整个链路，只是派单文件落在工作区里。
"""

from __future__ import annotations

import json
import os
from pathlib import Path

# ---- 工作区 ----
# **不写死任何绝对路径。** 三级解析，从"跟着谁搬家"倒推：
#   1. LEAD_LEARN_HOME        显式指定 → 它就是真理
#   2. 配置文件 ~/.lead-learn/config.json 里的 home → 跨会话持久，换盘只改一处
#   3. 都没设 → Path.cwd()/lead-learn-data  （退化成"在哪跑就在哪建"）
#
# 为什么不给默认值写死个人工作区：那样 skill 一装到别人机器就废，
# 而且公开仓库里带个人路径既泄隐私又不可移植。
def _read_config() -> dict:
    """读用户级配置。没有就当空。"""
    cfg = Path.home() / ".lead-learn" / "config.json"
    if not cfg.exists():
        return {}
    try:
        return json.loads(cfg.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}


_CFG = _read_config()

_env_home = os.environ.get("LEAD_LEARN_HOME", "").strip()
if _env_home:
    HOME = Path(_env_home).expanduser()
elif _CFG.get("home"):
    HOME = Path(_CFG["home"]).expanduser()
else:
    HOME = Path.cwd() / "lead-learn-data"

OUT = HOME / ".favorites-out"
MEDIA = HOME / "media-downloads"
STATE = OUT / "pipeline-state.json"
STAGING = OUT / "longterm-staging"

# ---- recall 记忆区（**可选增强，不是依赖**）----
# 只用来做两件事：核盘面（看各 agent longterm 有没有多文件）、
# 以及在它们的 LONGTERM.md 里留一行指路。**派单文件不进这里。**
_recall_env = os.environ.get("MIDNIGHT_BASE_DIR", "").strip() or _CFG.get("midnight_base_dir", "").strip()
RECALL = Path(_recall_env).expanduser() if _recall_env else Path.home() / ".midnight" / "recall"

# ---- 派单 ----
# **派单落在工作区，跟 recall 无关。**
#
# 2026-11-24 改：原来 AGENT 一设就把 DISPATCH 指到
# `<RECALL>/<agent>/longterm/dispatch`，等于把「过程状态」塞进了「长期记忆」。
# 三个后果：①记忆区不是工作区，语义错位；②记忆区跟 ~/.midnight 搬家、
# 工作区跟盘符搬家，两者时机不同必然错位；③skill 与某个派单者绑死，
# 换个派单者整条链路要重配。
#
# 现在的判据：dispatch / _ledger 是**这轮的待办**，跟素材、state、日志一样
# 属于工作区。记忆区只留 criteria / roster / roundup —— 那些是「下次还要用的判断」。
#
# AGENT 只用于「向哪个 agent 的 LONGTERM.md 登记」和核盘面，不决定落盘位置。
AGENT = os.environ.get("LEAD_LEARN_AGENT", "").strip() or str(_CFG.get("agent") or "").strip()
_env_dispatch = os.environ.get("LEAD_LEARN_DISPATCH", "").strip()
DISPATCH = (Path(_env_dispatch).expanduser() if _env_dispatch
            else HOME / "dispatch")

# ---- cookie 文件 ----
BILI_COOKIES_TXT = OUT / "bilibili-cookies.txt"
BILI_COOKIES_JSON = OUT / "bilibili-cookies.json"
DY_COOKIES_TXT = OUT / "douyin-cookies.txt"
DY_COOKIES_JSON = OUT / "douyin-cookies.json"
CC_CONF = OUT / "cookiecloud.json"

# ---- CookieCloud 用哪份账号 ----
# 多份 profile（一个浏览器一个账号）时，lead-learn 用哪一份。
# 留空 = 由 cc_config 按 cookiecloud.json 里的 preferred:true 决定。
CC_PROFILE = (os.environ.get("LEAD_LEARN_CC_PROFILE", "").strip()
              or str(_CFG.get("cc_profile") or "").strip())

# ---- 收藏数据 ----
BILI_FAV = OUT / "bilibili-latest40.json"
DY_FAV = OUT / "douyin-favorites.json"

# ---- 外部工具 ----
YTDLP = Path(
    os.environ.get(
        "MEDIA_DOWNLOADER_YTDLP",
        os.path.expandvars(r"%APPDATA%\Python\Python313\Scripts\yt-dlp.exe"),
    )
)
FFMPEG = Path(
    os.environ.get(
        "MEDIA_DOWNLOADER_FFMPEG",
        os.path.expandvars(r"%USERPROFILE%\.dsh\tools\ffmpeg\bin\ffmpeg.exe"),
    )
)
FFPROBE = FFMPEG.parent / "ffprobe.exe"

SKILLS = Path.home() / ".dsh" / "skills"
SKILL_DL = SKILLS / "media-downloader" / "scripts" / "download.py"
SKILL_ASR = SKILLS / "asr-subtitle" / "scripts" / "transcribe.py"
SKILL_RECALL = SKILLS / "recall" / "scripts"
STORYBOARD_BIN = (
    Path.home()
    / ".dsh" / "profiles" / "web" / "node_modules"
    / "dsh-video-storyboard" / "bin" / "storyboard.mjs"
)
CHROMIUM = Path(
    os.environ.get(
        "LEAD_LEARN_CHROMIUM",
        os.path.expandvars(
            r"%LOCALAPPDATA%\ms-playwright\chromium-1254\chrome-win64\chrome.exe"
        ),
    )
)

# B站 UID。**必须自己填**，不设默认值——写死谁的 UID 都等于替别人抓收藏夹。
#
# 四级：环境变量 BILI_UID > 按 profile 绑定的 uid > 通用 bili_uid > 空
#
# ⚠ **为什么要按 profile 绑定**（2026-11-24 踩出来的）：
#   一份 cookie = 一个登录账号。cookie 换了账号而 UID 没换，抓的就是
#   **别人的收藏夹**——而且完全不报错，只是内容悄悄变了。
#
# ⚠ **缺 key 时不许回退到通用 bili_uid。**
#   早先的写法是 `_env_uid or _bound_uid or 通用 bili_uid`，于是 cc_profile
#   指向 chrome-b、而 bili_uid_by_profile 里只有 edge-a（漏填/拼错/按老文档
#   配置）时，会**静默退回另一个账号的 UID**——正是本文件要消灭的那个错，
#   换了个入口又回来了。
#
#   现在的判据：只要 cc_profile 有值，就**必须**在 bili_uid_by_profile 里
#   找到对应的 key；找不到就是 BILI_UID = ""，让下游明确报错而不是抓错人。
#   「配错了要吵，不要猜」——和 cc_config 里「不替你挑 profile」同一条原则。
_env_uid = os.environ.get("BILI_UID", "").strip()
_uid_map = _CFG.get("bili_uid_by_profile") or {}
_generic_uid = str(_CFG.get("bili_uid") or "").strip()

if _env_uid:
    BILI_UID = _env_uid
elif CC_PROFILE and isinstance(_uid_map, dict):
    # 绑定了 profile：只认这个 key，缺失即空（不回退 _generic_uid）
    BILI_UID = str(_uid_map.get(CC_PROFILE) or "").strip()
else:
    # 没绑 profile（单账号老配置）：才轮到通用 bili_uid
    BILI_UID = _generic_uid

# 供体检/抓取层诊断用：空值 + 有原因时说明为什么空
BILI_UID_PROBLEM = ""
if not BILI_UID:
    if CC_PROFILE and isinstance(_uid_map, dict) and _uid_map:
        BILI_UID_PROBLEM = (
            f"cc_profile={CC_PROFILE!r} 在 bili_uid_by_profile 里没有对应项"
            f"（已有 {sorted(_uid_map)}）。不回退到通用 bili_uid——"
            f"那会是另一个账号的 UID，抓回来的是别人的收藏夹。"
        )
    elif not _generic_uid:
        BILI_UID_PROBLEM = "没配 bili_uid，也没配 bili_uid_by_profile"

# 每平台每次抓多少条收藏。**唯一出处**，bili_grab3.py 与 favorites.py 都读它。
#
# 为什么从 40 提到 100：窗口只有 40 时，第 41 条以后如果没被新收藏顶上来，
# 就永远学不到。2026-11-24 实测抖音 40 条收藏跨 22 天（约 1.8 条/天），
# 40 条只够 3 周；一旦某周收藏猛增，就会静默漏稿——而漏稿不会有任何报错。
#
# 上限不是越大越好：B站要逐夹翻页（实测 40 条约 60 秒），抖音要滚屏
# （favorites.py 写死最多 8 屏）。100 是"覆盖度"和"抓取耗时"的折中。
FAV_LIMIT = int(os.environ.get("FAV_LIMIT", "100"))


def ensure_dirs() -> None:
    for d in (OUT, MEDIA, STAGING):
        d.mkdir(parents=True, exist_ok=True)
