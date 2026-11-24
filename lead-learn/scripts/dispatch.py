"""把「分流」的机械部分做掉，判断留给人（或模型）。

设计前提：**分流是判断，不是计数。** 关键词打分有三个硬伤——
词表漏人、max() 只留一个赢家、字面计数看不懂语义。
所以本脚本不做任何打分，它只做四件机械活：

  roster   扫盘出花名册（谁管什么，从 self.md / agent.json 读）
  list     把待分流的稿子列出来（标题 + 前 300 字，够判归属就行）
  apply    按你写的 plan.json 落成派单文件
  verify   不看回报，看盘面实际变了什么

用法：
    python dispatch.py roster
    python dispatch.py list
    python dispatch.py apply plan.json
    python dispatch.py status
    python dispatch.py verify --since 2026-11-24
"""

from __future__ import annotations

import json
import re
import sys
from datetime import date, datetime
from pathlib import Path

from paths import DISPATCH, RECALL, STAGING  # noqa: E402

# ---------------------------------------------------------------- 读稿子

def _read_front(raw: str) -> tuple[dict, str]:
    """拆 frontmatter 与正文。CRLF 也认——Windows 编辑器存过的稿子会被整篇误判。"""
    raw = raw.replace("\r\n", "\n").replace("\r", "\n").lstrip("\ufeff")
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", raw, re.S)
    if not m:
        return {}, raw
    meta = {}
    for line in m.group(1).split("\n"):
        if ":" in line:
            k, _, v = line.partition(":")
            meta[k.strip()] = v.strip()
    return meta, m.group(2)


DISPATCHED_PREFIXES = ("routed:", "dispatched:", "dropped", "undecided")


def _items() -> list[dict]:
    """STAGING 下**还没派过**的 .staged.md。

    ⚠ 这里曾经只认 `routed:`，但 `cmd_apply` 写的是 `dispatched:`——
    读写两端用了两个不同的词，等于一条都没跳过。实测后果：36 份稿子里
    18 份已经派过单，`list` 仍然把它们算成「待分流」，排版/选题重复劳动。
    """
    if not STAGING.exists():
        return []
    out = []
    for f in sorted(STAGING.glob("*.staged.md")):
        meta, body = _read_front(f.read_text(encoding="utf-8", errors="replace"))
        if meta.get("status", "").startswith(DISPATCHED_PREFIXES):
            continue
        body = re.sub(r"^##\s*转录全文\s*", "", body.strip())
        brief = re.sub(r"\s+", " ", body).strip()
        out.append({
            "file": f,
            "key": meta.get("key", ""),
            "title": meta.get("title", f.stem),
            "platform": meta.get("platform", ""),
            "chars": int(meta["chars"]) if meta.get("chars", "").isdigit() else len(brief),
            "brief": brief[:300],
            "status": meta.get("status", ""),
        })
    return out


# ---------------------------------------------------------------- 花名册

def _agent_info(name: str) -> dict:
    """一个 agent 的定位。self.md 的 position 比 agent.json 的 description 可信。

    agent.json 里 description 等于自己名字的都是占位空壳，别被它骗。
    """
    d = RECALL / name
    desc, pos = "", ""
    aj = d / "agent.json"
    if aj.exists():
        try:
            desc = (json.loads(aj.read_text(encoding="utf-8-sig")).get("description") or "").strip()
        except Exception:
            pass
    sm = d / "self.md"
    if sm.exists():
        raw = sm.read_text(encoding="utf-8", errors="replace")
        m = re.search(r'"position":\s*"((?:[^"\\]|\\.)*)"', raw)
        if m:
            pos = m.group(1).replace('\\"', '"')
        if not pos:
            m = re.search(r'"persona_style":\s*"((?:[^"\\]|\\.)*)"', raw)
            if m:
                pos = m.group(1)
    placeholder = desc == name or not desc
    return {
        "name": name,
        "display": _display_name(sm),
        "description": desc,
        "position": pos,
        "placeholder": placeholder,
        "has_longterm": (d / "longterm").exists(),
        "has_self": sm.exists(),
    }


