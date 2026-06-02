# ============================================================
# testcase-creator 一键初始化脚本（Windows PowerShell 版）
# 用法：.\init-testcase.ps1 -TargetDir C:\path\to\your-project
#       .\init-testcase.ps1 -TargetDir . -Force
# ============================================================

param(
    [string]$TargetDir = "",
    [switch]$Force
)

# ---------- 颜色输出函数 ----------
function Write-Color {
    param([string]$Text, [string]$Color = "White")
    Write-Host $Text -ForegroundColor $Color
}

function Write-OK   { param([string]$msg) Write-Host "  [OK] $msg" -ForegroundColor Green }
function Write-Warn { param([string]$msg) Write-Host "  [WARN] $msg" -ForegroundColor Yellow }
function Write-Fail { param([string]$msg) Write-Host "  [FAIL] $msg" -ForegroundColor Red }
function Write-Info { param([string]$msg) Write-Host $msg -ForegroundColor Cyan }

# ---------- 脚本自身目录（模板源）----------
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# ---------- 目标项目路径 ----------
if (-not $TargetDir) {
    Write-Host "请输入目标项目的绝对路径（直接回车则使用当前目录）：" -ForegroundColor Yellow
    $InputPath = Read-Host
    if (-not $InputPath) {
        $TargetDir = (Get-Location).Path
    } else {
        $TargetDir = $InputPath
    }
}

$TargetDir = (Resolve-Path $TargetDir -ErrorAction SilentlyContinue)?.Path
if (-not $TargetDir -or -not (Test-Path $TargetDir)) {
    Write-Fail "目标路径不存在：$TargetDir"
    exit 1
}

# ---------- 确认 ----------
Write-Host ""
Write-Color "==========================================" Cyan
Write-Color "   testcase-creator 初始化脚本 (Windows)" Cyan
Write-Color "==========================================" Cyan
Write-Host ""
Write-Host "[DIR] 模板来源：$ScriptDir"
Write-Host "[TARGET] 目标项目：$TargetDir"
Write-Host ""

$Confirm = Read-Host "确认将模板文件复制到上述目标路径？(y/N)"
if ($Confirm -notin @("y","Y")) {
    Write-Fail "已取消。"
    exit 0
}

Write-Host ""

# ---------- 复制函数 ----------
function Copy-Asset {
    param([string]$Src, [string]$Dst, [string]$Label)
    $FullSrc = (Resolve-Path $Src -ErrorAction SilentlyContinue).Path
    $FullDst = (Resolve-Path $Dst -ErrorAction SilentlyContinue).Path
    if ($FullSrc -and $FullDst -and $FullSrc -eq $FullDst) {
        Write-OK "目标与源相同，无需复制：$Label"
        return
    }

    $DstDir = Split-Path -Parent $Dst
    if (-not (Test-Path $DstDir)) {
        New-Item -ItemType Directory -Path $DstDir -Force | Out-Null
    }
    if ((Test-Path $Dst) -and -not $Force) {
        Write-Warn "$Label 已存在，跳过（加 -Force 参数强制覆盖）"
    } else {
        Copy-Item -Path $Src -Destination $Dst -Force
        Write-OK "已复制：$Label"
    }
}

# ---------- Cursor Skill ----------
Write-Info "-> 正在复制 Cursor Skill..."
Copy-Asset "$ScriptDir\.cursor\skills\testcase-creator\skill.md" `
           "$TargetDir\.cursor\skills\testcase-creator\skill.md" `
           ".cursor\skills\testcase-creator\skill.md"

# ---------- Claude Code 命令 ----------
Write-Host ""
Write-Info "-> 正在复制 Claude Code 命令..."
Copy-Asset "$ScriptDir\.claude\commands\testcase-creator.md" `
           "$TargetDir\.claude\commands\testcase-creator.md" `
           ".claude\commands\testcase-creator.md"

# ---------- 测试资产目录 ----------
Write-Host ""
Write-Info "-> 正在复制测试资产目录..."

$Assets = @(
    @{ S = ".testcase-assets\checkpoints-index.md";        D = ".testcase-assets\checkpoints-index.md" },
    @{ S = ".testcase-assets\review-expectations-index.md"; D = ".testcase-assets\review-expectations-index.md" },
    @{ S = ".testcase-assets\templates\testcase-table.md"; D = ".testcase-assets\templates\testcase-table.md" },
    @{ S = ".testcase-assets\templates\otp-schema.json";   D = ".testcase-assets\templates\otp-schema.json" },
    @{ S = ".testcase-assets\project.config.md";           D = ".testcase-assets\project.config.md" }
)

foreach ($a in $Assets) {
    Copy-Asset "$ScriptDir\$($a.S)" "$TargetDir\$($a.D)" $a.D
}

# 创建 history 目录
$HistoryDir = "$TargetDir\.testcase-assets\history"
if (-not (Test-Path $HistoryDir)) {
    New-Item -ItemType Directory -Path $HistoryDir -Force | Out-Null
    Write-OK "已创建：.testcase-assets\history\ 目录"
}

