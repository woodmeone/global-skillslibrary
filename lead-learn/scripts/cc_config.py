"""CookieCloud 凭据的唯一解析入口。

为什么需要单独一层：

    2026-11-24 用户手工把 cookiecloud.json 升级成 `profiles` 数组（一份 profile =
    一个浏览器 = 一个账号），但当时所有读凭据的脚本还在按扁平结构取 conf["host"]，
    于是 `cc_fetch.py show`、`health.py` 全部 KeyError 崩在第一个字段上。

    根因不是格式变了，是**凭据结构散落在三个脚本里各读一遍**。现在收敛到这里：
    谁要凭据都调 select()，格式怎么变只改这一个文件。

两种写法都认（读侧兼容，写侧统一写 profiles）：

    扁平（旧）                        profiles（新）
    {                                 {
      "host": "...",                    "profiles": [
      "uuid": "...",                      {"name": "edge-a", "host": "...",
      "password": "..."                     "uuid": "...", "password": "...",
    }                                       "platforms": ["bili"], "preferred": true}
                                        ]
                                      }

选哪一份的优先级：显式 name > preferred: true > 只有一份就用它 > 报错。

**不猜。** 多份都没有 preferred 时宁可报错列出候选，也不替用户挑一个——
挑错了就是拿 A 账号的 cookie 去抓 B 账号的收藏夹，静默污染，事后无从察觉。
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

from paths import CC_CONF

# ⚠ **不要校验 uuid 的形状。**
#
# 2026-11-24 踩过：初版按「36 位标准 UUID」写死了正则，结果用户第二份 profile
# 的自定义 uuid（扩展里可以任意填的短字符串）被判成「格式不对」直接拦下。
# 实测那个 uuid 在服务端返回 200 + 605 KB 真实数据、解密后是完好的
# bilibili + douyin cookie——**它是合法的，是校验错了**。
#
# （真实 uuid 是账号凭据，不入库。这里只记形状：20 字符左右的 base64 风格串。）
#
# CookieCloud 服务端只把 uuid 当目录名，查不到就 404，不挑形状。
# 所以这里只判「有没有填」，形状交给服务端回答（404 就是没同步过）。
# 占位值。填了这些等于没填，必须当「未配置」处理而不是拿去请求服务端。
_PLACEHOLDER_HINTS = ("todo", "填这里", "changeme", "your-", "<", "占位")

# 「可疑形状」——只提醒，不拦。
_LOOKS_STANDARD_UUID = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}"
    r"-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)


class CCConfigError(RuntimeError):
    """凭据配不对时抛这个。消息里必须包含「怎么办」，调用方直接打印给用户。"""


@dataclass
class Profile:
    name: str
    host: str
    uuid: str
    password: str
    account: str = ""
    platforms: list[str] = field(default_factory=list)
    preferred: bool = False

    # --- 判定 ---------------------------------------------------------------

    def is_filled(self) -> bool:
        """uuid/password 都是真值，不是占位符。"""
        for v in (self.uuid, self.password):
            low = (v or "").strip().lower()
            if not low:
                return False
            if any(h in low for h in _PLACEHOLDER_HINTS):
                return False
        return True

    def problems(self) -> list[str]:
        """返回这份 profile 的【致命】毛病，空列表表示可用。

        只判「填没填」，**不判形状**。理由见本文件顶部 _LOOKS_STANDARD_UUID 的注释：
        服务端把 uuid 当目录名，什么形状都收，拦住合法值是纯误伤。
        """
        out: list[str] = []
        if not self.host.strip():
            out.append("缺 host（服务器地址，形如 https://cc.example.com）")
        if not self.is_filled():
            out.append("uuid / password 还是占位值，没填真凭据")
        return out

    def warnings(self) -> list[str]:
        """非致命提醒。不拦执行，只说明「这看着不太常见」。"""
        out: list[str] = []
        u = self.uuid.strip()
        if u and not _LOOKS_STANDARD_UUID.match(u):
            out.append(f"uuid 不是标准 UUID 形状（{u[:10]}…）——合法，只是不常见")
        return out

    # --- 派生 ---------------------------------------------------------------

    def key_pass(self) -> str:
        """CookieCloud 的 AES 口令：md5(uuid-password)[:16]。"""
        raw = f"{self.uuid}-{self.password}"
        return hashlib.md5(raw.encode()).hexdigest()[:16]

    def masked(self) -> str:
        """给人看的一行。**不露任何密码字符**。

        哪怕只是尾 4 位也不露：短密码（比如 "edge"）的尾 4 位就是全文，
        而日志会被贴进对话、写进 issue、进 git —— 那就是泄露。
        uuid 同样只留「能区分是谁」的最短前缀。
        """
        uid = self.uuid or ""
        return (f"{self.name}  host={self.host}  "
                f"uuid={uid[:8]}…  "
                f"pw=<{len(self.password)}位，已隐去>  "
                f"platforms={','.join(self.platforms) or '-'}"
                f"{'  [preferred]' if self.preferred else ''}")

    def as_dict(self) -> dict:
        d = {
            "name": self.name,
            "host": self.host,
            "uuid": self.uuid,
            "password": self.password,
        }
        if self.account:
            d["account"] = self.account
        if self.platforms:
            d["platforms"] = list(self.platforms)
        d["preferred"] = self.preferred
        return d


# ---- 读 -------------------------------------------------------------------

def _raw(path: Path | None = None) -> dict:
    p = Path(path) if path else CC_CONF
    if not p.exists():
        raise CCConfigError(
            f"没有凭据文件：{p}\n"
            f"  怎么办：照 references/cookiecloud.md 里的模板建一份，填 host/uuid/password。"
        )
    try:
        # PowerShell 写的 JSON 带 BOM，必须 utf-8-sig
        return json.loads(p.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise CCConfigError(
            f"凭据文件不是合法 JSON：{p}\n"
            f"  {exc}\n"
            f"  怎么办：检查是不是少逗号/多了尾逗号；也可以从 "
            f"cookiecloud.bak-*.json 恢复。"
        ) from exc


def _from_flat(raw: dict) -> list[Profile]:
    return [Profile(
        name="default",
        host=str(raw.get("host") or ""),
        uuid=str(raw.get("uuid") or ""),
        password=str(raw.get("password") or ""),
        account=str(raw.get("account") or ""),
        platforms=list(raw.get("platforms") or []),
        preferred=True,   # 扁平格式只有一份，天然就是默认
    )]


def load_profiles(path: Path | None = None) -> list[Profile]:
    """读全部 profile。两种格式都认，顺序即文件里的顺序。"""
    raw = _raw(path)
    if isinstance(raw.get("profiles"), list):
        out: list[Profile] = []
        for i, item in enumerate(raw["profiles"]):
            if not isinstance(item, dict):
                continue
            out.append(Profile(
                name=str(item.get("name") or f"profile-{i}"),
                host=str(item.get("host") or ""),
                uuid=str(item.get("uuid") or ""),
                password=str(item.get("password") or ""),
                account=str(item.get("account") or ""),
                platforms=[str(x) for x in (item.get("platforms") or [])],
                preferred=bool(item.get("preferred")),
            ))
        if not out:
            raise CCConfigError(
                f"{path or CC_CONF} 里 profiles 是空数组。\n"
                f"  怎么办：至少填一份，或改回扁平写法 {{host,uuid,password}}。"
            )
        return out
    # 扁平旧格式
    if raw.get("uuid") or raw.get("host"):
        return _from_flat(raw)
    raise CCConfigError(
        f"{path or CC_CONF} 既没有 profiles 数组，也没有 host/uuid 字段。\n"
        f"  怎么办：看 references/cookiecloud.md 的模板重写一份。"
    )


def select(name: str | None = None, path: Path | None = None) -> Profile:
    """挑一份可用的 profile。

    优先级：显式 name > 环境变量 LEAD_LEARN_CC_PROFILE > paths.CC_PROFILE
            > preferred:true > 唯一一份 > 报错（绝不替你猜）。

    选中的那份如果有毛病（占位符没填），这里就抛错，
    **不要让它带着半成品凭据去请求服务端**——那样只会拿到 404，
    然后被误判成「服务端挂了」。
    """
    profiles = load_profiles(path)
    want = (name or os.environ.get("LEAD_LEARN_CC_PROFILE", "")).strip()

    if not want:
        # 第二来源：用户级配置里的 cc_profile（paths.py 已解析好）
        try:
            import paths
            want = (getattr(paths, "CC_PROFILE", "") or "").strip()
        except Exception:
            want = ""

    if want:
        for p in profiles:
            if p.name == want:
                chosen = p
                break
        else:
            raise CCConfigError(
                f"没有名为 {want!r} 的 profile。现有：{[p.name for p in profiles]}\n"
                f"  怎么办：确认名字拼写，或去掉 --profile 参数。"
            )
    else:
        preferred = [p for p in profiles if p.preferred]
        if len(preferred) == 1:
            chosen = preferred[0]
        elif len(preferred) > 1:
            raise CCConfigError(
                f"有 {len(preferred)} 份 profile 都标了 preferred: "
                f"{[p.name for p in preferred]}\n"
                f"  怎么办：只留一份 true，或显式指定 --profile <名字>。"
            )
        elif len(profiles) == 1:
            chosen = profiles[0]
        else:
            raise CCConfigError(
                f"有 {len(profiles)} 份 profile 但都没有 preferred: true："
                f"{[p.name for p in profiles]}\n"
                f"  怎么办：给要用的那份加 \"preferred\": true，或显式指定 --profile <名字>。\n"
                f"  不替你挑：选错了就是拿 A 账号的 cookie 抓 B 账号的收藏夹，静默污染。"
            )

    probs = chosen.problems()
    if probs:
        detail = "\n".join(f"  - {x}" for x in probs)
        raise CCConfigError(
            f"profile {chosen.name!r} 还不能用：\n{detail}\n"
            f"  怎么办：改 {path or CC_CONF} 里这份的字段；"
            f"uuid/password 在浏览器 CookieCloud 扩展的设置页里能看到或生成。"
        )
    return chosen


def check_bili_uid_binding(profile: Profile | None = None) -> list[str]:
    """检查【cookie 账号】与【B站 UID】是不是同一个账号。

    这是最阴的一类错：两者都是合法值，配错了哪儿都不报错，
    只是抓回来的收藏夹悄悄换了个人。所以拉到 cookie 之后主动核对一次
    cookie 里的 DedeUserID 与 paths.BILI_UID 是否一致。

    返回警告列表（不抛错——不确定时只提醒，因为有些 cookie 确实没有
    DedeUserID，那是未登录态）。
    """
    warns: list[str] = []
    try:
        import paths
    except Exception:
        return warns

    want = (getattr(paths, "BILI_UID", "") or "").strip()
    if not want:
        warns.append(
            "没配 BILI_UID —— 抓 B站收藏夹会失败。\n"
            "      怎么办：~/.lead-learn/config.json 里填 bili_uid_by_profile"
        )
        return warns

    # 显式 profile 与 paths.CC_PROFILE 不一致时，UID 绑定必然对不上，
    # 提前说清楚，省得抓到别人收藏夹还以为正常
    if profile is not None:
        try:
            bound = getattr(paths, "CC_PROFILE", "") or ""
        except Exception:
            bound = ""
        if bound and bound != profile.name:
            warns.append(
                f"显式指定了 profile={profile.name}，但 UID 绑定按 cc_profile={bound} 解析"
                f"（BILI_UID={want}）。\n"
                f"      如果 {profile.name} 是另一个账号，抓到的会是错人的收藏夹。\n"
                f"      怎么办：要么去掉 --profile，要么同时设 BILI_UID 环境变量。"
            )
    return warns


def summary(path: Path | None = None) -> str:
    """体检用：所有 profile 的状态一览，不抛错。"""
    try:
        profiles = load_profiles(path)
    except CCConfigError as exc:
        return f"读不了凭据：{exc}"
    lines = []
    for p in profiles:
        probs = p.problems()
        mark = "✓" if not probs else "✗"
        lines.append(f"  {mark} {p.masked()}")
        for x in probs:
            lines.append(f"      - {x}")
        for x in p.warnings():
            lines.append(f"      · {x}")
    return "\n".join(lines)


# ---- 写 -------------------------------------------------------------------

def set_credentials(
    name: str,
    *,
    uuid: str | None = None,
    password: str | None = None,
    host: str | None = None,
    path: Path | None = None,
    make_preferred: bool = True,
) -> Profile:
    """改某份 profile 的凭据，写回原文件，保留其余字段与注释。

    只动传进来的字段；传 None 的一律保持不变。写完立刻回读校验，
    避免「写进去一个空格」这种事后才发现的问题。

    写之前备份一份带时间戳的 .bak，凭据写错就靠它。
    """
    p = Path(path) if path else CC_CONF
    raw = _raw(p)
    profiles = load_profiles(p)

    target = next((x for x in profiles if x.name == name), None)
    if target is None:
        raise CCConfigError(
            f"没有名为 {name!r} 的 profile。现有：{[x.name for x in profiles]}\n"
            f"  怎么办：先手工在 {p} 里加一条，或把 name 写对。"
        )

    if uuid is not None:
        target.uuid = uuid.strip()
    if password is not None:
        target.password = password.strip()
    if host is not None:
        target.host = host.strip().rstrip("/")

    probs = target.problems()
    if probs:
        raise CCConfigError(
            f"改完仍然不可用，**没有写入**：\n" + "\n".join(f"  - {x}" for x in probs) +
            "\n  怎么办：uuid/password 抄扩展设置页里的原值，一字不差（形状不限）。"
        )

    if make_preferred:
        for x in profiles:
            x.preferred = (x.name == name)
        target.preferred = True

    # 备份
    if p.exists():
        import time
        bak = p.with_name(f"{p.stem}.bak-{time.strftime('%Y%m%d-%H%M%S')}{p.suffix}")
        bak.write_text(p.read_text(encoding="utf-8-sig"), encoding="utf-8")

    if isinstance(raw.get("profiles"), list):
        # 保住 _README / _说明 这类非 profile 字段，只替换 profiles 数组
        raw["profiles"] = [x.as_dict() for x in profiles]
    else:
        # 扁平格式：退化成单 profile，仍写成扁平，免得老脚本看不懂
        one = profiles[0]
        raw = {k: v for k, v in raw.items() if k in ("account",)}
        raw.update({
            "host": one.host,
            "uuid": one.uuid,
            "password": one.password,
        })
        if one.account:
            raw["account"] = one.account

    p.write_text(json.dumps(raw, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # 回读校验
    back = select(name, path=p)
    if back.uuid != target.uuid or back.password != target.password:
        raise CCConfigError(f"写回后回读不一致，检查 {p}")
    return back


if __name__ == "__main__":
    import sys

    if len(sys.argv) >= 2 and sys.argv[1] == "show":
        print(f"凭据文件：{CC_CONF}")
        print(summary())
        try:
            got = select()
            print(f"\n默认使用：{got.name}")
        except CCConfigError as e:
            print(f"\n⚠ {e}")
    else:
        print(__doc__)
        sys.exit(64)