def _display_name(sm: Path) -> str:
    if not sm.exists():
        return ""
    m = re.search(r"(?m)^name:\s*(.+)$", sm.read_text(encoding="utf-8", errors="replace"))
    return m.group(1).strip() if m else ""


def _roster() -> list[dict]:
    if not RECALL.exists():
        return []
    skip = {"default"}
    out = []
    for d in sorted(RECALL.iterdir()):
        if not d.is_dir() or d.name in skip or d.name.startswith(("_", ".")):
            continue
        out.append(_agent_info(d.name))
    return out


# ---------------------------------------------------------------- 命令

def cmd_roster() -> int:
    rs = _roster()
    if not rs:
        print(f"没有 recall 记忆区：{RECALL}")
        print("（没有 recall 也能用本 skill——派单会落在 $LEAD_LEARN_HOME/dispatch，见 paths.py）")
        return 0
    for a in rs:
        if not a["has_self"] and a["placeholder"]:
            continue
        tag = "" if not a["placeholder"] else "  ⚠ agent.json 是占位，看 position"
        print(f"【{a['display'] or a['name']}】{a['name']}{tag}")
        src = a["position"] or a["description"]
        if src:
            print(f"    {src[:160]}")
        if not a["has_longterm"]:
            print("    （无 longterm，还没建长期内容）")
    return 0


def cmd_list(show: int = 300) -> int:
    items = _items()
    if not items:
        print(f"没有待分流的稿子（{STAGING}）")
        return 0
    print(f"待分流 {len(items)} 份\n")
    for it in items:
        print(f"◎ [{it['platform']}] {it['key']}  ({it['chars']}字)")
        print(f"  T: {it['title']}")
        print(f"  B: {it['brief'][:show]}")
        print()
    return 0


def _canonical(agent: str, match: dict) -> str:
    """把 plan 里写的 agent 统一成**目录名**（`liangliang`），不要用显示名。

    为什么必须归一到目录名：显示名只用来给人看，落盘文件名一用显示名，
    `liangliang` 和 `量量` 就会写成同一个 `量量_staging.md` ——
    `by_agent` 里是 2 个键、盘上只有 1 个文件，**后写的整份覆盖先写的，静默丢派单**。
    实测：plan 里一条写 `liangliang`、一条写 `量量`，2 条派单只落了 1 条。
    """
    info = match.get(agent)
    return info["name"] if info else agent


def _load_plan(path: Path) -> dict:
    if not path.exists():
        raise SystemExit(f"plan 不存在：{path}")
    plan = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(plan.get("items"), list):
        raise SystemExit("plan 缺 items 数组")

    known_keys = {it["key"] for it in _items()}
    roster = _roster()
    known_agents = {a["name"] for a in roster}
    known_agents |= {a["display"] for a in roster if a["display"]}
    match: dict[str, dict] = {}
    for a in roster:
        match[a["name"]] = a
        if a["display"]:
            match.setdefault(a["display"], a)

    problems = []
    for it in plan["items"]:
        if it.get("key") not in known_keys:
            problems.append(f"未知 key（不在 staging 里或已分流）：{it.get('key')}")
        if not it.get("to"):
            problems.append(f"没写 to：{it.get('title')}")
        seen_canon: dict[str, str] = {}
        for t in it.get("to") or []:
            # 没有 recall 时无从校验角色名，只校验结构
            if roster and t.get("agent") not in known_agents:
                problems.append(f"未知 agent：{t.get('agent')}（{it.get('title')}）")
            if not t.get("reason"):
                problems.append(f"派给 {t.get('agent')} 但没写 reason：{it.get('title')}")
            # 同一 agent 用名字和显示名写两遍 → 归一后重复派单
            c = _canonical(t.get("agent", ""), match)
            if c in seen_canon and seen_canon[c] != t.get("agent"):
                problems.append(
                    f"同一个 agent 写了两次（{seen_canon[c]} / {t.get('agent')}）：{it.get('title')}")
            seen_canon[c] = t.get("agent", "")

    if problems:
        print("plan 有问题，未写入：")
        for p in problems:
            print(f"  ✗ {p}")
        raise SystemExit(1)
    return plan


