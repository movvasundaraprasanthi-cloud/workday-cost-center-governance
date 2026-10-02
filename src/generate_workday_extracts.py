"""Synthetic Workday HCM + Financials extracts for a regional health system.

Simulates the monthly EIB-style extracts a Workday Financials analyst would pull:
cost center master, supervisory org hierarchy, worker assignments, payroll
actuals by ledger account, annual budgets, manual journals, and quarterly
cost-center owner attestations. All data is fictional.

Cost center IDs follow a Workday-style pattern (CC-####). Ledger accounts use
a hospital chart of accounts. The generator deliberately seeds realistic
governance failures (orphan cost centers, lapsed attestations, SoD conflicts,
spend on inactive codes) so the governance engine has real findings.
"""
import numpy as np
import pandas as pd

rng = np.random.default_rng(7)

MONTHS = pd.date_range("2024-01-01", periods=24, freq="MS")

# (cost center, supervisory org, division, owner, annual budget $, active?)
COST_CENTERS = [
    # --- Clinical ---
    ("CC-1010", "Emergency Department", "SO-ED", "Acute Care", 38_400_000),
    ("CC-1020", "Surgical Services", "SO-SURG", "Acute Care", 58_800_000),
    ("CC-1030", "Cardiology", "SO-CARD", "Acute Care", 44_400_000),
    ("CC-1040", "Oncology", "SO-ONC", "Acute Care", 40_800_000),
    ("CC-1050", "Radiology & Imaging", "SO-RAD", "Diagnostics", 22_800_000),
    ("CC-1060", "Laboratory", "SO-LAB", "Diagnostics", 14_400_000),
    ("CC-1070", "Pharmacy", "SO-PHARM", "Diagnostics", 20_400_000),
    ("CC-1080", "Med/Surg Nursing", "SO-MS", "Acute Care", 36_000_000),
    ("CC-1090", "ICU", "SO-ICU", "Acute Care", 30_000_000),
    ("CC-1100", "Behavioral Health", "SO-BH", "Acute Care", 12_600_000),
    ("CC-1110", "Rehabilitation Services", "SO-REHAB", "Acute Care", 9_600_000),
    ("CC-1120", "Women's Services", "SO-WOMEN", "Acute Care", 18_000_000),
    # --- Support ---
    ("CC-2010", "Facilities & Maintenance", "SO-FAC", "Operations", 11_400_000),
    ("CC-2020", "Information Technology", "SO-IT", "Operations", 13_200_000),
    ("CC-2030", "Revenue Cycle", "SO-RC", "Finance", 16_200_000),
    ("CC-2040", "Finance & Accounting", "SO-FIN", "Finance", 8_400_000),
    ("CC-2050", "Human Resources", "SO-HR", "Operations", 9_360_000),
    ("CC-2060", "Supply Chain", "SO-SC", "Operations", 10_800_000),
    ("CC-2070", "Patient Access", "SO-PA", "Finance", 7_200_000),
    ("CC-2080", "Care Management", "SO-CM", "Acute Care", 6_000_000),
]

# Deliberate master-data defects (the governance engine must catch these)
DEFECTS = {
    "orphan_cc": [("CC-9010", "Legacy Ortho Clinic", None, "Acute Care", 0)],  # no supervisory org
    "inactive_with_spend": [("CC-3010", "Closed Wound Care", "SO-WC", "Acute Care", 0)],
}

LEDGER = {
    "6100": "Salaries & Wages",
    "6110": "Overtime Premium",
    "6120": "Contract / Agency Labor",
    "6130": "Benefits",
    "6200": "Medical Supplies",
    "6210": "Pharmaceuticals",
    "6300": "Purchased Services",
    "6400": "Repairs & Maintenance",
    "6500": "IT Software & Licenses",
}

FIRST = ["Alicia", "Marcus", "Priya", "David", "Chen", "Maria", "James", "Fatima",
         "Robert", "Lena", "Tom", "Aisha", "Kevin", "Nora", "Omar", "Julia"]
LAST = ["Nguyen", "Patel", "Garcia", "Kim", "Johnson", "Rahman", "Smith", "Lopez",
        "Hassan", "Brown", "Ali", "Davis", "Khan", "Miller", "Singh", "Adams"]


