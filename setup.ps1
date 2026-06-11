<#
.SYNOPSIS
    One-click setup for Confluence MCP Server.
.DESCRIPTION
    Fully automated setup:
      1. Validates Python >= 3.10
      2. Creates virtual environment
      3. Installs dependencies
      4. Prompts for PAT (or accepts -Pat parameter)
      5. Validates PAT against Confluence API
      6. Verifies MCP server loads correctly
      7. Safely injects config into VS Code settings.json

    After running, reload VS Code. That is it.
.NOTES
    .\setup.ps1
    .\setup.ps1 -Pat "YOUR_TOKEN_HERE"
#>

param(
    [string]$Url,
    [string]$Pat
)

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
$failed = $false

function Write-Step { param($num, $total, $msg) Write-Host "[$num/$total] $msg" -ForegroundColor Yellow }
function Write-Ok   { param($msg) Write-Host "  $msg" -ForegroundColor Green }
function Write-Warn { param($msg) Write-Host "  $msg" -ForegroundColor DarkYellow }
function Write-Err  { param($msg) Write-Host "  ERROR: $msg" -ForegroundColor Red }
function Write-Info { param($msg) Write-Host "  $msg" -ForegroundColor White }
function Write-Dim  { param($msg) Write-Host "  $msg" -ForegroundColor DarkGray }

Write-Host "" 
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  Confluence MCP Server - Setup                             " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host ""

$totalSteps = 7

Write-Step 1 $totalSteps "Checking Python..."

$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) {
    Write-Err "Python not found in PATH."
    Write-Info "Install Python 3.10+ from https://www.python.org/downloads/"
    Write-Info "Make sure to check 'Add Python to PATH' during installation."
    exit 1
}

$pyVerRaw = (python --version 2>&1).ToString().Trim()
$pyVerMatch = [regex]::Match($pyVerRaw, '(\d+)\.(\d+)\.(\d+)')
if ($pyVerMatch.Success) {
    $major = [int]$pyVerMatch.Groups[1].Value
    $minor = [int]$pyVerMatch.Groups[2].Value
    if ($major -lt 3 -or ($major -eq 3 -and $minor -lt 10)) {
        Write-Err "$pyVerRaw is too old. Python 3.10+ required."
        exit 1
    }
    Write-Ok $pyVerRaw
} else {
    Write-Warn "Could not parse Python version: $pyVerRaw - continuing anyway"
}

Write-Step 2 $totalSteps "Setting up virtual environment..."

$venvPath = Join-Path $Root ".venv"
$venvPython = Join-Path $venvPath "Scripts\python.exe"
$venvPip = Join-Path $venvPath "Scripts\pip.exe"

if (Test-Path $venvPython) {
    Write-Ok "Virtual environment exists - reusing"
} else {
    if (Test-Path $venvPath) {
        Write-Warn "Broken .venv detected - recreating..."
        Remove-Item -Recurse -Force $venvPath
    }
    python -m venv $venvPath 2>&1 | Out-Null
    if (-not (Test-Path $venvPython)) {
        Write-Err "Failed to create virtual environment."
        Write-Info "Try: python -m venv .venv"
        exit 1
    }
    Write-Ok "Created .venv"
}

Write-Step 3 $totalSteps "Installing dependencies..."

$reqFile = Join-Path $Root "requirements.txt"
if (-not (Test-Path $reqFile)) {
    Write-Err "requirements.txt not found in $Root"
    exit 1
}

$ErrorActionPreference = "Continue"
& $venvPip install -q -r $reqFile 2>&1 | Out-Null
$pipExit = $LASTEXITCODE
$ErrorActionPreference = "Stop"
if ($pipExit -ne 0) {
    Write-Err "pip install failed. Run manually: .venv\Scripts\pip install -r requirements.txt"
    exit 1
}
Write-Ok "Dependencies installed"

