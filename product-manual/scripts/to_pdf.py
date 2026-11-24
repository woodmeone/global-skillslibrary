# -*- coding: utf-8 -*-
"""DOCX → PDF（Windows / Word COM）。

为什么单独成脚本：Word COM 会静默卡死，直接写在流程里会让整轮任务超时。
本脚本加了三道防线：显式 DisplayAlerts=0、单个文档超时、失败后强杀残留进程。

用法：
    python to_pdf.py --dir docs/manuals
    python to_pdf.py --dir docs/manuals --keep-docx
    python to_pdf.py --file a.docx --timeout 180

前提：本机装有 Microsoft Word。没有的话改用 LibreOffice：
    soffice --headless --convert-to pdf --outdir OUT file.docx
"""
import argparse
import subprocess
import sys
import time
from pathlib import Path

PS_TEMPLATE = r"""
$ErrorActionPreference = "Stop"
$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
try {{
  $doc = $word.Documents.Open("{src}")
  $doc.ExportAsFixedFormat("{dst}", 17)
  $doc.Close(0)
  Write-Output "OK"
}} finally {{
  $word.Quit()
  [System.Runtime.Interopservices.Marshal]::ReleaseComObject($word) | Out-Null
}}
"""


def kill_word():
    subprocess.run(["powershell", "-NoProfile", "-Command",
                    "Get-Process WINWORD -ErrorAction SilentlyContinue | Stop-Process -Force"],
                   capture_output=True)


def _win_path(p: Path) -> str:
    """转成 PowerShell 能正确解析的绝对路径。

    踩过的坑：用 as_posix() 得到 "D:/桌面/..." 时，PowerShell 里
    Documents.Open() 会把它误解析成 "D:\\//桌面/..."，报"找不到文件"。
    必须用 Windows 原生反斜杠，并对单引号做转义。
    """
    return str(p.resolve()).replace("/", "\\").replace("'", "''")


def convert(src: Path, dst: Path, timeout=180):
    if dst.exists():
        dst.unlink()
    ps = PS_TEMPLATE.format(src=_win_path(src), dst=_win_path(dst))
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        kill_word()
        print(f"  超时 {timeout}s，已强杀 Word：{src.name}")
        return False
    except Exception as e:
        # 中文路径 / 非 UTF-8 控制台输出都可能让 subprocess 起不来
        kill_word()
        print(f"  启动失败 {src.name}: {e}")
        return False

    if dst.exists() and dst.stat().st_size > 0:
        print(f"  OK {src.name} -> {dst.name}  {dst.stat().st_size // 1024}KB")
        return True

    kill_word()
    err = (r.stderr or "").strip()[:200] if r else ""
    if err:
        print(f"  失败 {src.name}: {err}")
    else:
        print(f"  失败 {src.name}（无输出，可能是路径或权限问题）")
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir")
    ap.add_argument("--file")
    ap.add_argument("--timeout", type=int, default=180)
    ap.add_argument("--keep-docx", action="store_true", help="保留源文件（默认保留，此开关仅示意）")
    args = ap.parse_args()

    if args.file:
        src = Path(args.file).resolve()
        return 0 if convert(src, src.with_suffix(".pdf"), args.timeout) else 1

    if not args.dir:
        print("需要 --dir 或 --file")
        return 1

    files = sorted(Path(args.dir).glob("*.docx"))
    if not files:
        print("目录下没有 .docx")
        return 1
    ok = sum(convert(f, f.with_suffix(".pdf"), args.timeout) for f in files)
    print(f"完成 {ok}/{len(files)}")
    return 0 if ok == len(files) else 1


if __name__ == "__main__":
    sys.exit(main())
