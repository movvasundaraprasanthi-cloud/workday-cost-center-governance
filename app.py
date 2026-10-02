"""Workday Cost Center Governance — Command Center dashboard.

The daily-driver view for the analyst who owns cost-center governance:
exception queue with severity triage, control effectiveness, budget variance,
and labor analytics. Reads the outputs of governance_engine.py + analytics.py.
"""
import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Cost Center Governance — Command Center", layout="wide")

@st.cache_data
def load():
    with open("data/analytics_summary.json") as f:
        s = json.load(f)
    return (s, pd.read_csv("data/exceptions.csv"), pd.read_csv("data/cc_variance.csv"),
            pd.read_csv("data/cost_centers.csv"), pd.read_csv("data/payroll_actuals.csv"))

s, exc, var, cc, pay = load()
pay["actual_amount"] = pay["actual_amount"].astype(float)
pay["month"] = pd.to_datetime(pay["month"])

st.title("Workday Cost Center Governance — Command Center")
st.caption("Health system · 22 cost centers · synthetic Workday HCM/Financials extracts")

# ------------------------------------------------------------- KPI band --
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Open exceptions", s["exception_count"], f"{s['critical_exceptions']} critical",
          delta_color="inverse")
k2.metric("Attestation compliance", f"{s['attestation_compliance']:.0%}", "Q2 FY25")
k3.metric("Journal auto-post rate", f"{s['auto_post_rate']:.1%}")
k4.metric("Net budget variance (TTM)", f"${s['net_variance']/1e6:+.1f}M")
k5.metric("Agency labor", f"{s['agency_pct_of_labor']:.1%}", "of labor spend",
          delta_color="inverse")

tab1, tab2, tab3, tab4 = st.tabs(["Exception Queue", "Control Effectiveness",
                                  "Budget Variance", "Labor Analytics"])

# ------------------------------------------------------- exception queue --
with tab1:
    st.subheader("Prioritized exception queue")
    sev = st.multiselect("Severity", ["Critical", "High", "Medium", "Low"],
                         default=["Critical", "High", "Medium", "Low"])
    q = exc[exc["severity"].isin(sev)].copy()
    sev_color = {"Critical": "#d62728", "High": "#ff7f0e", "Medium": "#1f77b4", "Low": "#7f7f7f"}
    fig = px.bar(q.groupby(["control", "severity"]).size().reset_index(name="n"),
                 x="control", y="n", color="severity",
                 color_discrete_map=sev_color, title="Exceptions by control")
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(q[["control", "severity", "cost_center_id", "detail", "owner"]],
                 use_container_width=True, height=420)
    st.caption("Triage rule: Critical = financial-statement or master-data risk — "
               "clear within 5 business days. High within 15.")

# -------------------------------------------------------------- controls --
with tab2:
    st.subheader("Control framework effectiveness")
    cs = pd.DataFrame(s["control_summary"])
    fig2 = px.bar(cs, x="control", y="count", color="severity",
                  color_discrete_map=sev_color,
                  title="Findings per control (higher = weaker control)")
    st.plotly_chart(fig2, use_container_width=True)
    c1, c2 = st.columns(2)
    j = pd.read_csv("data/journals.csv", dtype=str)
    c1.metric("SoD violations (CC-03)", int((exc["control"] == "CC-03").sum()),
              "journals where requester = approver", delta_color="inverse")
    c2.metric("Large journals missing director approval (CC-04)",
              int((exc["control"] == "CC-04").sum()), delta_color="inverse")
    st.markdown("**Control catalog** — CC-01 orphan cost centers · CC-02 owner attestations · "
                "CC-03 segregation of duties · CC-04 large-journal approvals · CC-05 spend on "
                "inactive codes · CC-06 unassigned workers · CC-07 budget coverage")

# -------------------------------------------------------------- variance --
with tab3:
    st.subheader("Budget vs. actual — trailing 12 months")
    v = var.copy()
    v["variance_m"] = v["variance"] / 1e6
    colors = ["#d62728" if x > 0 else "#2ca02c" for x in v["variance"]]
    fig3 = go.Figure(go.Bar(x=v["cost_center_name"], y=v["variance_m"],
                            marker_color=colors,
                            text=v["variance_m"].apply(lambda x: f"${x:+.2f}M"),
                            textposition="outside"))
    fig3.update_layout(title="Variance by cost center (+ = over budget)",
                       yaxis_title="$M", height=460)
    fig3.update_xaxes(tickangle=45)
    st.plotly_chart(fig3, use_container_width=True)
    st.dataframe(v[["cost_center_id", "cost_center_name", "division", "actual_amount",
                    "budget_amount", "variance", "variance_pct", "run_rate_status"]]
                 .sort_values("variance", ascending=False)
                 .style.format({"actual_amount": "${:,.0f}", "budget_amount": "${:,.0f}",
                                "variance": "${:,.0f}", "variance_pct": "{:.2%}"}),
                 use_container_width=True)

# ----------------------------------------------------------------- labor --
with tab4:
    st.subheader("Labor analytics")
    lab = pay[pay["ledger_account"].isin(["6100", "6110", "6120", "6130"])].copy()
    lab["acct"] = lab["ledger_account"].map({"6100": "Base", "6110": "Overtime",
                                             "6120": "Agency", "6130": "Benefits"})
    tr = lab.groupby(["month", "acct"])["actual_amount"].sum().reset_index()
    fig4 = px.area(tr, x="month", y="actual_amount", color="acct",
                   title="Labor mix over time — watch agency creep",
                   labels={"actual_amount": "USD"})
    st.plotly_chart(fig4, use_container_width=True)
    c1, c2 = st.columns(2)
    ot = pd.DataFrame(s["top_overtime"])
    c1.bar_chart(ot.set_index("cost_center_id")["ot_pct_of_base"],
                 use_container_width=True)
    c1.caption("Overtime as % of base pay — top cost centers")
    ag = pd.DataFrame(s["top_agency"])
    c2.bar_chart(ag.set_index("cost_center_id")["agency_pct_of_base"],
                 use_container_width=True)
    c2.caption("Agency as % of base pay — top cost centers")
    st.info("Read: Med/Surg Nursing and ICU show agency labor above 10% of base pay with "
            "unfavorable budget variance — the classic premium-labor spiral. Recommended actions: "
            "float-pool expansion, retention review, and a 90-day agency reduction target.")

st.sidebar.markdown("---")
st.sidebar.caption("Synthetic data · governance engine: src/governance_engine.py")
