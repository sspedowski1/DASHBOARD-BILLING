
"""
Predictive denial risk (rule-based starter).
Scores a claim stub based on common denial patterns.
"""
from __future__ import annotations
from typing import Dict, Any, List
import math, json, os

def _rule_hits(claim:Dict[str,Any]) -> List[str]:
    hits = []
    cpts = [c.get("code") for c in claim.get("cpts",[])]
    icds = claim.get("icds",[])
    # Missing -25 when E/M + procedure/screening same day
    if any(c.startswith("9921") for c in cpts) and any(x for x in cpts if x not in {"99212","99213","99214","99215"}):
        if not any("25" in (c.get("modifiers") or []) for c in claim.get("cpts",[])):
            hits.append("Missing -25 on same-day E/M + procedure")
    # G0444 without Z13.31
    if "G0444" in cpts and "Z13.31" not in icds:
        hits.append("G0444 missing Z13.31")
    # Z00.00 w/ problem-focused services
    if "Z00.00" in icds and any(c.startswith("9921") for c in cpts):
        hits.append("Z00.00 with problem-focused E/M")
    return hits

def score_claim(claim:Dict[str,Any], era_stats:Dict[str,Any]|None=None) -> Dict[str,Any]:
    hits = _rule_hits(claim)
    base = 0.15 * len(hits)
    # Optional ERA stats bump (e.g., payer-specific risk)
    payer = claim.get("payer","")
    if era_stats:
        bump = era_stats.get("payer_bumps",{}).get(payer,0)
    else:
        bump = 0
    risk = min(0.95, base + bump)
    return {"risk": round(risk,2), "top_factors": hits or ["No rule hits"]}

def batch_score(claims:List[Dict[str,Any]], era_stats_path:str|None=None):
    stats = None
    if era_stats_path and os.path.exists(era_stats_path):
        with open(era_stats_path,"r") as f:
            stats = json.load(f)
    out = []
    for c in claims:
        scored = score_claim(c, stats)
        out.append({"claim_stub_id": c.get("id","tmp"), **scored})
    return out

if __name__ == "__main__":
    demo_claims = [
        {"id":"12345","payer":"MC","cpts":[{"code":"99214","modifiers":[]},{"code":"G0444","modifiers":[]}],"icds":["F32.A"]},
        {"id":"12346","payer":"BCBS","cpts":[{"code":"99213","modifiers":["25"]},{"code":"G0444","modifiers":[]}],"icds":["Z13.31"]},
    ]
    print(json.dumps(batch_score(demo_claims), indent=2))
