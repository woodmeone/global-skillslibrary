"""回填：把已处理但当时走了 ASR 的条目，重新检测字幕。

之前 probe_subtitle 的判断有 bug，把所有视频都判成「无字幕」，
导致 9 条全走了 ASR。现在修好了，回填一遍：
  - 有字幕的改成 subtitle 路线（更准）
  - 没字幕的保留原 ASR 结果

用法：
    python backfill_subs.py           # 只报告
    python backfill_subs.py --apply   # 实际改写状态
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from paths import HOME as BASE, STATE, MEDIA  # noqa: E402


def main(apply: bool) -> int:
    state = json.loads(STATE.read_text(encoding="utf-8"))
    proc = state.get("processed", {})

    sys.path.insert(0, str(BASE))
    import pipeline as P

    hits = 0
    changed = 0
    for key, v in proc.items():
        if v.get("platform") != "bilibili":
            continue
        bv = v.get("key", "").split(":", 1)[-1]
        if not bv.startswith("BV"):
            continue
        if v.get("has_subtitle"):
            continue

        has = P.probe_subtitle(bv)
        if not has:
            print(f"·  {bv} 无中文字幕")
            continue

        hits += 1
        print(f"✓  {bv} 有字幕 | {(v.get('title') or '')[:40]}")
        if not apply:
            continue

        # 找已有的 mp4：标题里可能含 / 等字符，yt-dlp 会替换成 ⧸ 之类，
        # 所以用「清洗后前 12 字」做匹配，且失败时退到最新文件
        import re

        def norm(s: str) -> str:
            return re.sub(r"[\\/:*?\"<>|⧸｜\s]+", "", s)

        want = norm(v.get("title") or "")[:12]
        video = None
        if want:
            for p in MEDIA.glob("*.mp4"):
                if want in norm(p.stem):
                    video = p
                    break
        if not video:
            print("   ⚠ 找不到已下载文件，跳过")
            continue

        sub = P.fetch_subtitle(video, bv)
        if not sub:
            print("   ⚠ 字幕下载失败，保留 ASR")
            continue
        chars = len(sub.read_text(encoding="utf-8", errors="replace"))
        old = v.get("transcript_chars", 0)
        v["has_subtitle"] = True
        v["route"] = "subtitle"
        v["transcript"] = str(sub)
        v["transcript_chars"] = chars
        v["backfilled"] = True
        changed += 1
        print(f"   ✓ 改用字幕：{old} 字(ASR) → {chars} 字(字幕)")

    if apply and changed:
        STATE.write_text(
            json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        # 清掉空的 srt 残留
        for f in MEDIA.glob("*.sub*.srt"):
            try:
                f.unlink()
            except OSError:
                pass

    print(f"\n有字幕: {hits} 条 / 已改写: {changed} 条")
    if not apply:
        print("（只报告，加 --apply 实际改写）")
    return 0


if __name__ == "__main__":
    sys.exit(main("--apply" in sys.argv))
