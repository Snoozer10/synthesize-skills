#Requires -Version 5.1
<#
.SYNOPSIS
  Universal Multi-Agent Skills Installer (PowerShell native).
  Supports 7+ AI host ecosystems across Project-local and User-Global scopes.

.PARAMETER Scope
  "Project" (default) installs into active repository subdirectories.
  "Global" installs directly into user-level agent home directories (~/.gemini, ~/.claude, etc.).

.PARAMETER Target
  "Auto" (default) detects installed AI hosts on the current system.
  "All" installs into every known host target.
  Or provide a comma-separated list of host identifiers (e.g., "antigravity,claude,codex").

.PARAMETER Skill
  "all" (default) installs all canonical skills.
  Or provide a comma-separated list of skill names (e.g., "release-sync,skill-creator").

.PARAMETER Mode
  "Copy" (default) duplicates files with SHA-256 change detection and backup.
  "Link" creates directory junctions (where supported).

.PARAMETER Force
  Applies changes. Without this switch, execution runs in safe DRY-RUN mode.

.PARAMETER Rollback
  Rolls back the most recent installation using the saved transaction receipt.
#>
param(
  [ValidateSet("Project", "Global")][string]$Scope = "Project",
  [string]$Target = "Auto",
  [string]$Skill = "all",
  [ValidateSet("Copy", "Link")][string]$Mode = "Copy",
  [switch]$Force,
  [switch]$CommandsOnly,
  [switch]$Rollback
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Src = Join-Path $Root ".agents\skills"
$HomeDir = if ($env:USERPROFILE) { $env:USERPROFILE } else { $HOME }
$RuntimeDir = Join-Path $Root ".runtime"
$ReceiptFile = Join-Path $RuntimeDir "installed_receipt.json"

# --- Rollback Operation ---
if ($Rollback) {
  Write-Host "=== Rolling back skills installation ===" -ForegroundColor Yellow
  if (!(Test-Path $ReceiptFile)) {
    Write-Error "No receipt file found at '$ReceiptFile' to rollback."
    exit 1
  }

  $receipt = Get-Content $ReceiptFile -Raw | ConvertFrom-Json
  
  # 1. Restore backups
  if ($receipt.backups) {
    foreach ($b in $receipt.backups) {
      if (Test-Path $b.backup) {
        Copy-Item $b.backup $b.dest -Force
        Remove-Item $b.backup -Force
        Write-Host "  [RESTORED] $($b.dest) from backup" -ForegroundColor Green
      }
    }
  }

  # 2. Remove newly created files that had no backup
  if ($receipt.new_files) {
    foreach ($nf in $receipt.new_files) {
      if (Test-Path $nf) {
        Remove-Item $nf -Force
        Write-Host "  [REMOVED] $nf" -ForegroundColor DarkGray
      }
    }
  }

  Remove-Item $ReceiptFile -Force -ErrorAction SilentlyContinue
  Write-Host "ROLLBACK COMPLETE" -ForegroundColor Green
  exit 0
}

if (!(Test-Path $Src)) {
  Write-Error "Canonical skills directory not found at '$Src'"
  exit 1
}

# --- Concurrency Lock ---
if (!(Test-Path $RuntimeDir)) {
  New-Item -ItemType Directory -Force -Path $RuntimeDir | Out-Null
}
$LockFile = Join-Path $RuntimeDir "install.lock"

$lockTimeoutSeconds = 10
$sw = [System.Diagnostics.Stopwatch]::StartNew()
while (Test-Path $LockFile) {
  if ($sw.Elapsed.TotalSeconds -ge $lockTimeoutSeconds) {
    Write-Warning "Overriding stale installer lock (older than $lockTimeoutSeconds seconds)..."
    break
  }
  Write-Warning "Waiting for active installer lock to release..."
  Start-Sleep -Milliseconds 500
}
Set-Content -Path $LockFile -Value $PID -Force

try {
  # Host Target Map (Local relative to $Root, Global relative to $HomeDir)
  $HostRegistry = @{
    "agents"      = @{ Name = "Open Agents Standard";  Project = ".agents\skills";           Global = ".agents\skills" }
    "antigravity" = @{ Name = "Antigravity / Gemini"; Project = ".gemini\skills";           Global = ".gemini\skills" }
    "claude"      = @{ Name = "Claude Code / CLI";     Project = ".claude\skills";           Global = ".claude\skills" }
    "codex"       = @{ Name = "OpenAI Codex";          Project = ".codex\skills";            Global = ".codex\skills" }
    "opencode"    = @{ Name = "OpenCode";              Project = ".opencode\skills";         Global = ".config\opencode\skills" }
    "cursor"      = @{ Name = "Cursor";                Project = ".cursor\skills";           Global = ".cursor\skills" }
    "windsurf"    = @{ Name = "Codeium Windsurf";      Project = ".windsurf\skills";         Global = ".codeium\windsurf\skills" }
    "copilot"     = @{ Name = "GitHub Copilot";        Project = ".copilot\skills";          Global = ".copilot\skills" }
  }

  # Resolve selected targets
  $SelectedHosts = @()
  if ($Target -eq "All") {
    $SelectedHosts = @($HostRegistry.Keys)
  } elseif ($Target -eq "Auto") {
    $SelectedHosts += "agents"

    if ($Scope -eq "Global") {
      if (Test-Path (Join-Path $HomeDir ".gemini"))           { $SelectedHosts += "antigravity" }
      if (Test-Path (Join-Path $HomeDir ".claude"))           { $SelectedHosts += "claude" }
      if (Test-Path (Join-Path $HomeDir ".codex"))            { $SelectedHosts += "codex" }
      if (Test-Path (Join-Path $HomeDir ".config\opencode"))  { $SelectedHosts += "opencode" }
      if (Test-Path (Join-Path $HomeDir ".cursor"))           { $SelectedHosts += "cursor" }
      if (Test-Path (Join-Path $HomeDir ".codeium\windsurf")) { $SelectedHosts += "windsurf" }
      if (Test-Path (Join-Path $HomeDir ".copilot"))          { $SelectedHosts += "copilot" }
    } else {
      foreach ($k in $HostRegistry.Keys) {
        $projRel = $HostRegistry[$k].Project
        if (Test-Path (Join-Path $Root $projRel)) {
          if ($SelectedHosts -notcontains $k) { $SelectedHosts += $k }
        }
      }
      if ($SelectedHosts.Count -le 1) {
        $SelectedHosts += @("claude", "opencode", "antigravity")
      }
    }
  } else {
    $parts = $Target -split "," | ForEach-Object { $_.Trim().ToLower() }
    foreach ($p in $parts) {
      if ($HostRegistry.ContainsKey($p)) {
        $SelectedHosts += $p
      } else {
        Write-Warning "Unknown host '$p' ignored. Available: $($HostRegistry.Keys -join ', ')"
      }
    }
  }

  $SelectedHosts = $SelectedHosts | Select-Object -Unique

  $AvailableSkills = Get-ChildItem "$Src" -Directory
  $Skills = $AvailableSkills
  if ($Skill -ne "all") {
    $requestedSkills = $Skill -split "," | ForEach-Object { $_.Trim().ToLower() } | Where-Object { $_ -ne "" }
    $validNames = $AvailableSkills | ForEach-Object { $_.Name }
    $filteredSkills = @()
    foreach ($req in $requestedSkills) {
      $match = $AvailableSkills | Where-Object { $_.Name -eq $req }
      if ($match) {
        $filteredSkills += $match
      } else {
        Write-Error "Skill '$req' not found in canonical skills directory '$Src'. Available: $($validNames -join ', ')"
        exit 1
      }
    }
    $Skills = $filteredSkills
  }

  Write-Host "=== Universal Multi-Agent Skills Installer ===" -ForegroundColor Cyan
  Write-Host "Scope:   $Scope"
  Write-Host "Targets: $($SelectedHosts -join ', ')"
  Write-Host "Skills:  $($Skills.Name -join ', ')"
  Write-Host "Mode:    $Mode"
  Write-Host "Action:  $(if ($Force) { 'APPLYING CHANGES' } else { 'DRY-RUN (use -Force to apply)' })"
  Write-Host ""

  function SameFile($a, $b) {
    if (!(Test-Path $b)) { return $false }
    return (Get-FileHash "$a" -Algorithm SHA256).Hash -eq (Get-FileHash "$b" -Algorithm SHA256).Hash
  }

  $TotalCopied = 0
  $TotalSkipped = 0

  $ReceiptData = @{
    timestamp  = (Get-Date).ToString("o")
    scope      = $Scope
    targets    = $SelectedHosts
    skills     = @($Skills | ForEach-Object { $_.Name })
    installed  = @()
    backups    = @()
    new_files  = @()
  }

  foreach ($hostKey in $SelectedHosts) {
    $hostDef = $HostRegistry[$hostKey]
    $targetBase = if ($Scope -eq "Global") {
      Join-Path $HomeDir $hostDef.Global
    } else {
      Join-Path $Root $hostDef.Project
    }

    Write-Host "--> Target: $($hostDef.Name) [$hostKey]" -ForegroundColor Yellow
    Write-Host "    Directory: $targetBase"

    foreach ($s in $Skills) {
      $destSkillDir = Join-Path $targetBase $s.Name
      $files = Get-ChildItem $s.FullName -Recurse -File

      foreach ($f in $files) {
        if ($f.FullName -match "\\__pycache__\\" -or $f.Extension -eq ".pyc") {
          continue
        }

        $rel = $f.FullName.Substring($s.FullName.Length).TrimStart('\','/')
        $destFilePath = Join-Path $destSkillDir $rel

        if (!$Force) {
          Write-Host "  [WOULD-COPY] `"$($f.Name)`" -> `"$destFilePath`""
          $TotalCopied++
          continue
        }

        $existed = Test-Path $destFilePath
        if ($existed) {
          if (SameFile "$($f.FullName)" "$destFilePath") {
            $TotalSkipped++
            continue
          }
          $bak = "$destFilePath.bak-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
          Copy-Item "$destFilePath" "$bak" -Force
          $ReceiptData.backups += @{ dest = $destFilePath; backup = $bak }
        } else {
          $ReceiptData.new_files += $destFilePath
        }

        $destParent = Split-Path $destFilePath -Parent
        if (!(Test-Path $destParent)) {
          New-Item -ItemType Directory -Force -Path $destParent | Out-Null
        }

        $stagingPath = "$destFilePath.tmp.$PID"
        Copy-Item "$($f.FullName)" "$stagingPath" -Force
        Move-Item "$stagingPath" "$destFilePath" -Force
        $ReceiptData.installed += $destFilePath
        Write-Host "  [INSTALLED] `"$($f.Name)`" -> `"$destFilePath`"" -ForegroundColor Green
        $TotalCopied++
      }
    }
  }

  if ($Force) {
    $json = $ReceiptData | ConvertTo-Json -Depth 5
    $utf8NoBom = New-Object System.Text.UTF8Encoding $false
    [System.IO.File]::WriteAllText($ReceiptFile, $json, $utf8NoBom)
  }

  Write-Host ""
  Write-Host "Summary: $TotalCopied processed, $TotalSkipped identical skipped. (DryRun=$(-not $Force))" -ForegroundColor Cyan
}
finally {
  Remove-Item $LockFile -Force -ErrorAction SilentlyContinue
}
