
"""
OV → Billing (CPT/ICD/Modifiers) suggester.

Inputs example:
{
  "patient_id": "123",
  "dos": "2025-08-25",
  "visit_type": "OV",
  "mdm_level": "moderate",  # optional
  "time_minutes": 30,       # optional
  "procedures": ["cryotherapy"],  # free-text tags
  "complaints": ["depression screen"],
  "assessment_free_text": "CKD stage 3a ...",
  "icd_candidates": ["N18.30","Z13.31"],
  "history": { "recent_cpts":[{"code":"G0439","dos":"2025-01-10"}] },
  "previous_cpt_lookback_days": 365
}

Output example:
{
  "recommended_cpts": [
    {"code":"99214","modifiers":["25"],"reason":"E/M level by time 30 min + distinct problem on day of procedure"},
    {"code":"G0444","modifiers":[],"reason":"Depression screen documented ≥15 min"}
  ],
  "recommended_icds": ["F32.A","Z13.31","N18.30"],
  "missing_documentation": ["Add time statement for 99497 ..."],
  "conflicts": ["AWV + 99214 requires -25 and distinct problem-oriented work"]
}
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Any
from datetime import datetime, timedelta
import re

E_M_BY_TIME = [
    (40, "99215"),
    (30, "99214"),
    (20, "99213"),
    (10, "99212"),
]

MDM_TO_EM = {
    "straightforward":"99212",
    "low":"99213",
    "moderate":"99214",
    "high":"99215",
}

TIME_REQUIRED = {
    "G0444": 15,   # Depression screen
    "99497": 16,   # ACP first 30 min; CMS counts ≥16
    "99406": 3,    # Smoking cessation 3-10 min
}

ANNUAL_FREQ = {
    "G0439": 365,  # AWV subsequent
    "G0402": 365,  # Initial preventive physical exam (Welcome to Medicare)
}

def _pick_em_code(time_minutes:int|None, mdm_level:str|None) -> str|None:
    if time_minutes and time_minutes >= 10:
        for threshold, code in E_M_BY_TIME:
            if time_minutes >= threshold:
                return code
    if mdm_level:
        return MDM_TO_EM.get(mdm_level.lower())
    return None

def _contains(text:str, *keywords:str) -> bool:
    t = (text or "").lower()
    return all(k.lower() in t for k in keywords)

def _any_contains(items:List[str], *keywords:str) -> bool:
    return any(_contains(x, *keywords) for x in (items or []))

def _already_billed(history:dict, code:str, dos:str, lookback:int) -> bool:
    try:
        pivot = datetime.strptime(dos,"%Y-%m-%d")
    except:
        # attempt flexible parsing
        pivot = datetime.fromisoformat(dos[:10])
    days = timedelta(days=int(lookback))
    for row in (history or {}).get("recent_cpts", []):
        if row.get("code") == code:
            # if within lookback, treat as already billed
            try:
                prev = datetime.strptime(row.get("dos",""), "%Y-%m-%d")
            except:
                prev = datetime.fromisoformat(row.get("dos","")[:10])
            if abs((pivot - prev).days) <= lookback:
                return True
    return False

def ov_to_billing(payload:Dict[str,Any]) -> Dict[str,Any]:
    visit = payload
    dos = visit.get("dos") or ""
    lookback_days = int(visit.get("previous_cpt_lookback_days", 365))
    history = visit.get("history") or {}

    out = {
        "recommended_cpts": [],
        "recommended_icds": [],
        "missing_documentation": [],
        "conflicts": [],
    }

    # 1) Determine E/M
    em = _pick_em_code(visit.get("time_minutes"), visit.get("mdm_level"))
    if em:
        em_entry = {"code": em, "modifiers": [], "reason": "E/M selected by time/MDM"}
    else:
        em_entry = None

    # 2) Preventive/AWV logic suppressing E/M unless distinct
    visit_type = (visit.get("visit_type") or "").lower()
    is_awv = visit_type in {"awv","preventive"} or _any_contains(visit.get("complaints",[]),"annual wellness") 
    if is_awv:
        # suggest G0439 if within frequency and 'subsequent' implied; leave specificity to real rules
        if not _already_billed(history, "G0439", dos, ANNUAL_FREQ["G0439"]):
            out["recommended_cpts"].append({"code":"G0439","modifiers":[],"reason":"Annual Wellness Visit (subsequent) — within frequency"})
        # If distinct problem work exists (procedures or problem list), add -25 to E/M
        if em_entry:
            em_entry["modifiers"].append("25")
            em_entry["reason"] = (em_entry["reason"] + " + distinct problem on same day as AWV").strip()
            out["conflicts"].append("AWV + E/M requires -25 and distinct documentation.")
    # 3) Same-day procedure? Then -25 on E/M
    if visit.get("procedures"):
        if em_entry and "25" not in em_entry["modifiers"]:
            em_entry["modifiers"].append("25")
            em_entry["reason"] = (em_entry["reason"] + " + same-day procedure").strip()

    # Commit E/M if chosen
    if em_entry:
        out["recommended_cpts"].append(em_entry)

    # 4) Screenings & time-based services
    text_blob = " ".join([
        visit.get("assessment_free_text") or "",
        " ".join(visit.get("complaints") or [])
    ])

    # Depression screening (G0444)
    if _any_contains(visit.get("complaints",[]), "phq", "depression") or _contains(text_blob,"phq-9") or _contains(text_blob,"g0444"):
        out["recommended_cpts"].append({"code":"G0444","modifiers":[],"reason":"Depression screening documented"})
        if visit.get("time_minutes",0) < TIME_REQUIRED["G0444"]:
            out["missing_documentation"].append("Add time statement for G0444 (≥15 min, tool used, score).")

    # ACP (99497)
    if _contains(text_blob, "advance care planning") or _any_contains(visit.get("procedures",[]),"acp"):
        out["recommended_cpts"].append({"code":"99497","modifiers":[],"reason":"Advance care planning"})
        if visit.get("time_minutes",0) < TIME_REQUIRED["99497"]:
            out["missing_documentation"].append("Add time for 99497 (≥16 minutes, consent).")

    # 5) ICD suggestions: prefer provided candidates + enrich from free text
    icds = set(visit.get("icd_candidates") or [])
    if _contains(text_blob,"ckd"):
        icds.add("N18.30")
    if _contains(text_blob,"depression"):
        icds.add("F32.A")
        icds.add("Z13.31")  # screening encounter
    if is_awv:
        # prefer Z00.01 when abnormal findings documented
        if _contains(text_blob,"abnormal"):
            icds.add("Z00.01")
        else:
            icds.add("Z00.00")
    out["recommended_icds"] = sorted(icds)

    # 6) Frequency checks (suppress if already billed recently)
    pruned = []
    for c in out["recommended_cpts"]:
        freq = ANNUAL_FREQ.get(c["code"])
        if freq and _already_billed(history, c["code"], dos, freq):
            continue
        pruned.append(c)
    out["recommended_cpts"] = pruned

    # 7) Simple payer edit warnings (examples)
    if any(c["code"]=="G0444" for c in out["recommended_cpts"]) and "Z13.31" not in out["recommended_icds"]:
        out["conflicts"].append("G0444 typically requires Z13.31 as primary or supporting diagnosis.")

    # done
    return out

if __name__ == "__main__":
    demo = {
        "patient_id":"DEMO1",
        "dos":"2025-08-26",
        "visit_type":"OV",
        "mdm_level":"moderate",
        "time_minutes":30,
        "procedures": ["cryotherapy"],
        "complaints":["depression screen"],
        "assessment_free_text":"CKD stage 3a; PHQ-9 completed; abnormal affect.",
        "icd_candidates":["Z13.31"],
        "history":{"recent_cpts":[{"code":"G0439","dos":"2024-08-20"}]},
        "previous_cpt_lookback_days":365
    }
    import json
    print(json.dumps(ov_to_billing(demo), indent=2))