Write-Step 4 $totalSteps "Confluence URL & Personal Access Token..."

# ── Confluence URL ──────────────────────────────────────────────────────────
if (-not $Url) {
    Write-Host ""
    Write-Info "Enter your Confluence base URL (e.g. https://your-company.atlassian.net)"
    Write-Info "For Confluence Server / Data Center use your internal URL."
    Write-Host ""
    $Url = Read-Host "  Confluence URL"
    Write-Host ""
}

$Url = $Url.Trim().TrimEnd('/')
if (-not $Url -or -not $Url.StartsWith('http')) {
    Write-Err "Invalid URL '$Url'. Must start with http:// or https://."    
    exit 1
}
Write-Ok "Confluence URL: $Url"

$patUrl = "$Url/plugins/personalaccesstokens/usertokens.action"

# ── Personal Access Token ───────────────────────────────────────────────────
if (-not $Pat) {
    Write-Host ""
    Write-Info "A Confluence Personal Access Token is required."
    Write-Info "Create one here: $patUrl"
    Write-Host ""
    $Pat = Read-Host "  Enter your PAT"
    Write-Host ""
}

if (-not $Pat -or $Pat.Trim().Length -lt 10) {
    Write-Err "No valid PAT provided. Cannot continue."
    Write-Info "Get your PAT from: $patUrl"
    exit 1
}

$Pat = $Pat.Trim()
Write-Ok "PAT received"

Write-Step 5 $totalSteps "Validating PAT against Confluence..."

$ErrorActionPreference = "Continue"
$validateResult = & $venvPython -c "
import httpx, sys
pat = sys.argv[1]
try:
    r = httpx.get(f'{sys.argv[2]}/rest/api/user/current',
                  headers={'Authorization': f'Bearer {pat}', 'Accept': 'application/json'},
                  verify=False, timeout=10)
    if r.status_code == 200:
        name = r.json().get('displayName', 'Unknown')
        print(f'OK|{name}')
    else:
        print(f'FAIL|HTTP {r.status_code}')
except Exception as e:
    print(f'FAIL|{e}')
" $Pat $Url 2>$null
$ErrorActionPreference = "Stop"

if ($validateResult -and $validateResult.StartsWith("OK|")) {
    $userName = $validateResult.Substring(3)
    Write-Ok "Authenticated as: $userName"
} elseif ($validateResult -and $validateResult.StartsWith("FAIL|")) {
    $reason = $validateResult.Substring(5)
    Write-Err "PAT validation failed: $reason"
    Write-Info "Check your PAT at: $patUrl"
    exit 1
} else {
    Write-Warn "Could not reach Confluence - VPN? Continuing with unverified PAT..."
}

Write-Step 6 $totalSteps "Verifying MCP server..."

$serverPy = Join-Path $Root "server.py"
if (-not (Test-Path $serverPy)) {
    Write-Err "server.py not found in $Root"
    exit 1
}

$verifyResult = & $venvPython -c "
import sys, re, pathlib
root = pathlib.Path(sys.argv[1]).parent
try:
    tool_names = []
    for f in (root / 'confluence_mcp').rglob('*.py'):
        src = f.read_text(encoding='utf-8')
        tool_names += re.findall(r'@mcp\.tool\(\)\ndef (\w+)', src)
    if not tool_names:
        print('FAIL|No tools found in confluence_mcp package')
    else:
        print(f'OK|{len(tool_names)}|' + ','.join(sorted(tool_names)))
except Exception as e:
    print(f'FAIL|{e}')
