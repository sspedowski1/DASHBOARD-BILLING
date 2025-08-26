
"""
Exports payer summary and denial trends from parsed ERA.
This is a stub that generates mock data; replace with real aggregation.
"""
import json, os, random

def export_summaries(out_dir:str):
    os.makedirs(out_dir, exist_ok=True)
    payer_summary = {
        "rows":[
            {"payer":"Medicare","clean_rate":0.91,"top_denial":"Missing -25","avg_dollars":126,"delta":"+2%"},
            {"payer":"BCBS","clean_rate":0.78,"top_denial":"ICD mismatch","avg_dollars":118,"delta":"-1%"},
            {"payer":"Priority Health","clean_rate":0.84,"top_denial":"Frequency edits","avg_dollars":119,"delta":"+1%"},
        ]
    }
    with open(os.path.join(out_dir,"payer_summary.json"),"w") as f: json.dump(payer_summary, f, indent=2)

    months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
    denial_trends = [{"month":m, "rate": round(random.uniform(0.09,0.16),2)} for m in months]
    with open(os.path.join(out_dir,"denial_trends.json"),"w") as f: json.dump(denial_trends, f, indent=2)

if __name__ == "__main__":
    export_summaries("./output")