def write_count(path: Path, n: int) -> None:
    """把派单文件 frontmatter 的 count 改成实际未划掉的条目数。

    为什么要这么一个函数：count 是 apply 时写死的，之后子智能体划掉条目
    不会改它，`status` 读的却是它——于是永远显示派单当天的数字。
    实测：`II_staging.md` 的 count 一直显示 4，而第 1 条早已学完。
    """
    raw = path.read_text(encoding="utf-8", errors="replace")
    if re.search(r"(?m)^count:\s*\d+\s*$", raw):
        raw = re.sub(r"(?m)^count:\s*\d+\s*$", f"count: {n}", raw, count=1)
    else:
        raw = raw.replace("---\n", f"---\ncount: {n}\n", 1)
    path.write_text(raw, encoding="utf-8")


def _pending_count(path: Path) -> int:
    """一份派单文件里还有几条没划掉（`## 1.` 算未完成，`## ~~1.` 算已完成）。"""
    raw = path.read_text(encoding="utf-8", errors="replace")
    return len(re.findall(r"(?m)^## \d+\.", raw))


def cmd_apply(plan_path: Path, confirm: bool = False, mark_index: bool = False) -> int:
    plan = _load_plan(plan_path)
    items = {it["key"]: it for it in _items()}
    RECALL_MATCH = {a["name"]: a for a in _roster()}
    for a in _roster():
        if a["display"]:
            RECALL_MATCH.setdefault(a["display"], a)

    # 按 agent 归拢。**键用目录名**：用显示名会让 liangliang / 量量 撞成同一个文件。
    by_agent: dict[str, list[dict]] = {}
    for it in plan["items"]:
        src = items[it["key"]]          # 平台/字数/简介从 staging 原件取，plan 里只写判断
        for t in it["to"]:
            canon = _canonical(t["agent"], RECALL_MATCH)
            by_agent.setdefault(canon, []).append({
                **src,
                "url": it.get("url", ""),
                "reason": t["reason"],
                "also": [x["agent"] for x in it["to"]],
            })

    # 预览
    print(f"派单目录：{DISPATCH}")
    total = 0
    for agent, entries in sorted(by_agent.items()):
        display = RECALL_MATCH.get(agent, {}).get("display") or agent
        print(f"  {display}_staging.md  {len(entries)} 条  ← {', '.join(e['key'] for e in entries)}")
        total += len(entries)
    dropped = plan.get("dropped") or []
    undecided = plan.get("undecided") or []
    print(f"\n派给 {len(by_agent)} 家，共 {total} 条；丢 {len(dropped)} 份；待定 {len(undecided)} 份。")

    if not confirm:
        print("\n（预览。加 --confirm 实际写入，加 --mark-index 同时在各 agent 的 LONGTERM.md 登记）")
        return 0

    DISPATCH.mkdir(parents=True, exist_ok=True)
    now = datetime.now().isoformat(timespec="seconds")
    written = 0
    for agent, entries in sorted(by_agent.items()):
        info = RECALL_MATCH.get(agent, {})
        display = info.get("display") or agent
        path = DISPATCH / f"{display}_staging.md"
        # 追加而不是覆盖：上一轮没学完的条目必须留着。
        # 实测教训——整份覆盖会让上一轮的派单静默消失，agent 再也看不到那些活。
        prev = ""
        if path.exists():
            raw_prev = path.read_text(encoding="utf-8", errors="replace")
            m_prev = re.search(r"(?ms)^---\n.*?\n---\n(.*)$", raw_prev)
            body_prev = (m_prev.group(1) if m_prev else raw_prev).strip()
            if body_prev and re.search(r"(?m)^## ", body_prev):
                prev = body_prev
        lines = [
            "---",
            "dispatched_by: lead-learn",
            f"dispatched_at: {now}",
            f"agent: {agent}",
            f"count: {len(entries)}",
            "---",
            "",
            f"# 派单 · {display}",
            "",
            f"这里 {len(entries)} 条，从收藏夹抓来。判给你的理由写在每条下面。",
            "**判给你的只是我的判断，学不学、留不留由你定。**",
            "",
            "需要文字稿自己转，需要看画面用 storyboard 抽帧。",
            "**`.favorites-out/longterm-staging/` 里的 `.staged.md` 是唯一兜底，一份都不许删。**",
            "学完只划掉本文件里对应的条目，本文件全部学完才删。",
            "",
            "---",
            "",
        ]
        # 追加：上一轮未消化的条目原样保留在前面
        if prev:
            lines += [prev, "", "---", "", f"<!-- 以下为 {now} 新派 -->", ""]
        for i, e in enumerate(entries, 1):
            others = [x for x in e["also"] if x != agent]
            lines += [
                f"## {i}. {e['title']}",
                "",
                f"- 链接：{e.get('url', '')}",
                f"- 平台：{e['platform']}　key：`{e['key']}`",
                f"- 派给你的理由：{e['reason']}",
            ]
            if others:
                lines.append(f"- 同时派给了：{'、'.join(others)}（别替他们做，只取你要的）")
            lines.append("")
        path.write_text("\n".join(lines), encoding="utf-8")
        # count 写**总待消化数**（含上一轮遗留），否则 status 会少报
        total_pending = len(re.findall(r"(?m)^## \d+\.", "\n".join(lines)))
        if total_pending != len(entries):
            write_count(path, total_pending)
        print(f"→ {path}  (本轮 {len(entries)} 条，共 {total_pending} 条待消化)")
        written += len(entries)

    # 台账
    ledger = DISPATCH / "_ledger.md"
    rows = [
        "| # | 标题 | 链接 | 派给 | 状态 |",
        "|---|---|---|---|---|",
    ]
    for i, it in enumerate(plan["items"], 1):
        who = "、".join(t["agent"] for t in it["to"])
        title = it["title"].replace("|", "／")[:40]
        rows.append(f"| {i} | {title} | {it.get('url', '')} | {who} | 已派 |")
    dropped = plan.get("dropped") or []
    body = [
        f"# 派单台账 · {plan.get('round', date.today().isoformat())}",
        "",
        f"派给 {len(by_agent)} 个 agent，共 {written} 条派单（含跨领域重复），"
        f"丢 {len(dropped)} 份。",
        "",
        "**本文件不删。** 它是最后汇总的骨架，也是下次核对的凭据。",
        "",
        *rows,
    ]
    if dropped:
        body += ["", "## 丢弃", "", "| 标题 | 为什么丢 |", "|---|---|"]
        for d in dropped:
            body.append(f"| {d.get('title', '')[:40]} | {d.get('why', '')} |")
    undecided = plan.get("undecided") or []
    if undecided:
        body += ["", "## 待定（需人点头）", "", "| 标题 | 卡在哪 |", "|---|---|"]
        for u in undecided:
            body.append(f"| {u.get('title', '')[:40]} | {u.get('why', '')} |")
    ledger.write_text("\n".join(body) + "\n", encoding="utf-8")
    print(f"→ {ledger}")

    # 回写源稿状态，避免下次重跑又被投一遍
    for it in plan["items"]:
        src = items[it["key"]]["file"]
        raw = src.read_text(encoding="utf-8", errors="replace")
        raw = re.sub(r"^status:\s*\S+\s*$",
                     f"status: dispatched:{'|'.join(t['agent'] for t in it['to'])}",
                     raw, count=1, flags=re.M)
        src.write_text(raw, encoding="utf-8")

    # ⚠ 丢掉的稿子也要回写状态，否则每晚的定时任务会把它们重新捞出来派一遍。
    # 这是实测出来的真 bug：台账里记了 16 条「丢弃」，但没有任何代码把
    # `status:` 改成 dropped，于是 `_items()` 每晚都返回它们。
    dropped_keys = set()
    for d in dropped:
        k = d.get("key")
        if k:
            dropped_keys.add(k)
    if dropped_keys:
        n_drop = 0
        for f in sorted(STAGING.glob("*.staged.md")):
            raw = f.read_text(encoding="utf-8", errors="replace")
            m = re.search(r"(?m)^key:\s*(\S+)\s*$", raw)
            if not m or m.group(1) not in dropped_keys:
                continue
            raw = re.sub(r"^status:\s*\S+\s*$", "status: dropped", raw, count=1, flags=re.M)
            f.write_text(raw, encoding="utf-8")
            n_drop += 1
        print(f"→ 已把 {n_drop} 份丢弃稿的 status 标为 dropped（不会再被 list 捞出来）")

    # undecided 的也标出来，但用一个"待你点头"的状态，免得混进丢弃
    undecided_keys = {u.get("key") for u in undecided if u.get("key")}
    if undecided_keys:
        n_und = 0
        for f in sorted(STAGING.glob("*.staged.md")):
            raw = f.read_text(encoding="utf-8", errors="replace")
            m = re.search(r"(?m)^key:\s*(\S+)\s*$", raw)
            if not m or m.group(1) not in undecided_keys:
                continue
            if re.search(r"(?m)^status:\s*dropped\s*$", raw):
                continue
            raw = re.sub(r"^status:\s*\S+\s*$", "status: undecided", raw, count=1, flags=re.M)
            f.write_text(raw, encoding="utf-8")
            n_und += 1
        if n_und:
            print(f"→ 已把 {n_und} 份待定稿的 status 标为 undecided（等你点头再派）")

    # 选填：在各 agent 的 LONGTERM.md 登记（默认不动别人的索引）
    if mark_index:
        print()
        _mark_index(by_agent, RECALL_MATCH)

    print(f"\n派给 {len(by_agent)} 家，{written} 条。")
    print("下一步：给每家开子智能体，提示词见 SKILL.md 第 5 步（逐字用，不改写）。")
    return 0


