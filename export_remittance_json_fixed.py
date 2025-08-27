import os
import fitz  # PyMuPDF
import pandas as pd
import re
import json
from datetime import datetime

# ---- PATH SETUP ----
folder_path = r"C:\Users\ma\Documents\DASHBOARD-BILLING"
source_pdf_folder = os.path.join(folder_path, "ERA COPIES 2025")
react_data_folder = os.path.join(folder_path, "output")
output_file = os.path.join(folder_path, "remittance_summary.xlsx")
processed_log = os.path.join(folder_path, "processed_files.txt")

# ---- LOAD PROCESSED FILES LOG ----
if os.path.exists(processed_log):
    with open(processed_log, "r") as log_file:
        processed_files = set(log_file.read().splitlines())
else:
    processed_files = set()

all_data = []

# ---- PDF PARSING PATTERN ----
pattern = re.compile(
    r"NAME\s+(?P<patient>[A-Z ,]+).*?"
    r"(\d{7,10})\s(?P<pos>\d{4})\s(?P<date>\d{6})\s+1\s(?P<proc>[A-Z0-9]+(?:\s[A-Z0-9]+)?)\s+"
    r"(?P<billed>\d+\.\d{2})\s+(?P<allowed>\d+\.\d{2})\s+(?P<deduct>\d+\.\d{2})\s+"
    r"(?P<coins>\d+\.\d{2})\s+(?P<group>[A-Z0-9\-]+)\s+(?P<grp_amt>\-?\d+\.\d{2})\s+"
    r"(?P<prov_pd>\-?\d+\.\d{2})", re.DOTALL
)

# ---- PROCESS PDF FILES ----
new_files = []
for filename in os.listdir(source_pdf_folder):
    if filename.lower().endswith(".pdf") and filename not in processed_files:
        new_files.append(filename)
        filepath = os.path.join(source_pdf_folder, filename)
        doc = fitz.open(filepath)
        full_text = "".join([page.get_text() for page in doc])

        # Detect insurance payer
        payer = "Unknown"
        for line in full_text.splitlines()[:20]:
            line = line.upper()
            if "HUMANA" in line:
                payer = "Humana"
            elif "BLUE CARE NETWORK" in line:
                payer = "BCN"
            elif "BCBSM" in line or "BLUE CROSS" in line:
                payer = "BCBS"
            elif "UHC" in line or "UNITED" in line:
                payer = "UHC"
            elif "TRICARE" in line:
                payer = "Tricare"
            elif "PRIORITY HEALTH" in line:
                payer = "Priority Health"

        matches = pattern.findall(full_text)
        for match in matches:
            patient, _, pos, date, proc, billed, allowed, deduct, coins, group, grp_amt, prov_pd = match
            all_data.append({
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

# ---- EXIT IF NO NEW FILES ----
if not all_data:
    print("No new files to process.")
    exit()

# ---- CREATE DATAFRAME ----
df = pd.DataFrame(all_data)

# ---- EXPAND COLUMNS ----
for code in df["GRP/RC-AMT"].unique():
    df[code] = 0.00
for i, row in df.iterrows():
    df.at[i, row["GRP/RC-AMT"]] = row["RC-AMT VALUE"]
df.drop(columns=["GRP/RC-AMT", "RC-AMT VALUE"], inplace=True)

# ---- APPEND TO EXCEL ----
if os.path.exists(output_file):
    df_existing = pd.read_excel(output_file)
    df_combined = pd.concat([df_existing, df], ignore_index=True)
else:
    df_combined = df
df_combined.to_excel(output_file, index=False)

# ---- AGGREGATE FOR JSON DASHBOARD ----
def parse_service_date(serv_date_str):
    try:
        parts = serv_date_str.split()
        if len(parts) == 2:
            return datetime.strptime(parts[1], "%m%d%y")
    except (ValueError, AttributeError):
        return pd.NaT

df_combined["Parsed_Date"] = df_combined["SERV DATE"].apply(parse_service_date)
df_combined.dropna(subset=["Parsed_Date"], inplace=True)

total_billed = df_combined["BILLED"].sum()
total_paid = df_combined["PROV PD"].sum()
collection_rate = (total_paid / total_billed * 100) if total_billed else 0
denied_df = df_combined[df_combined["PROV PD"] == 0]
denial_rate = (len(denied_df) / len(df_combined) * 100) if len(df_combined) else 0
average_payment = df_combined["PROV PD"].mean()
total_denied = denied_df["BILLED"].sum()

kpi_data = {
    "payments_ytd": round(total_paid, 2),
    "denial_rate": round(denial_rate / 100, 3),
    "days_to_pay": 18,
    "write_offs": round(total_denied, 2),
    "clean_rate": round((100 - denial_rate) / 100, 3),
    "incentives_ytd": 22500
}

payer_data = (
    df_combined.groupby("INSURANCE")["PROV PD"]
    .sum().reset_index().rename(columns={"INSURANCE": "name", "PROV PD": "amount"})
    .to_dict(orient="records")
)

denial_cols = [col for col in df_combined.columns if re.match(r"[A-Z]{2}-\d{2,3}", col)]
denial_sums = df_combined[denial_cols].sum().reset_index()
denial_sums.columns = ["name", "value"]
denial_reason_data = denial_sums[denial_sums["value"] > 0].to_dict(orient="records")

cpt_data = (
    df_combined.groupby("PROC")["PROV PD"]
    .sum().reset_index().rename(columns={"PROC": "name", "PROV PD": "amount"})
    .to_dict(orient="records")
)

# ---- EXPORT JSONS ----
os.makedirs(react_data_folder, exist_ok=True)
with open(os.path.join(react_data_folder, "kpi_snapshot.json"), "w") as f:
    json.dump(kpi_data, f, indent=2)
with open(os.path.join(react_data_folder, "payer_summary.json"), "w") as f:
    json.dump(payer_data, f, indent=2)
with open(os.path.join(react_data_folder, "denial_trends.json"), "w") as f:
    json.dump(denial_reason_data, f, indent=2)
with open(os.path.join(react_data_folder, "claim_risk_scores.json"), "w") as f:
    json.dump(cpt_data, f, indent=2)

from datetime import datetime, timezone

worklist_rows = []
denial_cols = [col for col in df_combined.columns if re.match(r"[A-Z]{2}-\d{2,3}", col)]
today = datetime.now(timezone.utc).date()

for _, row in df_combined.iterrows():
    if float(row.get("PROV PD", 0) or 0) == 0:
        reason = next((c for c in denial_cols if float(row.get(c, 0) or 0) != 0), None)
        serv_date = row.get("Parsed_Date")
        days = (today - serv_date.date()).days if pd.notna(serv_date) else 0
        worklist_rows.append({
            "id": f"{row.get('INSURANCE','UNK')}-{str(row.get('File','')).split('.')[0]}",
            "reason": reason or "Unspecified denial",
            "claim": row.get("File", ""),
            "amount": float(row.get("BILLED", 0) or 0),
            "days": int(days),
        })

with open(os.path.join(react_data_folder, "worklist.json"), "w") as f:
    json.dump(worklist_rows, f, indent=2)

# ---- FINALIZE ----
with open(processed_log, "a") as log_file:
    for f in new_files:
        log_file.write(f + "\n")

print("Dashboard JSONs exported to output folder!")
print(f"Done! Added {len(new_files)} new files.")