# ---------- 导出脚本 ----------
Write-Host ""
Write-Info "-> 正在复制导出脚本..."
Copy-Asset "$ScriptDir\.testcase-assets\scripts\export_excel.py" `
           "$TargetDir\.testcase-assets\scripts\export_excel.py" `
           ".testcase-assets\scripts\export_excel.py"
Copy-Asset "$ScriptDir\.testcase-assets\scripts\export_xmind.py" `
           "$TargetDir\.testcase-assets\scripts\export_xmind.py" `
           ".testcase-assets\scripts\export_xmind.py"

# ---------- 纯对话工具指南 ----------
Write-Host ""
Write-Info "-> 正在复制 Codex/纯对话工具指南..."
Copy-Asset "$ScriptDir\TESTCASE_GUIDE.md" "$TargetDir\TESTCASE_GUIDE.md" "TESTCASE_GUIDE.md"

# ---------- 生成 .claude/settings.local.json ----------
Write-Host ""
Write-Info "-> 正在生成 .claude\settings.local.json（根据当前用户动态写入路径）..."

$ClaudeDir = "$TargetDir\.claude"
if (-not (Test-Path $ClaudeDir)) {
    New-Item -ItemType Directory -Path $ClaudeDir -Force | Out-Null
}

$SettingsFile = "$ClaudeDir\settings.local.json"

# 检测是否安装了 WSL
$UseWSL = $false
try {
    $WslCheck = wsl --status 2>&1
    if ($LASTEXITCODE -eq 0) { $UseWSL = $true }
} catch {}

if ($UseWSL) {
    # WSL 环境：路径转换为 /mnt/c/Users/... 格式
    $WinUser = $env:USERNAME
    $HomePath = "/mnt/c/Users/$WinUser"
    Write-OK "检测到 WSL，使用 Linux 风格路径：$HomePath"
} else {
    # 纯 Windows：使用 Windows 路径（Claude Code on Windows 原生模式）
    $HomePath = $env:USERPROFILE -replace '\\', '/'
    Write-Warn "未检测到 WSL，使用 Windows 路径：$HomePath"
    Write-Host "         如需 PDF 读取功能，建议安装 WSL 并在其中运行 Claude Code" -ForegroundColor Yellow
}

$SettingsContent = @"
{
  "permissions": {
    "allow": [
      "Bash(pdftotext $HomePath/Downloads/*.pdf -)",
      "Bash(pdftotext $HomePath/Desktop/*.pdf -)",
      "Bash(python3 .testcase-assets/scripts/export_excel.py .testcase-assets/history/export_data_*.json .testcase-assets/history/testcases_*.xlsx)",
      "Bash(python3 .testcase-assets/scripts/export_xmind.py .testcase-assets/history/export_data_*.json .testcase-assets/history/testcases_*.xmind)"
    ]
  }
}
"@

Set-Content -Path $SettingsFile -Value $SettingsContent -Encoding UTF8
Write-OK "已生成 .claude\settings.local.json"

# ---------- 完成摘要 ----------
Write-Host ""
Write-Color "==========================================" Cyan
Write-Color " 初始化完成！" Green
Write-Color "==========================================" Cyan
Write-Host ""
Write-Host "[DIR] 目标项目结构："
Write-Host "   $TargetDir\"
Write-Host "   +-- .cursor\skills\testcase-creator\skill.md"
Write-Host "   +-- .claude\commands\testcase-creator.md"
Write-Host "   +-- TESTCASE_GUIDE.md"
Write-Host "   +-- .testcase-assets\"
Write-Host "       +-- project.config.md     (项目配置，首次使用前必填)"
Write-Host "       +-- checkpoints-index.md"
Write-Host "       +-- review-expectations-index.md"
Write-Host "       +-- templates\"
Write-Host "       +-- scripts\"
Write-Host "       |   +-- export_excel.py"
Write-Host "       |   +-- export_xmind.py"
Write-Host "       +-- history\"
Write-Host ""
Write-Host ">> 下一步："
Write-Color "   1. [必填] 编辑 .testcase-assets\project.config.md" Green
Write-Color "   2. [必填] 根据实际业务补充 .testcase-assets\checkpoints-index.md" Green
Write-Color "   3. [环境] 安装 Excel 导出依赖：pip install openpyxl" Yellow
Write-Color "   4. [环境] 如需读取 PDF：winget install poppler  (或在 WSL 中 apt install poppler-utils)" Yellow
Write-Color "   5. [环境] 如需读取 DOCX：pip install python-docx" Yellow
Write-Host "   6. Cursor 用户：输入 /testcase-creator 触发"
Write-Host "   7. Claude Code 用户：输入 /testcase-creator 触发"
Write-Host "   8. ChatGPT 用户：复制 TESTCASE_GUIDE.md 内容到对话开头"
Write-Host ""
Write-Color "[TIP] 如需强制覆盖已有文件，请加 -Force 参数重新运行" Yellow
Write-Host ""
