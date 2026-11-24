# scripts/run_nightly.ps1 · 每夜自动学习（只到派单，不派子智能体）
# 设计依据：docs/adr/0002。不自动开子智能体——分流是判断，需要人过一眼。
#
# 注意：本文件必须存成 UTF-8 with BOM。
# PowerShell 5.1 在中文 Windows 上按 GBK 读 .ps1，无 BOM 会把中文解析成乱码并报语法错。

$ErrorActionPreference = "Stop"
$SKILL = $PSScriptRoot

# 工作区解析：环境变量 > ~/.lead-learn/config.json > 当前目录。
# **不写死绝对路径**——skill 会装到别的机器上，写死即废。
function Resolve-Work {
    if ($env:LEAD_LEARN_HOME) { return $env:LEAD_LEARN_HOME }
    $cfg = Join-Path $env:USERPROFILE ".lead-learn\config.json"
    if (Test-Path $cfg) {
        try {
            $j = Get-Content -Raw -Encoding utf8 $cfg | ConvertFrom-Json
            if ($j.home) { return [string]$j.home }
        } catch { }
    }
    return (Join-Path (Get-Location).Path "lead-learn-data")
}
$WORK = Resolve-Work

$env:LEAD_LEARN_HOME = $WORK
$env:LEAD_LEARN_AGENT = if ($env:LEAD_LEARN_AGENT) { $env:LEAD_LEARN_AGENT } else { "lead" }
$env:PYTHONIOENCODING = "utf-8"

$LOG_DIR = Join-Path $WORK ".favorites-out\logs"
New-Item -ItemType Directory -Path $LOG_DIR -Force | Out-Null
$STAMP = Get-Date -Format "yyyyMMdd-HHmmss"
$LOG = Join-Path $LOG_DIR "nightly-$STAMP.log"

function Say($msg) {
    # 子脚本自己带 [HH:mm:ss]，这里就不再叠一层，否则日志变成
    # [12:31:20]   [12:31:20]   ✓ ...（实测踩过）
    $s = "$msg"
    $line = if ($s -match '^\s*\[\d{2}:\d{2}:\d{2}\]') { $s } else { "[{0}] {1}" -f (Get-Date -Format "HH:mm:ss"), $s }
    Write-Host $line
    Add-Content -Path $LOG -Value $line -Encoding utf8
}

function Step($name, [string[]]$pyArgs) {
    Say "=== $name ==="
    try {
        & python -X utf8 @pyArgs 2>&1 | ForEach-Object { Say "  $_" }
        $rc = $LASTEXITCODE
        if ($rc -ne 0) { Say "  ✗ $name 退出码 $rc"; return $false }
        return $true
    } catch {
        Say "  ✗ $name 异常: $_"
        return $false
    }
}

Say "夜间学习开始  work=$WORK  log=$LOG"

# ⚠ 全程在 $WORK 下运行。
# 子工具（media-downloader / yt-dlp）拿 Path.cwd() 当 workspace，
# 谁在哪个目录启动，产物就落在那个目录。2026-11-24 从 skill 目录启动，
# 20 条稿全下进了 globalSkills-library\lead-learn\media-downloads\，
# 还被 git 一起提交了。钉死 cwd 是第二道保险（第一道是 pipeline 传 -o）。
Push-Location $WORK
try {

# ① 抓取（失败不致命——用上次的 JSON 也能跑）
# 注意 favorites.py 需要两个参数：grab <platform>
Step "抓 B站" @((Join-Path $SKILL "bili_grab3.py")) | Out-Null
Step "抓抖音" @((Join-Path $SKILL "favorites.py"), "grab", "douyin") | Out-Null

# ② 有多少新增（这一步决定后面要不要真跑）
Say "=== 增量检测 ==="
$checkOut = & python -X utf8 (Join-Path $SKILL "pipeline.py") check 2>&1
$checkOut | ForEach-Object { Say "  $_" }
$newCount = 0
foreach ($line in $checkOut) {
    if ($line -match "新增:\s*(\d+)") { $newCount = [int]$Matches[1] }
}

if ($newCount -eq 0) {
    Say "无新增，跳过处理与归档。over."
    Pop-Location
    exit 0
}

# ③ 处理 + 归档 + 清媒体
Say "发现 $newCount 条新增，开始处理（上限 20）"
Step "处理" @((Join-Path $SKILL "pipeline.py"), "run", "--limit", "20") | Out-Null
Step "归档" @((Join-Path $SKILL "pipeline.py"), "stage") | Out-Null
Step "清媒体" @((Join-Path $SKILL "pipeline.py"), "clean") | Out-Null

# ④ 列出待分流（**不自动派单**）
Say "=== 待分流 ==="
& python -X utf8 (Join-Path $SKILL "dispatch.py") list 120 2>&1 | ForEach-Object { Say "  $_" }

Say "夜间学习结束。早上看：dispatch.py list，觉得该派再派。"

} finally {
    Pop-Location
}