def _mark_index(by_agent: dict, match: dict) -> None:
    """在各 agent 的 LONGTERM.md 留一行指路——索引没写等于没建。"""
    for agent in sorted(by_agent):
        info = match.get(agent, {})
        d = RECALL / agent
        idx = d / "longterm" / "LONGTERM.md"
        if not idx.exists():
            print(f"  {agent}: 无 LONGTERM.md，跳过登记")
            continue
        display = info.get("display") or agent
        line = (f"- 派单：`{DISPATCH / f'{display}_staging.md'}` "
                f"（{len(by_agent[agent])} 条，lead-learn 派来，学完划掉条目）")
        text = idx.read_text(encoding="utf-8", errors="replace")
        if "lead-learn 派单" in text:
            print(f"  {agent}: 已有登记，跳过")
            continue
        text = text.rstrip() + (
            f"\n\n<!-- lead-learn -->\n## 待消化：lead-learn 派单\n\n{line}\n"
            "\n读完 staging 后归入正式类目，然后**把本段整段删掉**。\n"
        )
        idx.write_text(text, encoding="utf-8")
        print(f"  {agent}: 已登记")


def cmd_reset(key: str = "") -> int:
    """把源稿的 dispatched: 状态清回 staged_needs_review，让它能重新被派。

    也用于撤错：派错了想重派，先 reset 对应 key，改 plan.json，再 apply。
    """
    files = sorted(STAGING.glob("*.staged.md")) if STAGING.exists() else []
    n = 0
    for f in files:
        raw = f.read_text(encoding="utf-8", errors="replace")
        m = re.search(r"(?m)^key:\s*(\S+)\s*$", raw)
        if not m:
            continue
        if key and m.group(1) != key:
            continue
        if not re.search(r"(?m)^status:\s*dispatched:", raw):
            continue
        raw = re.sub(r"(?m)^status:\s*dispatched:.*$", "status: staged_needs_review", raw)
        f.write_text(raw, encoding="utf-8")
        print(f"重置 {m.group(1)}  {f.name}")
        n += 1
    print(f"共重置 {n} 份" if n else "没有需要重置的")
    return 0


