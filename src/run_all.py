
"""
Generates dashboard JSON outputs using stubs + sample visits.
Replace individual generators with real logic as you integrate.
"""
import os, json, sys
from src.scrubber.ov_to_billing import ov_to_billing
from src.predict.denial_risk import batch_score
from src.era_pipeline.export_remittance_json import export_summaries
from src.integrations.incentives_ingest import ensure_incentive_snapshot

BASE = os.path.dirname(os.path.dirname(__file__))
sys.path.append(BASE)
sys.path.append(os.path.join(BASE, "src"))
OUT = os.path.join(BASE, "output")

def gen_kpis():
    kpis = {
        "payments_ytd": 142350,
        "denial_rate": 0.12,
        "days_to_pay": 18,
        "write_offs": 4230,
        "clean_rate": 0.88,
        "incentives_ytd": 22500
    }
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT,"kpi_snapshot.json"),"w") as f:
        json.dump(kpis, f, indent=2)

def gen_claims_and_risk():
    # Sample visits → scrubber → claim stubs → risk
    visits = json.load(open(os.path.join(BASE,"src","sample_visits.json"),"r"))
    suggestions = []
    for v in visits:
        sug = ov_to_billing(v)
        suggestions.append({"id": v.get("id"), "patient_id": v.get("patient_id"), "dos": v.get("dos"), **sug})
    with open(os.path.join(OUT,"scrubber_suggestions.json"),"w") as f:
        json.dump(suggestions, f, indent=2)

    claim_stubs = []
    for s in suggestions:
        cpts = [{"code": x["code"], "modifiers": x.get("modifiers",[])} for x in s["recommended_cpts"]]
        claim_stubs.append({"id": s["id"], "payer": "MC", "cpts": cpts, "icds": s["recommended_icds"]})
    risk = batch_score(claim_stubs, era_stats_path=None)
    with open(os.path.join(OUT,"claim_risk_scores.json"),"w") as f:
        json.dump(risk, f, indent=2)

def gen_payer_and_denials():
    export_summaries(OUT)

def gen_incentives():
    ensure_incentive_snapshot("../2025-INCENTIVE/output/incentive_snapshot.json", os.path.join(OUT,"incentive_snapshot.json"))

def main():
    gen_kpis()
    gen_claims_and_risk()
    gen_payer_and_denials()
    gen_incentives()
    print(f"JSON written to: {OUT}")

if __name__ == "__main__":
    main()
