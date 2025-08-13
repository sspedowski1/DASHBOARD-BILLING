import os

pdf_folder = r"C:\Users\ma\Documents\DASHBOARD-BILLING\ERA COPIES 2025"
log_file = r"C:\Users\ma\Documents\DASHBOARD-BILLING\processed_files.txt"


# All actual PDF files
pdf_files = set(f for f in os.listdir(pdf_folder) if f.lower().endswith(".pdf"))

# Logged processed files
with open(log_file, "r") as f:
    logged_files = set(f.read().splitlines())

# Difference
unprocessed = pdf_files - logged_files
print(f"🚨 Missing {len(unprocessed)} file(s):")
for f in sorted(unprocessed):
    print(f)
