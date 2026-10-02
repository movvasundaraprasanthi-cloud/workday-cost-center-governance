# Workday Cost Center Governance & Analytics

A controllership-grade control framework over Workday HCM & Financials extracts —
**validate first, analyze second**. Built for a regional health system: 22 cost centers,
$429M annual spend, 7 SOX-style controls, a severity-ranked exception queue, budget
variance analytics, and labor (overtime/agency) deep-dives.

## The headline findings

| Finding | Control | Severity |
|---|---|---|
| $518K posted to a closed cost center (CC-3010) | CC-05 | Critical |
| 25 journals where requester = approver | CC-03 | Critical |
| 2 orphan cost centers with no supervisory-org mapping | CC-01 | Critical |
| 9 journals > $25K without director approval | CC-04 | High |
| Agency-labor spiral in Med/Surg Nursing & ICU driving unfavorable variance | Analytics | — |

## Pipeline

```
generate → govern → analyze → visualize
```

| Step | Script | Output |
|---|---|---|
| 1. Simulate Workday extracts | `src/generate_workday_extracts.py` | `data/*.csv` — cost centers, supervisory orgs, workers, payroll actuals, budgets, journals, attestations |
| 2. Run control engine | `src/governance_engine.py` | `data/exceptions.csv`, `data/control_summary.csv` |
| 3. Analytics pack | `src/analytics.py` | `data/analytics_summary.json`, `data/cc_variance.csv` |
| 4. Dashboard | `app.py` | Streamlit command center |
| 5. Portfolio PDF | `src/build_pdf.py` | `docs/Workday_Cost_Center_Governance_Portfolio.pdf` |

```bash
python -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python src/generate_workday_extracts.py
.venv/bin/python src/governance_engine.py
.venv/bin/python src/analytics.py
.venv/bin/python src/build_pdf.py
.venv/bin/streamlit run app.py
```

## Control framework

| Control | Severity | What it checks | Workday concept |
|---|---|---|---|
| CC-01 | Critical | No orphan cost centers | Supervisory org mapping |
| CC-02 | High | Owner attestation current (quarterly) | Attestation business process |
| CC-03 | Critical | Segregation of duties on journals | BP approval routing |
| CC-04 | High | Journals > $25K need director approval | Approval thresholds |
| CC-05 | Critical | No spend on inactive cost centers | EIB load validation |
| CC-06 | Medium | Every active worker has a cost center | Worker assignment |
| CC-07 | Medium | Every active cost center has a budget | Budget load coverage |

Triage SLA: Critical → 5 business days; High → 15 days.

## Data

All data is **synthetic**, modeled on real Workday concepts (supervisory orgs, worktags,
ledger accounts, EIB loads, journal business processes). See `data/dictionary.md`.

## Why this exists

Cost centers are the foundation every healthcare finance number stands on. When the
master is wrong, budgets misallocate, labor spend hides, and close slows. This project
shows how I'd run governance as a Senior Financial Analyst: automated controls,
a prioritized exception queue owners can actually work, and analytics that turn
findings into the labor story Finance leadership needs.

---
Built by **Sundara Prasanthi Movva** — Senior Financial Analyst, Healthcare FP&A
(Humana · Optum/UnitedHealth Group · Cigna), MBA Business Analytics.