def build():
    cc_rows, so_rows, worker_rows, pay_rows = [], [], [], []
    budgets, journals, attest = [], [], []

    all_cc = COST_CENTERS + DEFECTS["orphan_cc"] + DEFECTS["inactive_with_spend"]
    so_ids = sorted({so for _, _, so, _, _ in COST_CENTERS if so})
    for so in so_ids:
        so_rows.append({"supervisory_org_id": so, "status": "Active",
                        "manager": f"{rng.choice(FIRST)} {rng.choice(LAST)}"})

    wid = 1000
    for cc, name, so, div, annual in all_cc:
        active = cc not in ("CC-3010",)
        cc_rows.append({"cost_center_id": cc, "cost_center_name": name,
                        "supervisory_org_id": so or "", "division": div,
                        "owner": f"{rng.choice(FIRST)} {rng.choice(LAST)}",
                        "status": "Active" if active else "Inactive",
                        "annual_budget": annual})
        if annual:
            budgets.append({"cost_center_id": cc, "fiscal_year": "FY2025",
                            "budget_amount": annual})
        # workers
        n = max(8, int(annual / 380_000)) if annual else rng.integers(3, 8)
        for _ in range(n):
            wid += 1
            # a few workers land on no cost center (defect for CC-06)
            cc_assign = cc if rng.random() > 0.012 else ""
            worker_rows.append({"worker_id": f"W-{wid}",
                                "name": f"{rng.choice(FIRST)} {rng.choice(LAST)}",
                                "cost_center_id": cc_assign,
                                "supervisory_org_id": so or "",
                                "job_profile": rng.choice(["RN", "Tech", "Analyst",
                                                           "Specialist", "Manager", "Clerk"]),
                                "status": "Active"})
        # monthly payroll actuals by ledger account
        for i, m in enumerate(MONTHS):
            season = 1 + 0.07 * np.sin(2 * np.pi * i / 12)
            monthly = annual / 12 * season if annual else 0
            # inactive cost center still getting spend (defect for CC-05)
            if cc == "CC-3010":
                monthly = 42_000 * rng.normal(1, 0.1)
            if not monthly:
                continue
            mix = {"6100": 0.58, "6110": 0.06, "6120": 0.05, "6130": 0.16,
                   "6200": 0.06, "6210": 0.03, "6300": 0.03, "6400": 0.015, "6500": 0.015}
            # agency creep in nursing areas late in the series
            if cc in ("CC-1080", "CC-1090") and i >= 15:
                mix = dict(mix); mix["6120"] = 0.11; mix["6100"] = 0.52
                monthly *= 1.045  # premium labor inflates total spend
            for acct, share in mix.items():
                pay_rows.append({"month": m.strftime("%Y-%m-%d"),
                                 "cost_center_id": cc, "ledger_account": acct,
                                 "account_name": LEDGER[acct],
                                 "actual_amount": round(monthly * share * rng.normal(1, 0.04), 2)})

    # manual journals (a few break SoD / approval rules)
    jid = 5000
    approvers = [f"{rng.choice(FIRST)} {rng.choice(LAST)}" for _ in range(6)]
    for i in range(320):
        jid += 1
        cc = rng.choice([c for c, *_ in COST_CENTERS])
        amt = round(float(rng.lognormal(9.2, 1.1)), 2)
        requester = rng.choice(approvers)
        # 8% SoD violations: requester == approver
        approver = requester if rng.random() < 0.08 else rng.choice([a for a in approvers if a != requester])
        # large journals sometimes missing director approval
        needs_dir = amt > 25_000
        has_dir = not (needs_dir and rng.random() < 0.15)
        journals.append({"journal_id": f"JE-{jid}", "month": pd.Timestamp(rng.choice(MONTHS)).strftime("%Y-%m-%d"),
                         "cost_center_id": cc, "amount": amt, "requester": requester,
                         "approver": approver, "director_approval": has_dir,
                         "auto_posted": bool(rng.random() < 0.72)})

    # quarterly attestations (some lapsed)
    for cc, name, so, div, annual in COST_CENTERS:
        for q in ["2024-Q1", "2024-Q2", "2024-Q3", "2024-Q4", "2025-Q1", "2025-Q2"]:
            lapsed = rng.random() < (0.22 if div == "Operations" else 0.08)
            attest.append({"cost_center_id": cc, "quarter": q,
                           "attested": not lapsed,
                           "attested_date": f"{q[:4]}-{ {'Q1':'03','Q2':'06','Q3':'09','Q4':'12'}[q[5:]] }-20"
                           if not lapsed else ""})

    out = {"cost_centers": pd.DataFrame(cc_rows), "supervisory_orgs": pd.DataFrame(so_rows),
           "workers": pd.DataFrame(worker_rows), "payroll_actuals": pd.DataFrame(pay_rows),
           "budgets": pd.DataFrame(budgets), "journals": pd.DataFrame(journals),
           "attestations": pd.DataFrame(attest)}
    for name, frame in out.items():
        frame.to_csv(f"data/{name}.csv", index=False)
        print(f"data/{name}.csv", frame.shape)
    return out


if __name__ == "__main__":
    build()
