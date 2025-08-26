# --- SETTINGS ---
$Docs = "C:\Users\ma\Documents"
$Backend = Join-Path $Docs "DASHBOARD-BILLING"
$Incentives = Join-Path $Docs "2025-INCENTIVE"     # keep hyphen, not space
$IncentivesOut = Join-Path $Incentives "output"
$IncentivesFile = Join-Path $IncentivesOut "incentive_snapshot.json"
$Frontend = Join-Path $Docs "bcfm-dashboard"       # change if your UI repo is named differently
$FrontendData = Join-Path $Frontend "src\data"
$BackendOutput = Join-Path $Backend "output"
$BackendEraRootFile = Join-Path $Backend "export_remittance_json.py"                # your older/real script at repo root
$BackendEraTarget = Join-Path $Backend "src\era_pipeline\export_remittance_json.py" # starter location

Write-Host "`n== Step 0: Ensure we're in DASHBOARD-BILLING ==" -ForegroundColor Cyan
Set-Location $Backend

# --- Step 1: Ensure incentives repo + output folder exist ---
Write-Host "== Step 1: Prepare 2025-INCENTIVE structure ==" -ForegroundColor Cyan
if (!(Test-Path $Incentives)) {
  Write-Host "Cloning 2025-INCENTIVE..." -ForegroundColor Yellow
  git clone https://github.com/sspedowski1/2025-INCENTIVE.git $Incentives
}
New-Item -ItemType Directory -Force -Path $IncentivesOut | Out-Null

# If the incentives JSON doesn't exist, create minimal mock
if (!(Test-Path $IncentivesFile)) {
  Write-Host "Creating $IncentivesFile" -ForegroundColor Yellow
  $json = @'
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
'@
  $json | Set-Content -Path $IncentivesFile -Encoding UTF8
}

# --- Step 2: Move your real ERA exporter into starter path (if present) ---
Write-Host "== Step 2: Move ERA exporter (if you have one at repo root) ==" -ForegroundColor Cyan
if (Test-Path $BackendEraRootFile) {
  Write-Host "Moving $BackendEraRootFile -> $BackendEraTarget (overwrite)" -ForegroundColor Yellow
  Move-Item -Force $BackendEraRootFile $BackendEraTarget
} else {
  Write-Host "No root export_remittance_json.py found. Using starter version." -ForegroundColor DarkGray
}

# --- Step 3: Make sure incentives_ingest points to sibling repo path if needed ---
Write-Host "== Step 3: Verify incentives_ingest path ==" -ForegroundColor Cyan
$ingest = Join-Path $Backend "src\integrations\incentives_ingest.py"
if (Test-Path $ingest) {
  $content = Get-Content $ingest -Raw
  # If you customized the path earlier, skip. Otherwise ensure default sibling path is fine.
  # (No rewrite by default. If you want to hard-code full path, uncomment the next block.)
  # $content = $content -replace '\.\./2025-INCENTIVE/output/incentive_snapshot\.json', [Regex]::Escape($IncentivesFile)
  # $content | Set-Content $ingest -Encoding UTF8
  Write-Host "Using default sibling path ../2025-INCENTIVE/output/incentive_snapshot.json" -ForegroundColor DarkGray
}

# --- Step 4: Run the generator to write JSON into output/ ---
Write-Host "== Step 4: Generate dashboard JSON (scripts\run_all.bat) ==" -ForegroundColor Cyan
$bat = Join-Path $Backend "scripts\run_all.bat"
if (Test-Path $bat) {
  cmd /c $bat
} else {
  Write-Host "scripts\run_all.bat not found; calling Python directly" -ForegroundColor Yellow
  python ".\src\run_all.py"
}

# --- Step 5: Verify outputs exist ---
Write-Host "== Step 5: Verify outputs ==" -ForegroundColor Cyan
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
    Write-Host " ✔ $f" -ForegroundColor Green
  } else {
    Write-Host " ✖ MISSING: $f" -ForegroundColor Red
    $missing += $f
  }
}
if ($missing.Count -gt 0) {
  Write-Host "`nSome files are missing. Open the console output above for errors." -ForegroundColor Red
} else {
  Write-Host "`nAll expected JSON outputs are present." -ForegroundColor Green
}

# --- Step 6 (optional): Copy outputs into your UI repo's src/data ---
Write-Host "== Step 6: Copy to UI repo (if it exists) ==" -ForegroundColor Cyan
if (Test-Path $FrontendData) {
  Copy-Item -Force (Join-Path $BackendOutput "*.json") $FrontendData
  Write-Host "Copied JSON to $FrontendData" -ForegroundColor Green
} else {
  Write-Host "UI repo not found at $FrontendData — skip copy (ok for now)" -ForegroundColor DarkGray
}

Write-Host "`nDone." -ForegroundColor Cyan