" $serverPy 2>$null
$ErrorActionPreference = "Stop"
if ($verifyResult -and $verifyResult.StartsWith("OK|")) {
    $parts = $verifyResult.Split('|')
    $toolCount = $parts[1]
    $toolNames = $parts[2] -split ','
    $writeTools = @('update_page','prepend_to_page','append_to_page','create_page',
                    'add_comment','add_label','upload_attachment',
                    'create_drawio_diagram','preview_drawio_diagram','publish_drawio_diagram')
    Write-Ok "$toolCount tools loaded:"
    foreach ($t in $toolNames) {
        if ($t -in $writeTools) {
            Write-Dim "  [W] $t"
        } else {
            Write-Dim "  [R] $t"
        }
    }
} else {
    $reason = if ($verifyResult) { $verifyResult.Substring(5) } else { "Unknown error" }
    Write-Err "Server failed to load: $reason"
    exit 1
}

Write-Step 7 $totalSteps "Configuring VS Code..."

$extDir = Join-Path $env:USERPROFILE ".vscode\extensions"
$hasDrawio = (Test-Path $extDir) -and (Get-ChildItem $extDir -Directory -Filter "hediet.vscode-drawio-*" -ErrorAction SilentlyContinue)
if ($hasDrawio) {
    Write-Ok "Draw.io extension already installed"
} else {
    Write-Warn "Draw.io extension not found - install it for diagram preview:"
    Write-Info "  Extensions sidebar (Ctrl+Shift+X), search 'hediet.vscode-drawio', Install"
}

$mcpJsonPath = Join-Path $env:APPDATA "Code\User\mcp.json"

$mcpEntry = @{
    command = ($venvPython -replace '\\', '/')
    args    = @(($serverPy -replace '\\', '/'))
    env     = @{
        CONFLUENCE_URL = $Url
        CONFLUENCE_PAT = $Pat
    }
    type    = "stdio"
}

try {
    if (Test-Path $mcpJsonPath) {
        $raw = Get-Content $mcpJsonPath -Raw -Encoding UTF8
        $mcpJson = $raw | ConvertFrom-Json

        $backupPath = "$mcpJsonPath.backup-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
        Copy-Item $mcpJsonPath $backupPath
        Write-Dim "Backup: $backupPath"

        if (-not $mcpJson.servers) {
            $mcpJson | Add-Member -NotePropertyName 'servers' -NotePropertyValue @{} -Force
        }

        $mcpJson.servers | Add-Member -NotePropertyName 'confluence' -NotePropertyValue $mcpEntry -Force

        $mcpJson | ConvertTo-Json -Depth 10 | Set-Content $mcpJsonPath -Encoding UTF8
        Write-Ok "Updated mcp.json with 'confluence' server"
    } else {
        $mcpJson = @{
            servers = @{ confluence = $mcpEntry }
            inputs  = @()
        }
        $mcpDir = Split-Path $mcpJsonPath
        if (-not (Test-Path $mcpDir)) { New-Item -ItemType Directory -Path $mcpDir -Force | Out-Null }
        $mcpJson | ConvertTo-Json -Depth 10 | Set-Content $mcpJsonPath -Encoding UTF8
        Write-Ok "Created mcp.json with 'confluence' server"
    }
    Write-Dim "Path: $mcpJsonPath"
} catch {
    Write-Err "Failed to update mcp.json: $_"
    Write-Info "You may need to add the config manually."
    $failed = $true
}

Write-Host ""
if ($failed) {
    Write-Host "==========================================================" -ForegroundColor Red
    Write-Host "  Setup completed with warnings - check errors above       " -ForegroundColor Red
    Write-Host "==========================================================" -ForegroundColor Red
} else {
    Write-Host "==========================================================" -ForegroundColor Green
    Write-Host "  Setup complete!                                          " -ForegroundColor Green
    Write-Host "==========================================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "  Next steps:" -ForegroundColor White
    Write-Host "    1. Reload VS Code:  Ctrl+Shift+P, then 'Developer: Reload Window'" -ForegroundColor Yellow
    Write-Host "    2. Install recommended extensions when prompted" -ForegroundColor Yellow
    Write-Host "       (includes draw.io editor for diagram preview)" -ForegroundColor DarkGray
    Write-Host ""
}
Write-Host ""
