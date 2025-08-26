
"""
CDI prompt generator for Elation Note-style blocks.
Produces lightweight prompts to nudge missing documentation/codes.
"""
from __future__ import annotations
from typing import Dict, Any, List

def cdi_prompts(note:Dict[str,Any]) -> List[Dict[str,str]]:
    text = (note.get("text") or "").lower()
    prompts = []
    if "ckd" in text and "n18.3" not in text:
        prompts.append({"type":"dx","message":"You mentioned CKD — add N18.30 staging if appropriate?"})
    if "phq" in text and "g0444" not in text:
        prompts.append({"type":"cpt","message":"PHQ documented — bill G0444 if ≥15 min and tool/score captured?"})
    if "advance care planning" in text and "99497" not in text:
        prompts.append({"type":"cpt","message":"ACP discussed — add 99497 if ≥16 minutes with consent/time?"})
    return prompts

if __name__ == "__main__":
    demo = {"text":"PHQ-9 performed; patient with CKD stage 3a. Advance care planning discussed."}
    print(cdi_prompts(demo))
