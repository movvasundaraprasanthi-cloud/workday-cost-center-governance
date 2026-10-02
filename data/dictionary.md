# Data dictionary — synthetic Workday extracts

All files live in `data/`. Amounts in USD. All data is fictional.

## cost_centers.csv
| Column | Meaning |
|---|---|
| cost_center_id | Workday-style ID, e.g. CC-1010 |
| cost_center_name | Display name |
| supervisory_org_id | Owning supervisory org (blank = orphan — a seeded defect) |
| division | Acute Care / Diagnostics / Finance / Operations |
| owner | Cost-center owner (attestation responsible party) |
| status | Active / Inactive |
| annual_budget | FY annual budget (0 for non-budgeted codes) |

## supervisory_orgs.csv
Supervisory org master: ID, status, manager.

## workers.csv
| Column | Meaning |
|---|---|
| worker_id | W-#### |
| cost_center_id | Assigned cost center (blank = unassigned — a seeded defect) |
| job_profile | RN / Tech / Analyst / Specialist / Manager / Clerk |

## payroll_actuals.csv
Monthly actuals by cost center × ledger account (the "EIB payroll load").

Ledger accounts: `6100` Salaries & Wages · `6110` Overtime Premium ·
`6120` Contract/Agency Labor · `6130` Benefits · `6200` Medical Supplies ·
`6210` Pharmaceuticals · `6300` Purchased Services · `6400` Repairs &
Maintenance · `6500` IT Software & Licenses.

## budgets.csv
FY budget by cost center.

## journals.csv
Manual journals: ID, month, cost center, amount, requester, approver,
director_approval flag, auto_posted flag. Seeded defects: SoD violations
(requester = approver) and large journals missing director approval.

## attestations.csv
Quarterly cost-center owner attestations. Seeded lapses, concentrated in Operations.

## Derived outputs
- `exceptions.csv` — control engine findings (control, severity, cost center, detail, owner)
- `control_summary.csv` — findings per control × severity
- `cc_variance.csv` — trailing-12-month actuals vs budget by cost center
- `analytics_summary.json` — KPI pack for the dashboard and PDF
