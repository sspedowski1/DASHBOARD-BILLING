# DASHBOARD-BILLING — Starter Kit

This package gives you a clean baseline for your **backend/data** repo and mock JSON for your **bcfm-dashboard** UI.

## What’s inside
- `src/scrubber/ov_to_billing.py` — OV → CPT/ICD/modifier suggestions with lookback suppression & -25 logic.
- `src/predict/denial_risk.py` — simple risk scoring using rule hits + (optional) ERA stats.
- `src/cdi/elation_blocks.py` — CDI prompts (missing dx, time docs, HCC nudges).
- `src/era_pipeline/` — placeholders to parse ERA and export JSON summaries.
- `src/integrations/incentives_ingest.py` — normalizes the Incentives repo output.
- `src/schemas/*.json` — JSON Schemas for the UI files.
- `src/run_all.py` — generates example JSON in `/output`.
- `scripts/run_all.sh` and `scripts/run_all.bat` — convenience scripts.
- `/output` — generated mock JSON for your dashboard.
- `/FRONTEND_DATA_SAMPLE` — same JSON copies you can drop into `bcfm-dashboard/src/data/` during UI dev.

## Quick Start
1. Copy this folder into your `DASHBOARD-BILLING` repo (or unzip & merge).
2. (Optional) Put your incentives export at: `../2025-INCENTIVE/output/incentive_snapshot.json`.
3. Run one of:
   - **Windows:** `scripts\run_all.bat`
   - **Mac/Linux:** `bash scripts/run_all.sh`
4. Verify JSON files in `output/` — then copy them into your `bcfm-dashboard/src/data/`.

## Wire the UI
Point your UI to read these files (dev mode):
- `src/data/kpi_snapshot.json`
- `src/data/payer_summary.json`
- `src/data/denial_trends.json`
- `src/data/claim_risk_scores.json`
- `src/data/incentive_snapshot.json`

> Everything here is stubbed but runnable. Replace stubs with your real ERA exports step‑by‑step.
