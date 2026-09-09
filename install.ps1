#Requires -Version 5.1
param([switch]$Force)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Src = Join-Path $Root ".agents\skills"
$Targets = @(".claude\skills", ".opencode\skills", ".gemini\skills")
# ponytail: minimal copy, sha256 compare only; add logging/parallel when skill count grows
function Same($a, $b) {
  if (!(Test-Path $b)) { return $false }
  return (Get-FileHash "$a" -Algorithm SHA256).Hash -eq (Get-FileHash "$b" -Algorithm SHA256).Hash
}
if (!$Force) { Write-Host "DRY-RUN: rerun with -Force to apply."; }
Get-ChildItem "$Src" -Directory | ForEach-Object {
  foreach ($t in $Targets) {
    $dest = Join-Path $Root (Join-Path $t $_.Name)
    $files = Get-ChildItem $_.FullName -Recurse -File
    foreach ($f in $files) {
      $rel = $f.FullName.Substring($_.FullName.Length)
      $dp = Join-Path $dest $rel.TrimStart('\','/')
      if (!$Force) { Write-Host "WOULD-COPY: `"$($f.FullName)`" -> `"$dp`""; continue }
      if (Test-Path "$dp") {
        if (Same "$($f.FullName)" "$dp") { continue }
        $bak = "$dp.bak-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
        Copy-Item "$dp" "$bak"
      }
      New-Item -ItemType Directory -Force -Path (Split-Path "$dp") | Out-Null
      Copy-Item "$($f.FullName)" "$dp" -Force
      Write-Host "COPIED: `"$($f.FullName)`" -> `"$dp`""
    }
  }
}
Write-Host "DONE (dry-run=$(-not $Force))"
