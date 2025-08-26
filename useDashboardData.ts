export type KpiSnapshot = {
  payments_ytd: number; denial_rate: number; days_to_pay: number;
  write_offs: number; clean_rate: number; incentives_ytd: number;
};

async function load(path: string) {
  const r = await fetch(path);
  if (!r.ok) throw new Error(`Missing: ${path}`);
  return r.json();
}
export const loadKpis = () => load('/src/data/kpi_snapshot.json');
export const loadPayerSummary = () => load('/src/data/payer_summary.json');
export const loadDenialTrends = () => load('/src/data/denial_trends.json');
export const loadClaimRisk = () => load('/src/data/claim_risk_scores.json');
export const loadIncentives = () => load('/src/data/incentive_snapshot.json');