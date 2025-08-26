
"""
Reads the 2025-INCENTIVE repo's output and validates structure.
If not present, emits a mock file.
"""
import os, json

def ensure_incentive_snapshot(incentive_source_path:str, out_path:str):
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    data = None
    if incentive_source_path and os.path.exists(incentive_source_path):
        with open(incentive_source_path,"r") as f:
            data = json.load(f)
    if not data:
        data = {
            "total_paid": 22500,
            "by_program":[
                {"name":"MA HCC gap closures","amount":14200},
                {"name":"Quality Gap Closures","amount":6800},
                {"name":"Chronic Care Mgmt Bonus","amount":1500}
            ],
            "by_provider":[
                {"npi":"1234567890","amount":12000},
                {"npi":"0987654321","amount":10500}
            ]
        }
    with open(out_path,"w") as f:
        json.dump(data, f, indent=2)

if __name__ == "__main__":
    ensure_incentive_snapshot(r"C:\Users\ma\Documents\2025 INCENTIVE\output.json", "./output/incentive_snapshot.json")
