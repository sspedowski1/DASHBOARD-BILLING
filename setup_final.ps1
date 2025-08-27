# setup_final.ps1
# Run from: C:\Users\ma\Documents\DASHBOARD-BILLING
# Purpose: finalize repo merge, ensure incentives file, run generators, copy JSON to UI

$ErrorActionPreference = "Stop"

# --- Resolve key paths based on script location (robust if you run from anywhere) ---
if ($PSScriptRoot) {
  $Backend = $PSScriptRoot
} else {
  $Backend = Convert-Path "."
}
$Docs = Split-Path -Parent $Backend
$Incentives = Join-Path $Docs "2025-INCENTIVE"
$IncentivesWithSpace = Join-Path $Docs "2025 INCENTIVE"
$IncentivesOut = Join-Path $Incentives "output"
$IncentivesFile = Join-Path $IncentivesOut "incentive_snapshot.json"
$Frontend = Join-Path $Docs "bcfm-dashboard"
$FrontendData = Join-Path $Frontend "src\data"
$BackendOutput = Join-Path $Backend "output"
$BackendEraRootFile = Join-Path $Backend "export_remittance_json.py"
$BackendEraTargetDir = Join-Path $Backend "src\era_pipeline"
$BackendEraTarget = Join-Path $BackendEraTargetDir "export_remittance_json.py"
$IngestFile = Join-Path $Backend "src\integrations\incentives_ingest.py"

Write-Host "`n== Repo merge setup starting ==" -ForegroundColor Cyan

# --- 0) Ensure folders exist ---
New-Item -ItemType Directory -Force -Path $BackendOutput | Out-Null

# --- 1) Normalize incentives repo name (space -> hyphen) ---
if (Test-Path $IncentivesWithSpace) {
  Write-Host "Renaming '2025 INCENTIVE' -> '2025-INCENTIVE'" -ForegroundColor Yellow
  if (Test-Path $Incentives) { Remove-Item -Recurse -Force $Incentives }
  Rename-Item -Path $IncentivesWithSpace -NewName "2025-INCENTIVE"
}

# --- 2) Ensure incentives repo + output file ---
if (!(Test-Path $Incentives)) {
  Write-Host "Cloning 2025-INCENTIVE (public) into $Incentives" -ForegroundColor Yellow
  git clone https://github.com/sspedowski1/2025-INCENTIVE.git $Incentives | Out-Null
}
New-Item -ItemType Directory -Force -Path $IncentivesOut | Out-Null

if (!(Test-Path $IncentivesFile)) {
  Write-Host "Creating minimal incentive_snapshot.json" -ForegroundColor Yellow
  @'
{
  "total_paid": 22500,
  "by_program": [
    {"name": "MA HCC gap closures", "amount": 14200},
    {"name": "Quality Gap Closures", "amount": 6800},
    {"name": "Chronic Care Mgmt Bonus", "amount": 1500}
  ],
  "by_provider": [
    {"npi": "1234567890", "amount": 12000},
    {"npi": "0987654321", "amount": 10500}
  ]
}
'@ | Set-Content -Path $IncentivesFile -Encoding UTF8
}

# --- 3) Move real ERA exporter into starter path (if present) ---
if (Test-Path $BackendEraRootFile) {
  New-Item -ItemType Directory -Force -Path $BackendEraTargetDir | Out-Null
  Write-Host "Moving export_remittance_json.py to src\era_pipeline (overwriting stub)" -ForegroundColor Yellow
  Move-Item -Force $BackendEraRootFile $BackendEraTarget
} else {
  Write-Host "No root export_remittance_json.py found — keeping starter stub." -ForegroundColor DarkGray
}

# --- 4) Ensure incentives_ingest uses sibling path (optional patch) ---
if (Test-Path $IngestFile) {
  $orig = Get-Content $IngestFile -Raw
  $patched = $orig -replace '(?s)ensure_incentive_snapshot\([^\)]*\)', 'ensure_incentive_snapshot("../2025-INCENTIVE/output/incentive_snapshot.json", "./output/incentive_snapshot.json")'
  if ($patched -ne $orig) {
    Copy-Item $IngestFile "$IngestFile.bak" -Force
    $patched | Set-Content $IngestFile -Encoding UTF8
    Write-Host "Patched incentives_ingest.py to use ../2025-INCENTIVE path (backup at incentives_ingest.py.bak)" -ForegroundColor Yellow
  } else {
    Write-Host "incentives_ingest.py already points to ../2025-INCENTIVE" -ForegroundColor DarkGray
  }
}

# --- 5) Run generator ---
$bat = Join-Path $Backend "scripts\run_all.bat"
Write-Host "Generating dashboard JSON (run_all)" -ForegroundColor Cyan
if (Test-Path $bat) {
  cmd /c $bat
} else {
  # try python via py launcher, then python
  $ran = $false
  try { & py ".\src\run_all.py"; $ran = $true } catch {}
  if (-not $ran) { python ".\src\run_all.py" }
}

# --- 6) Verify outputs ---
$expected = @(
  "kpi_snapshot.json",
  "payer_summary.json",
  "denial_trends.json",
  "claim_risk_scores.json",
  "incentive_snapshot.json"
)
$missing = @()
foreach ($f in $expected) {
  $p = Join-Path $BackendOutput $f
  if (Test-Path $p) {
    Write-Host (" ✔ " + $f) -ForegroundColor Green
  } else {
    Write-Host (" ✖ MISSING: " + $f) -ForegroundColor Red
    $missing += $f
  }
}

# --- 7) Copy to frontend (if exists) ---
if (Test-Path $FrontendData) {
  Copy-Item -Force (Join-Path $BackendOutput "*.json") $FrontendData
  Write-Host "Copied output JSON to $FrontendData" -ForegroundColor Green
} else {
  Write-Host "UI repo not found at $FrontendData — skipping copy (ok)." -ForegroundColor DarkGray
}

if ($missing.Count -gt 0) {
  Write-Host "`nCompleted with missing files. Scroll up for error messages." -ForegroundColor Yellow
  exit 1
} else {
  Write-Host "`nAll good. Outputs ready." -ForegroundColor Cyan
}
