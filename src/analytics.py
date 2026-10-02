"""Analytics layer — labor spend, variance, overtime & agency deep-dives.

Produces the KPI pack a Senior Financial Analyst would present to Finance
leadership: budget-vs-actual by cost center, margin waterfall inputs, overtime
and agency labor analytics, journal control effectiveness, and attestation
compliance. Writes data/analytics_summary.json for the dashboard and PDF.
"""
import json
import pandas as pd

ACCT = {"6100": "Salaries & Wages", "6110": "Overtime Premium",
        "6120": "Contract / Agency Labor", "6130": "Benefits"}


def analyze():
    cc = pd.read_csv("data/cost_centers.csv", dtype=str)
    pay = pd.read_csv("data/payroll_actuals.csv", dtype={"ledger_account": str})
    pay["actual_amount"] = pay["actual_amount"].astype(float)
    pay["month"] = pd.to_datetime(pay["month"])
    budgets = pd.read_csv("data/budgets.csv")
    budgets["budget_amount"] = budgets["budget_amount"].astype(float)
    journals = pd.read_csv("data/journals.csv", dtype=str)
    journals["amount"] = journals["amount"].astype(float)
    att = pd.read_csv("data/attestations.csv", dtype=str)
    ex = pd.read_csv("data/exceptions.csv")

    # YTD actuals vs annual budget by cost center (trailing 12 months vs FY budget)
    cutoff = pay["month"].max() - pd.DateOffset(months=11)
    pay_ttm = pay[pay["month"] >= cutoff]
    ytd = pay_ttm.groupby("cost_center_id")["actual_amount"].sum().reset_index()
    m = ytd.merge(budgets, on="cost_center_id", how="left").merge(
        cc[["cost_center_id", "cost_center_name", "division", "owner"]], on="cost_center_id")
    m["budget_amount"] = m["budget_amount"].fillna(0)
    m["variance"] = m["actual_amount"] - m["budget_amount"]
    m["variance_pct"] = (m["variance"] / m["budget_amount"].replace(0, pd.NA)).fillna(0).round(4)
    m["run_rate_status"] = pd.cut(m["variance_pct"],
                                  [-9, -0.03, 0.03, 9],
                                  labels=["Under budget", "On track", "Over budget"])

    # labor mix: overtime & agency as % of total labor
    labor = pay[pay["ledger_account"].isin(["6100", "6110", "6120", "6130"])]
    mix = labor.groupby("ledger_account")["actual_amount"].sum()
    labor_total = mix.sum()
    ot = pay[pay["ledger_account"] == "6110"].groupby("cost_center_id")["actual_amount"].sum()
    agency = pay[pay["ledger_account"] == "6120"].groupby("cost_center_id")["actual_amount"].sum()
    base = pay[pay["ledger_account"] == "6100"].groupby("cost_center_id")["actual_amount"].sum()
    ot_pct = (ot / base).fillna(0).sort_values(ascending=False).head(8)
    agency_pct = (agency / base).fillna(0).sort_values(ascending=False).head(8)

    # monthly trend
    trend = pay.groupby("month")["actual_amount"].sum().reset_index()
    trend["month"] = trend["month"].dt.strftime("%Y-%m")

    # journal effectiveness
    j_total = len(journals)
    auto_rate = (journals["auto_posted"] == "True").mean()
    late_large = ((journals["amount"] > 25_000) & (journals["director_approval"] != "True")).sum()

    # attestation compliance (latest quarter)
    latest_q = "2025-Q2"
    att_q = att[att["quarter"] == latest_q]
    att_rate = (att_q["attested"] == "True").mean()

    summary = {
        "total_ytd_spend": round(ytd["actual_amount"].sum(), 0),
        "total_budget": round(budgets["budget_amount"].sum(), 0),
        "net_variance": round(m["variance"].sum(), 0),
        "over_budget_cc": int((m["run_rate_status"] == "Over budget").sum()),
        "cost_centers": int(cc[cc["status"] == "Active"].shape[0]),
        "overtime_pct_of_labor": round(mix.get("6110", 0) / labor_total, 4),
        "agency_pct_of_labor": round(mix.get("6120", 0) / labor_total, 4),
        "auto_post_rate": round(auto_rate, 4),
        "attestation_compliance": round(att_rate, 4),
        "exception_count": int(len(ex)),
        "critical_exceptions": int((ex["severity"] == "Critical").sum()),
        "top_overruns": m.sort_values("variance", ascending=False)
            .head(6)[["cost_center_id", "cost_center_name", "actual_amount",
                      "budget_amount", "variance", "variance_pct"]]
            .to_dict("records"),
        "top_overtime": [{"cost_center_id": k, "ot_pct_of_base": round(v, 4)}
                         for k, v in ot_pct.items()],
        "top_agency": [{"cost_center_id": k, "agency_pct_of_base": round(v, 4)}
                       for k, v in agency_pct.items()],
        "monthly_trend": trend.to_dict("records"),
        "control_summary": pd.read_csv("data/control_summary.csv").to_dict("records"),
    }
    with open("data/analytics_summary.json", "w") as f:
        json.dump(summary, f, indent=2)
    m.to_csv("data/cc_variance.csv", index=False)
    print("analytics_summary.json written;",
          f"YTD ${summary['total_ytd_spend']/1e6:.0f}M, net variance ${summary['net_variance']/1e6:+.1f}M")
    return summary


if __name__ == "__main__":
    analyze()