def cmd_status() -> int:
    if not DISPATCH.exists():
        print(f"派单目录还不存在：{DISPATCH}")
        return 0
    files = sorted(DISPATCH.glob("*_staging.md"))
    print(f"派单目录：{DISPATCH}")
    if not files:
        print("  空（全部收工，或还没派）")
    live = 0
    for f in files:
        # 数**实际未划掉的条目**，不读 frontmatter 的 count。
        # count 是 apply 时写死的，子智能体划条目不会改它，读它会永远少报。
        pending = _pending_count(f)
        stored = re.search(r"(?m)^count:\s*(\d+)",
                           f.read_text(encoding="utf-8", errors="replace"))
        drift = ""
        if stored and stored.group(1).isdigit() and int(stored.group(1)) != pending:
            drift = f"  （count 字段写的 {stored.group(1)}，已漂移）"
        if pending:
            live += 1
            print(f"  {f.name:24} 剩 {pending} 条未消化{drift}")
        else:
            print(f"  {f.name:24} 已清空，可删{drift}")
    led = DISPATCH / "_ledger.md"
    if led.exists():
        print(f"  台账：{led}")
    print(f"\n派单文件数 = 还没交活的 agent 数：{live}"
          f"（另有 {len(files) - live} 份已清空待删）")
    return 0


