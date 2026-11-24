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
#
# ⚠ **只匹配前缀，不做子串匹配。**
# 子串匹配会把合法凭据误伤成「没填」：实测 `a<b>C9!xyz`、`PassTODOword9`
# 都被拦下，而它们是完全合法的密码。这和「不校验 uuid 形状」是同一条教训
# ——校验越狠，误伤越重。占位值有它的固定长相（模板抄下来没改），
# 所以只在前缀上认。
_PLACEHOLDER_PREFIXES = (
    "todo",          # TODO-在Chrome扩展里生成后填这里
    "<your",         # <your-domain> / <你的域名>
    "<你的",
    "填这里",
    "changeme",
    "your-",
    "<",             # 任何以尖括号开头的都是模板残渣
    "占位",
)

# host 里不该出现的东西——出现即说明还是模板原样。
#
# 只放「抄模板留下的残渣」，不放 example.com：本文件的示例文案与文档
# 都用 `https://cc.example.com` 举形状，把它判成占位就等于自己的示例不可用。
# 模板里真正会残留的是尖括号包着的 `<your-domain>`，那个由 `<` / `>` 兜住。
_HOST_PLACEHOLDER_HINTS = ("<", ">", "your-domain", "你的域名")

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
        """uuid/password 都填了真值，不是模板残渣。

        只认前缀（见 _PLACEHOLDER_PREFIXES 的注释），
        免得密码里恰好含 `<` 或 `todo` 就永远存不进去。
        """
        for v in (self.uuid, self.password):
            low = (v or "").strip().lower()
            if not low:
                return False
            if low.startswith(_PLACEHOLDER_PREFIXES):
                return False
        return True

    def host_problem(self) -> str:
        """host 的毛病，空字符串表示没问题。

        **host 也参与占位判定。** 早先只查了 uuid/password，于是把文档模板
        原样抄下来（host 还是 `https://<your-domain>`）、只填了 uuid/password
        的配置会被判定为「已配置」，然后拿这个不存在的域名去请求，
        最后被误诊成「服务端挂了」。
        """
        h = (self.host or "").strip()
        if not h:
            return "缺 host（服务器地址，形如 https://cc.example.com）"
        low = h.lower()
        if any(k in low for k in _HOST_PLACEHOLDER_HINTS):
            return f"host 还是模板占位值（{h}），要填真实服务器地址"
        if "://" not in h:
            return f"host 要以 http:// 或 https:// 开头（当前 {h}）"
        return ""

    def problems(self) -> list[str]:
        """返回这份 profile 的【致命】毛病，空列表表示可用。

        只判「填没填」，**不判形状**。理由见本文件顶部 _LOOKS_STANDARD_UUID 的注释：
        服务端把 uuid 当目录名，什么形状都收，拦住合法值是纯误伤。
        """
        out: list[str] = []
        hp = self.host_problem()
        if hp:
            out.append(hp)
        if not self.is_filled():
            out.append("uuid / password 还是占位值，没填真凭据")
        return out

    def warnings(self) -> list[str]:
        """非致命提醒。不拦执行，只说明「这看着不太常见」。

        **不打 uuid 片段**：短 uuid 的前几位可能就是全文。
        只给长度——和 masked() 同一口径。
        """
        out: list[str] = []
        u = self.uuid.strip()
        if u and not _LOOKS_STANDARD_UUID.match(u):
            out.append(f"uuid 不是标准 UUID 形状（{len(u)} 位）——合法，只是不常见")
        return out

    # --- 派生 ---------------------------------------------------------------

    def key_pass(self) -> str:
        """CookieCloud 的 AES 口令：md5(uuid-password)[:16]。"""
        raw = f"{self.uuid}-{self.password}"
        return hashlib.md5(raw.encode()).hexdigest()[:16]

    def safe_uuid(self) -> str:
        """可以进日志的 uuid 形式。**任何脚本要打 uuid 都用这个。**

        规则：**只给长度，一个字符都不给。**

        为什么连「前 6 位」也不给：uuid 是 CookieCloud 的账号键（服务端路径
        就是 `/get/<uuid>`），泄露前缀等于缩小爆破空间；而日志会被贴进对话、
        issue、git。6 位对「区分是哪份 profile」没有帮助——`masked()` 已经
        打了 profile 名字，那才是给人区分的字段。

        收敛成一个方法，是因为 `uid[:8]` 这种写法散在各处时总有地方会漏。
        """
        u = (self.uuid or "").strip()
        if not u:
            return "<未填>"
        return f"<{len(u)}位，已隐去>"

    def masked(self) -> str:
        """给人看的一行。**不露密码或 uuid 的任何可用字符**。

        哪怕只是尾 4 位也不露：短密码（比如 "edge"）的尾 4 位就是全文，
        而日志会被贴进对话、写进 issue、进 git —— 那就是泄露。
        """
        return (f"{self.name}  host={self.host}  "
                f"uuid={self.safe_uuid()}  "
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
        data = json.loads(p.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise CCConfigError(
            f"凭据文件不是合法 JSON：{p}\n"
            f"  {exc}\n"
            f"  怎么办：检查是不是少逗号/多了尾逗号；也可以从 "
            f"cookiecloud.bak-*.json 恢复。"
        ) from exc
    # 根节点必须是对象。否则后面 raw.get(...) 会抛 AttributeError，
    # 而 cc_fetch.main() 只捕 CCConfigError/RuntimeError，用户看到的是裸 traceback。
    if not isinstance(data, dict):
        raise CCConfigError(
            f"凭据文件根节点必须是 JSON 对象，实际是 {type(data).__name__}：{p}\n"
            f"  怎么办：检查文件是不是被写成了数组或 null；"
            f"可以从 cookiecloud.bak-*.json 恢复。"
        )
    return data


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
        skipped = 0
        for i, item in enumerate(raw["profiles"]):
            if not isinstance(item, dict):
                skipped += 1
                continue
            # preferred 只认 JSON 的 true。`"false"`（字符串）是手写配置里
            # 极常见的错误，bool("false") == True 会把它当成默认账号选中。
            out.append(Profile(
                name=str(item.get("name") or f"profile-{i}"),
                host=str(item.get("host") or ""),
                uuid=str(item.get("uuid") or ""),
                password=str(item.get("password") or ""),
                account=str(item.get("account") or ""),
                platforms=[str(x) for x in (item.get("platforms") or [])],
                preferred=item.get("preferred") is True,
            ))
        if not out:
            hint = f"（其中 {skipped} 项不是对象，已跳过）" if skipped else ""
            raise CCConfigError(
                f"{path or CC_CONF} 里 profiles 是空数组{hint}。\n"
                f"  怎么办：至少填一份，或改回扁平写法 {{host,uuid,password}}。"
            )
        # 重名必须拦。放过去会怎样：set_credentials 按名字把所有同名项都置
        # preferred=True → 写盘 → 之后任何 select() 都报「2 份都标了 preferred」，
        # 用户从此只能手改文件。篡改发生在写盘之后，是真实的「写坏配置」路径。
        names = [p.name for p in out]
        dups = sorted({n for n in names if names.count(n) > 1})
        if dups:
            raise CCConfigError(
                f"{path or CC_CONF} 里有重名 profile：{dups}\n"
                f"  怎么办：给每个 name 起唯一的名字。"
                f"（重名会让 preferred 同时命中多份，配置直接不可用）"
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

    # 环境变量给了名字，但它不在**这次指定的文件**里 → 不要静默忽略，
    # 也不要当成「文件坏了」。这是两处配置打架，必须说清楚。
    if want and not any(p.name == want for p in profiles):
        raise CCConfigError(
            f"环境变量 LEAD_LEARN_CC_PROFILE={want!r}，但 "
            f"{path or CC_CONF} 里没有这个名字。现有：{[p.name for p in profiles]}\n"
            f"  怎么办：把两处改成一致，或清掉这个环境变量。"
        )

    if not want:
        # 第二来源：用户级配置里的 cc_profile（paths.py 已解析好）。
        # 只在没显式传 path 时才看它——传了 path 就是在问「按这个文件选」，
        # 再掺进用户配置里的 cc_profile 会让「读另一份文件」的调用直接报错。
        if path is None:
            try:
                import paths
                want = (getattr(paths, "CC_PROFILE", "") or "").strip()
            except Exception:
                want = ""
            if want and not any(p.name == want for p in profiles):
                raise CCConfigError(
                    f"~/.lead-learn/config.json 的 cc_profile={want!r}，但 "
                    f"{CC_CONF} 里没有这个名字。现有：{[p.name for p in profiles]}\n"
                    f"  怎么办：把 cc_profile 改成现存的某个名字，或补上那份 profile。"
                )

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
    verify_remote: bool = True,
) -> Profile:
    """改某份 profile 的凭据，写回原文件，保留其余字段与注释。

    只动传进来的字段；传 None 的一律保持不变。

    写盘前做两道验证，任一不过就**一个字节都不写**：
      1. 本地：字段不为占位值、host 形状像样（`problems()`）
      2. 远端：新口令真能解开服务端那份密文（`_verify_remote`）
         —— 因为「语法合法的错口令」本地查不出来，而它会在下次抓取时才炸

    写盘方式：先写 `.tmp` → 回读校验 → `os.replace` 原子替换。
    原文件始终是完整可用的旧版本，直到新内容确认无误。

    替换前备份一份带时间戳的 `.bak`。

    verify_remote=False 用于离线改配置或测试；生产路径不要关掉它。
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

    # ---- 服务端预验证：新口令真能解开服务端那份密文吗？----
    #
    # 只有「本地回读一致」是不够的：把一个语法合法、但服务端解不开的口令写进
    # 配置，函数会返回成功，而用户下次抓取时才炸——那正是 Issue 背景第 4 条
    # （改密码后旧配置解不开）发生的场景。所以在落盘前先探一次。
    #
    # 做成可选：verify_remote=False 时不联网（测试/离线改配置用），
    # 但**默认必须验证**——凭据写错是静默故障，代价远大于一次 GET。
    remote_note = ""
    if verify_remote:
        remote_note = _verify_remote(target)

    if make_preferred:
        for x in profiles:
            x.preferred = (x.name == name)
        target.preferred = True

    if isinstance(raw.get("profiles"), list):
        # 保住 _README / _说明 这类非 profile 字段，只替换 profiles 数组
        raw["profiles"] = [x.as_dict() for x in profiles]
    else:
        # 扁平格式：退化成单 profile，仍写成扁平，免得老脚本看不懂。
        # **保留原有全部键**，只覆盖这三个——早先用白名单只留 account，
        # 结果 platforms/_note 等字段读写一轮就静默消失。
        raw["host"] = profiles[0].host
        raw["uuid"] = profiles[0].uuid
        raw["password"] = profiles[0].password
        if profiles[0].account:
            raw["account"] = profiles[0].account

    new_text = json.dumps(raw, ensure_ascii=False, indent=2) + "\n"

    # ---- 先写临时文件并校验，通过了才原子替换 ----
    #
    # 早先是「直接写盘 → 回读 → 不一致再抛错」，可那时盘已经被写脏了。
    # 典型触发：同名 profile 让 preferred 同时命中多份，写盘后 select() 永久报错。
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(new_text, encoding="utf-8")
    try:
        back = select(name, path=tmp)
        if back.uuid != target.uuid or back.password != target.password:
            raise CCConfigError(f"临时文件回读不一致，未替换原文件：{p}")
    except CCConfigError:
        tmp.unlink(missing_ok=True)
        raise

    # 备份（在确认新内容可用之后才动原文件）
    if p.exists():
        import time
        bak = p.with_name(f"{p.stem}.bak-{time.strftime('%Y%m%d-%H%M%S')}{p.suffix}")
        bak.write_text(p.read_text(encoding="utf-8-sig"), encoding="utf-8")

    os.replace(tmp, p)
    if remote_note:
        print(f"  {remote_note}")
    return select(name, path=p)


def _verify_remote(prof: Profile) -> str:
    """确认 prof 的凭据能解开服务端数据。返回一句人话说明结果。

    失败就抛错——**不允许**把解不开的凭据写进配置。
    """
    import cc_crypto

    try:
        payload = cc_crypto.fetch_payload(prof.host, prof.uuid, prof.password)
    except LookupError as exc:
        # 404 / 无 encrypted：服务端还没有这个 uuid 的数据。
        # 这不代表凭据错了（新账号首次配置就是这种状态），放行但明说。
        raise CCConfigError(
            f"无法在服务端验证新凭据，**没有写入**：\n  {exc}\n"
            f"  如果这是刚建的新账号，先在扩展里同步一次，再改配置。"
        ) from None
    except PermissionError as exc:
        raise CCConfigError(
            f"新口令解不开服务端数据，**没有写入**：\n  {exc}\n"
            f"  配置里的旧值没动，可以从 cookiecloud.bak-*.json 对照。"
        ) from None
    except Exception as exc:
        raise CCConfigError(
            f"连不上服务端，**没有写入**：{type(exc).__name__}: {str(exc)[:120]}\n"
            f"  怎么办：确认网络/代理，或显式传 verify_remote=False 跳过验证。"
        ) from None

    groups = (payload.get("cookie_data") or {})
    if not groups:
        return "⚠ 服务端能解密，但里面没有 cookie_data —— 扩展可能还没同步内容"
    detail = ", ".join(f"{k}:{len(v)}" for k, v in groups.items())
    return f"✓ 服务端验证通过（{detail}）"


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
