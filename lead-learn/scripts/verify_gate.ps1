param(
    [switch]$Quiet
)

# scripts/verify_gate.ps1 · 自优化的三道闸（G2）
# 设计依据：docs/adr/0002。任一闸不过就退 1，自优化流程必须据此拒绝提交。
#
# 注意：本文件必须存成 UTF-8 with BOM。
# PowerShell 5.1 在中文 Windows 上按 GBK 读 .ps1，无 BOM 会把中文解析成乱码并报语法错。

$ErrorActionPreference = "Continue"
$SKILL = Split-Path $PSScriptRoot -Parent

# 工作区解析：环境变量 > ~/.lead-learn/config.json > 当前目录。不写死绝对路径。
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

$script:failed = @()

function Gate($name, $block) {
    Write-Host ""
    Write-Host "── $name ──" -ForegroundColor Cyan
    # 只取块的最后一个返回值：块内的 Write-Host 不产管道输出，
    # 但 ForEach-Object / git 输出会混进来，取 Last 1 才拿得到真布尔。
    $ok = (@(& $block) | Select-Object -Last 1)
    if ($ok -isnot [bool]) { $ok = [bool]$ok }
    if (-not $ok) {
        # ⚠ 必须写 $script: —— 函数内的 $failed += 会创建局部变量，
        # 脚本级那个永远不变，于是「三道闸全过」照样打印（实测踩过）。
        $script:failed += $name
    }
    return $ok
}

# ---- 闸 1：测试全绿 ----
Gate "闸1 pytest" {
    Push-Location (Join-Path $SKILL "scripts")
    try {
        $out = & python -X utf8 -m pytest (Join-Path $SKILL "tests") -q 2>&1
        $out | ForEach-Object { Write-Host "  $_" }
        return ($LASTEXITCODE -eq 0)
    } finally { Pop-Location }
} | Out-Null

# ---- 闸 2：三个冒烟命令 exit 0 ----
Gate "闸2 冒烟" {
    $allOk = $true
    foreach ($t in @(
        @{ n = "dispatch status"; s = "dispatch.py"; a = "status" },
        @{ n = "health";          s = "health.py";   a = "" },
        @{ n = "pipeline status"; s = "pipeline.py"; a = "status" }
    )) {
        $args = @("-X", "utf8", (Join-Path $SKILL "scripts\$($t.s)"))
        if ($t.a) { $args += $t.a }
        $null = & python @args 2>&1
        $code = $LASTEXITCODE
        if ($code -ne 0) {
            Write-Host ("  ✗ {0} 退出码 {1}" -f $t.n, $code) -ForegroundColor Red
            $allOk = $false
        } else {
            Write-Host ("  ✓ {0}" -f $t.n) -ForegroundColor Green
        }
    }
    return $allOk
} | Out-Null

# ---- 闸 3：不许碰的路径 ----
Gate "闸3 禁改区" {
    Push-Location $SKILL
    try {
        $diff = & git diff --name-only HEAD 2>&1
        $staged = & git diff --cached --name-only 2>&1
        $changed = @($diff) + @($staged) | Where-Object { $_ } | Select-Object -Unique

        $forbidden = @()
        foreach ($f in $changed) {
            if ($f -eq "SKILL.md") { $forbidden += "$f（name/description 会触发 skill 目录刷新）" }
            if ($f -eq "scripts/paths.py") { $forbidden += "$f（路径常量）" }
            if ($f -eq "assets/学习任务模板.md") { $forbidden += "$f（子智能体提示词）" }
        }

        if ($forbidden.Count -gt 0) {
            Write-Host "  ✗ 改到了禁改区：" -ForegroundColor Red
            $forbidden | ForEach-Object { Write-Host "      $_" -ForegroundColor Red }
            return $false
        }
        Write-Host ("  ✓ 改动 {0} 个文件，无禁改区" -f $changed.Count) -ForegroundColor Green
        return $true
    } finally { Pop-Location }
} | Out-Null

Write-Host ""
if ($script:failed.Count -eq 0) {
    Write-Host "三道闸全过 ✓  可以提交" -ForegroundColor Green
    exit 0
} else {
    Write-Host ("闸未过：{0}" -f ($script:failed -join "、")) -ForegroundColor Red
    Write-Host "按 docs/adr/0002：不许提交，先修或 revert。" -ForegroundColor Yellow
    exit 1
}