def cmd_verify(since: str = "") -> int:
    """不听回报，看盘面实际变了什么。"""
    since = since or date.today().isoformat()
    print(f"[盘面核查] since {since}\n")

    files = sorted(DISPATCH.glob("*_staging.md")) if DISPATCH.exists() else []
    live = [f for f in files if _pending_count(f)]
    print(f"派单未消化：{len(live)} 家")
    for f in live:
        print(f"  · {f.name}  剩 {_pending_count(f)} 条")
    done = [f.name for f in files if not _pending_count(f)]
    if done:
        print(f"已清空可删：{'、'.join(done)}")

    if not RECALL.exists():
        print(f"\n没有 recall 区（{RECALL}），跳过记忆区核查。")
        return 0

    # longterm 列必须算**增量**，不能是总数——总数对「这一轮有没有干活」毫无信息，
    # 而且一个 agent 的 longterm 基数大（开编 29 个文件）时，涨没涨根本看不出来。
    since_ts = datetime.fromisoformat(since).timestamp() if _is_date(since) else None
    print("\n各 agent 变化（longterm 列 = 该日之后新增/修改的文件数）：")
    hdr = f"  {'agent':12} {'新增/改':>7} {'今日日记':>7}  索引登记"
    print(hdr)
    for a in _roster():
        d = RECALL / a["name"]
        lt = d / "longterm"
        n_lt = 0
        if lt.exists() and since_ts is not None:
            n_lt = sum(1 for p in lt.rglob("*")
                       if p.is_file() and not p.name.startswith(".")
                       and p.stat().st_mtime >= since_ts)
        dn = d / "dailynote"
        n_today = sum(1 for p in dn.glob(f"{since}*.md")) if dn.exists() else 0
        idx = lt / "LONGTERM.md"
        marked = ""
        if idx.exists():
            marked = "✓" if "lead-learn 派单" in idx.read_text(encoding="utf-8", errors="replace") else ""
        if n_today or marked or n_lt:
            print(f"  {a['name']:12} {n_lt:>7} {n_today:>7}  {marked}")
    print("\n判据：今日日记有 = 它真的动了；新增/改为 0 但回报说收了 = 以盘面为准；"
          "索引登记留着 = 活没干完。")
    return 0


def _is_date(s: str) -> bool:
    try:
        date.fromisoformat(s)
        return True
    except ValueError:
        return False


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 0
    cmd = argv[0]
    if cmd == "roster":
        return cmd_roster()
    if cmd == "list":
        n = int(argv[1]) if len(argv) > 1 and argv[1].isdigit() else 300
        return cmd_list(n)
    if cmd == "apply":
        if len(argv) < 2:
            raise SystemExit("用法：python dispatch.py apply plan.json [--confirm] [--mark-index]")
        return cmd_apply(
            Path(argv[1]),
            confirm="--confirm" in argv,
            mark_index="--mark-index" in argv,
        )
    if cmd == "reset":
        return cmd_reset(argv[1] if len(argv) > 1 else "")
    if cmd == "status":
        return cmd_status()
    if cmd == "verify":
        since = argv[argv.index("--since") + 1] if "--since" in argv else ""
        return cmd_verify(since)
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
