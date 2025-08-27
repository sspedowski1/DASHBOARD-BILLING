import os
import fitz
import pandas as pd
import re
import json
from datetime import datetime, timezone

# ---- PATH SETUP ----
BASE_PATH = os.path.dirname(__file__)
SOURCE_PDF = os.path.join(BASE_PATH, "ERA COPIES 2025")
OUTPUT_DIR = os.path.join(BASE_PATH, "output")
EXCEL_FILE = os.path.join(BASE_PATH, "remittance_summary.xlsx")
LOG_FILE = os.path.join(BASE_PATH, "processed_files.txt")

# ---- PAYER MAPPING ----
PAYER_MAP = {
    "HUMANA": "Humana",
    "BLUE CARE NETWORK": "BCN", 
    "BCBSM": "BCBS",
    "BLUE CROSS": "BCBS",
    "UHC": "UHC",
    "UNITED": "UHC",
    "TRICARE": "Tricare",
    "PRIORITY HEALTH": "Priority Health"
}

def get_processed_files():
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f:
            return set(f.read().splitlines())
    return set()

def detect_payer(text):
    for keyword, payer in PAYER_MAP.items():
        if keyword in text.upper()[:1000]:
            return payer
    return "Unknown"

def parse_service_date(date_str):
    try:
        parts = date_str.split()
        if len(parts) == 2:
            return datetime.strptime(parts[1], "%m%d%y")
    except (ValueError, AttributeError):
        pass
    return pd.NaT

def process_pdfs():
    processed = get_processed_files()
    pattern = re.compile(
        r"NAME\s+(?P<patient>[A-Z ,]+).*?"
        r"(\d{7,10})\s(?P<pos>\d{4})\s(?P<date>\d{6})\s+1\s(?P<proc>[A-Z0-9]+(?:\s[A-Z0-9]+)?)\s+"
        r"(?P<billed>\d+\.\d{2})\s+(?P<allowed>\d+\.\d{2})\s+(?P<deduct>\d+\.\d{2})\s+"
        r"(?P<coins>\d+\.\d{2})\s+(?P<group>[A-Z0-9\-]+)\s+(?P<grp_amt>\-?\d+\.\d{2})\s+"
        r"(?P<prov_pd>\-?\d+\.\d{2})", re.DOTALL
    )
    
    data = []
    new_files = []
    
    for filename in os.listdir(SOURCE_PDF):
        if not filename.lower().endswith(".pdf") or filename in processed:
            continue
            
        new_files.append(filename)
        filepath = os.path.join(SOURCE_PDF, filename)
        
        with fitz.open(filepath) as doc:
            text = "".join(page.get_text() for page in doc)
            
        payer = detect_payer(text)
        
        for match in pattern.findall(text):
            patient, _, pos, date, proc, billed, allowed, deduct, coins, group, grp_amt, prov_pd = match
            data.append({
                "INSURANCE": payer,
                "File": filename,
                "PATIENT NAME": patient.strip(),
                "SERV DATE": f"{pos} {date}",
                "PROC": proc.strip(),
                "BILLED": float(billed),
                "ALLOWED": float(allowed),
                "DEDUCT": float(deduct),
                "COINS": float(coins),
                "GRP/RC-AMT": group.strip(),
                "RC-AMT VALUE": float(grp_amt),
                "PROV PD": float(prov_pd)
            })
    
    return data, new_files

def create_dataframe(data):
    if not data:
        return None
        
    df = pd.DataFrame(data)
    
    # Expand denial codes
    for code in df["GRP/RC-AMT"].unique():
        df[code] = 0.0
    
    for idx, row in df.iterrows():
        df.at[idx, row["GRP/RC-AMT"]] = row["RC-AMT VALUE"]
    
    df.drop(columns=["GRP/RC-AMT", "RC-AMT VALUE"], inplace=True)
    return df

def save_excel(df):
    if os.path.exists(EXCEL_FILE):
        existing = pd.read_excel(EXCEL_FILE)
        df = pd.concat([existing, df], ignore_index=True)
    
    df.to_excel(EXCEL_FILE, index=False)
    return df

def generate_dashboard_data(df):
    df["Parsed_Date"] = df["SERV DATE"].apply(parse_service_date)
    df = df.dropna(subset=["Parsed_Date"])
    
    total_billed = df["BILLED"].sum()
    total_paid = df["PROV PD"].sum()
    denied_df = df[df["PROV PD"] == 0]
    denial_rate = len(denied_df) / len(df) if len(df) > 0 else 0
    
    # KPI data matching starter kit schema
    kpi_data = {
        "payments_ytd": round(total_paid, 2),
        "denial_rate": round(denial_rate, 3),
        "days_to_pay": 18,
        "write_offs": round(denied_df["BILLED"].sum(), 2),
        "clean_rate": round(1 - denial_rate, 3),
        "incentives_ytd": 22500
    }
    
    # Payer summary
    payer_data = (df.groupby("INSURANCE")["PROV PD"]
                   .sum().reset_index()
                   .rename(columns={"INSURANCE": "name", "PROV PD": "amount"})
                   .to_dict(orient="records"))
    
    # Denial trends
    denial_cols = [col for col in df.columns if re.match(r"[A-Z]{2}-\d{2,3}", col)]
    denial_data = (df[denial_cols].sum().reset_index()
                   .rename(columns={"index": "name", 0: "value"})
                   .query("value > 0")
                   .to_dict(orient="records"))
    
    # CPT data
    cpt_data = (df.groupby("PROC")["PROV PD"]
                .sum().reset_index()
                .rename(columns={"PROC": "name", "PROV PD": "amount"})
                .to_dict(orient="records"))
    
    return kpi_data, payer_data, denial_data, cpt_data

def export_json_files(kpi_data, payer_data, denial_data, cpt_data):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    files = {
        "kpi_snapshot.json": kpi_data,
        "payer_summary.json": payer_data,
        "denial_trends.json": denial_data,
        "claim_risk_scores.json": cpt_data
    }
    
    for filename, data in files.items():
        with open(os.path.join(OUTPUT_DIR, filename), "w") as f:
            json.dump(data, f, indent=2)

def update_log(new_files):
    with open(LOG_FILE, "a") as f:
        for filename in new_files:
            f.write(f"{filename}\n")

def main():
    data, new_files = process_pdfs()
    
    if not data:
        print("No new files to process.")
        return
    
    df = create_dataframe(data)
    df_combined = save_excel(df)
    
    kpi_data, payer_data, denial_data, cpt_data = generate_dashboard_data(df_combined)
    export_json_files(kpi_data, payer_data, denial_data, cpt_data)
    
    update_log(new_files)
    print(f"Processed {len(new_files)} files. Dashboard JSONs exported to output/")

if __name__ == "__main__":
    main()