"""Governance control engine — Workday cost center controls.

Implements a SOX-style control framework over the Workday extracts. Each control
returns exception records with severity, owner, and aging. Severity scoring
mirrors how a controllership team would prioritize: financial-statement risk
and master-data integrity first.

Controls:
  CC-01  No orphan cost centers (must map to an active supervisory org)
  CC-02  Owner attestation current (quarterly, no lapses in last 2 quarters)
  CC-03  Segregation of duties (journal requester != approver)
  CC-04  Large-journal approval (>$25K journals need director approval)
  CC-05  No spend on inactive cost centers
  CC-06  Every active worker assigned to a cost center
  CC-07  Budget coverage (active cost center must have an FY budget)
"""
import pandas as pd

SEV_ORDER = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}


def _load():
    return {n: pd.read_csv(f"data/{n}.csv", dtype=str) for n in
            ["cost_centers", "supervisory_orgs", "workers", "payroll_actuals",
             "budgets", "journals", "attestations"]}


def run_controls():
    d = _load()
    cc = d["cost_centers"]
    exc = []

    def add(control, severity, cc_id, detail, owner=""):
        exc.append({"control": control, "severity": severity,
                    "cost_center_id": cc_id, "detail": detail, "owner": owner})

    active_cc = cc[cc["status"] == "Active"]
    active_ids = set(active_cc["cost_center_id"])
    active_so = set(d["supervisory_orgs"]["supervisory_org_id"])

    # CC-01 orphan cost centers
    for _, r in cc.iterrows():
        if not r["supervisory_org_id"] or r["supervisory_org_id"] not in active_so:
            add("CC-01", "Critical", r["cost_center_id"],
                f"No active supervisory org mapping (found: '{r['supervisory_org_id'] or 'blank'}')",
                r["owner"])

    # CC-02 lapsed attestations (last 2 quarters)
    recent_q = ["2025-Q1", "2025-Q2"]
    att = d["attestations"]
    for cid in active_ids:
        sub = att[(att["cost_center_id"] == cid) & (att["quarter"].isin(recent_q))]
        missing = [q for q in recent_q if not ((sub["quarter"] == q) & (sub["attested"] == "True")).any()]
        if missing:
            owner = cc.loc[cc["cost_center_id"] == cid, "owner"].iloc[0]
            add("CC-02", "High", cid,
                f"Owner attestation missing for {', '.join(missing)}", owner)

    # CC-03 / CC-04 journal controls
    for _, j in d["journals"].iterrows():
        if j["requester"] == j["approver"]:
            add("CC-03", "Critical", j["cost_center_id"],
                f"SoD violation on {j['journal_id']}: requester == approver ({j['requester']})")
        if float(j["amount"]) > 25_000 and j["director_approval"] != "True":
            add("CC-04", "High", j["cost_center_id"],
                f"{j['journal_id']} of ${float(j['amount']):,.0f} posted without director approval")

    # CC-05 spend on inactive cost centers
    pay = d["payroll_actuals"].copy()
    pay["actual_amount"] = pay["actual_amount"].astype(float)
    spend = pay.groupby("cost_center_id")["actual_amount"].sum()
    inactive = set(cc.loc[cc["status"] == "Inactive", "cost_center_id"])
    for cid in inactive:
        if cid in spend.index and spend[cid] > 0:
            add("CC-05", "Critical", cid,
                f"${spend[cid]:,.0f} YTD spend posted to inactive cost center")

    # CC-06 workers without cost center
    w = d["workers"]
    orphan_w = w[(w["status"] == "Active") & ((w["cost_center_id"] == "") | w["cost_center_id"].isna())]
    for _, r in orphan_w.iterrows():
        add("CC-06", "Medium", "(unassigned)",
            f"Active worker {r['worker_id']} ({r['name']}) has no cost center assignment")

    # CC-07 active cost centers missing FY budget
    budgeted = set(d["budgets"]["cost_center_id"])
    for cid in active_ids - budgeted:
        owner = cc.loc[cc["cost_center_id"] == cid, "owner"].iloc[0]
        add("CC-07", "Medium", cid, "Active cost center has no FY budget loaded", owner)

    ex = pd.DataFrame(exc)
    ex["severity_rank"] = ex["severity"].map(SEV_ORDER)
    ex = ex.sort_values(["severity_rank", "control", "cost_center_id"]).drop(columns="severity_rank")
    ex.to_csv("data/exceptions.csv", index=False)

    summary = (ex.groupby(["control", "severity"]).size().reset_index(name="count")
                 .sort_values(["control", "severity"]))
    summary.to_csv("data/control_summary.csv", index=False)
    print(f"{len(ex)} exceptions across {ex['control'].nunique()} controls")
    print(summary.to_string(index=False))
    return ex


if __name__ == "__main__":
    run_controls()
