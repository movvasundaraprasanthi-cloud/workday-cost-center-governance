"""Builds the portfolio PDF: Workday Cost Center Governance & Analytics.

A practitioner-grade write-up: executive summary, control framework, findings
with charts, and an operating model. Run: .venv/bin/python src/build_pdf.py
"""
import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (Image, PageBreak, Paragraph, SimpleDocTemplate,
                                Spacer, Table, TableStyle)

NAVY = colors.HexColor("#1b2a4a")
TEAL = colors.HexColor("#0e7c7b")
GRAY = colors.HexColor("#5a5a5a")
LIGHT = colors.HexColor("#eef2f7")
RED = colors.HexColor("#c0392b")
GREEN = colors.HexColor("#1e8449")

plt.rcParams.update({"font.size": 9, "axes.titlesize": 11, "figure.dpi": 150})


def chart_exceptions(exc):
    piv = exc.groupby(["control", "severity"]).size().unstack(fill_value=0)
    order = [c for c in ["Critical", "High", "Medium", "Low"] if c in piv.columns]
    piv = piv[order]
    ax = piv.plot(kind="bar", stacked=True,
                  color=["#c0392b", "#e67e22", "#2980b9", "#95a5a6"],
                  figsize=(7.2, 3.4), edgecolor="white")
    ax.set_title("Governance findings by control and severity", fontweight="bold")
    ax.set_xlabel(""); ax.set_ylabel("Exception count"); ax.legend(title="Severity")
    plt.xticks(rotation=0); plt.tight_layout(); plt.savefig("/tmp/c_exc.png"); plt.close()


def chart_variance(var):
    v = var.sort_values("variance").copy()
    v["short"] = v["cost_center_name"].str.replace(" Services", "").str.replace(
        " & Imaging", "").str.replace("Department", "Dept.")
    cols = ["#c0392b" if x > 0 else "#1e8449" for x in v["variance"]]
    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    ax.barh(v["short"], v["variance"] / 1e6, color=cols, edgecolor="white")
    ax.set_title("Budget variance by cost center — trailing 12 months ($M)",
                 fontweight="bold")
    ax.set_xlabel("$M  (+ over budget / − under budget)")
    for i, val in enumerate(v["variance"] / 1e6):
        if abs(val) >= 0.2:
            ax.text(val + (0.04 if val >= 0 else -0.04), i, f"{val:+.2f}",
                    va="center", ha="left" if val >= 0 else "right", fontsize=8)
    plt.tight_layout(); plt.savefig("/tmp/c_var.png"); plt.close()


def chart_labor(pay):
    lab = pay[pay["ledger_account"].isin(["6100", "6110", "6120", "6130"])].copy()
    lab["acct"] = lab["ledger_account"].map({"6100": "Base pay", "6110": "Overtime",
                                             "6120": "Agency", "6130": "Benefits"})
    piv = lab.groupby(["month", "acct"])["actual_amount"].sum().unstack()
    color_map = {"Base pay": "#2980b9", "Overtime": "#e67e22",
                 "Agency": "#c0392b", "Benefits": "#7f8c8d"}
    piv = piv[["Base pay", "Overtime", "Agency", "Benefits"]]
    ax = piv.plot(kind="area", stacked=True, figsize=(7.2, 3.4),
                  color=[color_map[c] for c in piv.columns])
    ax.legend(title="")
    ax.set_title("Labor mix over time — agency creep in nursing areas", fontweight="bold")
    ax.set_xlabel(""); ax.set_ylabel("$M")
    ax.set_ylim(0, None)
    import matplotlib.ticker as mt
    ax.yaxis.set_major_formatter(mt.FuncFormatter(lambda y, _: f"${y/1e6:.0f}M"))
    plt.tight_layout(); plt.savefig("/tmp/c_labor.png"); plt.close()


def build():
    s = json.load(open("data/analytics_summary.json"))
    exc = pd.read_csv("data/exceptions.csv")
    var = pd.read_csv("data/cc_variance.csv")
    pay = pd.read_csv("data/payroll_actuals.csv", dtype={"ledger_account": str})
    pay["actual_amount"] = pay["actual_amount"].astype(float)
    pay["month"] = pd.to_datetime(pay["month"])
    cc = pd.read_csv("data/cost_centers.csv", dtype=str)

    chart_exceptions(exc); chart_variance(var); chart_labor(pay)

    doc = SimpleDocTemplate("docs/Workday_Cost_Center_Governance_Portfolio.pdf",
                            pagesize=LETTER, topMargin=0.7*inch, bottomMargin=0.7*inch)
    styles = getSampleStyleSheet()
    title = ParagraphStyle("Title2", parent=styles["Title"], textColor=NAVY, fontSize=26,
                           leading=30, spaceAfter=6)
    h1 = ParagraphStyle("H1", parent=styles["Heading1"], textColor=NAVY, fontSize=15,
                        spaceBefore=14, spaceAfter=8, keepWithNext=True)
    h2 = ParagraphStyle("H2", parent=styles["Heading2"], textColor=TEAL, fontSize=12,
                        spaceBefore=10, spaceAfter=6, keepWithNext=True)
    body = ParagraphStyle("Body2", parent=styles["BodyText"], fontSize=10, leading=14.5,
                          spaceAfter=6, textColor=colors.HexColor("#222222"))
    bullet = ParagraphStyle("Bullet2", parent=body, leftIndent=18, bulletIndent=8,
                            spaceAfter=4)
    cap = ParagraphStyle("Cap", parent=styles["BodyText"], fontSize=8.5, textColor=GRAY,
                         alignment=1, spaceAfter=10)
    story = []

    # ---- cover ----
    story += [Spacer(1, 1.6*inch),
              Paragraph("Workday Cost Center<br/>Governance &amp; Analytics", title),
              Spacer(1, 0.15*inch),
              Paragraph("A controllership-grade control framework over Workday HCM &amp; "
                        "Financials extracts — exception triage, budget variance, and "
                        "labor analytics for a regional health system.", body),
              Spacer(1, 0.3*inch),
              Paragraph("Sundara Prasanthi Movva · Senior Financial Analyst, Healthcare FP&amp;A",
                        ParagraphStyle("by", parent=body, textColor=GRAY)),
              Paragraph("Python · SQL-style analytics · Streamlit · Workday concepts (EIB, "
                        "supervisory orgs, worktags, journals)", cap),
              PageBreak()]

    # ---- executive summary ----
    story.append(Paragraph("Executive summary", h1))
    story.append(Paragraph(
        "Cost centers are the foundation every healthcare finance number stands on. When the "
        "cost-center master is wrong — orphan codes, lapsed owner attestations, journals that "
        "bypass segregation of duties — budgets misallocate, labor spend hides, and the "
        "month-end close slows. I built an end-to-end governance program that treats Workday "
        "extracts the way a controllership team should: <b>validate first, analyze second</b>.",
        body))
    kpis = [
        ["22", "Active cost centers governed"],
        [str(s["exception_count"]), f"Exceptions surfaced ({s['critical_exceptions']} critical)"],
        ["7", "SOX-style controls, severity-ranked with SLA triage"],
        [f"{s['attestation_compliance']:.0%}", "Owner attestation compliance (Q2 FY25)"],
        [f"{s['auto_post_rate']:.1%}", "Journal auto-post rate"],
        [f"${s['net_variance']/1e6:+.1f}M", "Net TTM budget variance on $429M spend"],
    ]
    t = Table([[Paragraph(f"<b><font size=13 color='#1b2a4a'>{a}</font></b>", body),
                Paragraph(b, body)] for a, b in kpis], colWidths=[1.4*inch, 5.1*inch])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), LIGHT),
                           ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                           ("LEFTPADDING", (0, 0), (-1, -1), 10),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                           ("LINEBELOW", (0, 0), (-1, -2), 0.5, colors.white)]))
    story += [t, Spacer(1, 0.1*inch),
              Paragraph("Bottom line: the framework caught spend posting to a closed cost center, "
                        "25 segregation-of-duties violations, and an agency-labor spiral in "
                        "nursing that is driving unfavorable variance — the exact findings a "
                        "Finance leader needs before close, not after.", body)]

    # ---- why it matters ----
    story.append(Paragraph("Why cost-center governance decides close quality", h1))
    for b in [
        "Every journal, payroll run, and budget load in Workday keys off the cost center. "
        "Bad master data compounds into every downstream report.",
        "In healthcare, labor is 55–60% of operating expense. If agency and overtime "
        "dollars land on the wrong codes, productivity metrics lie.",
        "Auditors test exactly these controls: SoD on journals, approval thresholds, "
        "and attestation evidence. Findings here are audit findings.",
    ]:
        story.append(Paragraph(b, bullet, bulletText="•"))

    # ---- control framework ----
    story.append(Paragraph("Control framework", h1))
    story.append(Paragraph(
        "Seven preventive/detective controls, each mapped to a Workday concept and ranked by "
        "financial-statement risk. Critical findings carry a 5-day remediation SLA; High, 15 days.",
        body))
    controls = [
        ["Control", "Severity", "Control name", "What it checks"],
        ["CC-01", "Critical", "No orphan cost centers", "Every cost center maps to an active supervisory org"],
        ["CC-02", "High", "Owner attestation current", "Quarterly attestation; no lapse in last 2 quarters"],
        ["CC-03", "Critical", "Segregation of duties", "Journal requester \u2260 approver"],
        ["CC-04", "High", "Large-journal approval", "Journals > $25K require director approval"],
        ["CC-05", "Critical", "No spend on inactive codes", "Closed cost centers must carry zero spend"],
        ["CC-06", "Medium", "Worker cost-center assignment", "Every active worker assigned to a cost center"],
        ["CC-07", "Medium", "Budget coverage", "Every active cost center has an FY budget"],
    ]
    hdr = [Paragraph(f"<b><font color='white'>{c}</font></b>", body) for c in controls[0]]
    rows = [[Paragraph(f"<b>{r[0]}</b>", body), Paragraph(r[1], body),
             Paragraph(f"<b>{r[2]}</b>", body), Paragraph(r[3], body)] for r in controls[1:]]
    ct = Table([hdr] + rows, colWidths=[0.7*inch, 0.9*inch, 2.1*inch, 2.8*inch],
               repeatRows=1)
    ct.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"), ("GRID", (0, 0), (-1, -1), 0.5, colors.white),
        ("LEFTPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
    # header row styling fix: first row is data; add explicit header
    story.append(ct)
    story.append(Spacer(1, 0.1*inch))
    story.append(Image("/tmp/c_exc.png", width=6.8*inch, height=3.2*inch))
    story.append(Paragraph("Figure 1 — Findings by control. Journal SoD (CC-03) is the "
                           "weakest control; master-data defects (CC-01/CC-05) are few but critical.",
                           cap))

    # ---- findings deep dive ----
    story.append(Paragraph("What the data found", h1))
    story.append(Paragraph("The money story: premium-labor spiral in nursing", h2))
    story.append(Paragraph(
        "Med/Surg Nursing (CC-1080) and ICU (CC-1090) are the only cost centers running over "
        "budget — +$1.06M (+2.9%) and +$1.04M (+3.5%) respectively. The driver is not base wages; "
        "it is agency labor, which has climbed past 10% of base pay in both units while overtime "
        "holds at 7% system-wide. Agency dollars cost roughly 2× employed staff, so a double-digit "
        "agency mix mathematically guarantees unfavorable variance. Recommended actions: float-pool "
        "expansion, targeted retention review, and a 90-day agency-reduction target with weekly "
        "tracking — the standard playbook, now backed by the numbers.", body))
    story.append(Image("/tmp/c_var.png", width=6.8*inch, height=4.0*inch))
    story.append(Paragraph("Figure 2 — Trailing-12-month budget variance by cost center.", cap))
    story.append(Image("/tmp/c_labor.png", width=6.8*inch, height=3.2*inch))
    story.append(Paragraph("Figure 3 — Labor mix trend. The agency (red) band widens in the "
                           "last two quarters — the visual signature of the spiral.", cap))

    story.append(Paragraph("Master-data and journal findings", h2))
    for b in [
        "<b>$518K posted to a closed cost center (CC-3010, Closed Wound Care).</b> Spend hitting "
        "an inactive code means budgets and productivity metrics for the receiving units are "
        "wrong. Fix: hard-stop validation on the EIB payroll load.",
        "<b>25 journals where requester = approver.</b> A textbook SoD failure and an audit "
        "finding waiting to happen. Fix: Workday business-process routing that physically "
        "prevents self-approval.",
        "<b>9 journals over $25K without director approval,</b> plus attestation compliance at "
        "90% with Operations the weakest division — the attestation process needs an owner "
        "escalation workflow, not another reminder email.",
    ]:
        story.append(Paragraph(b, bullet, bulletText="•"))

    # ---- operating model ----
    story.append(Paragraph("How I'd run this in production", h1))
    for b in [
        "<b>Monthly EIB extracts</b> from Workday HCM/Financials into the control engine; "
        "exceptions auto-routed to cost-center owners with SLA clocks.",
        "<b>Pre-close checkpoint:</b> CC-01 through CC-05 must clear before the close checklist "
        "opens — no more discovering master-data breaks on day 4 of close.",
        "<b>Quarterly attestation campaign</b> with escalation to division finance leads at "
        "day 10, not day 30.",
        "<b>Executive read-out:</b> one page — exceptions by severity, variance vs. budget, "
        "agency/overtime trend. The dashboard in this repo is that page, live.",
    ]:
        story.append(Paragraph(b, bullet, bulletText="•"))

    # ---- tech ----
    story.append(Paragraph("Build notes", h1))
    story.append(Paragraph(
        "Python (pandas, NumPy) for the extract simulation and control engine; a severity-ranked "
        "exception queue as the triage artifact; Plotly/Streamlit for the command-center "
        "dashboard; matplotlib + ReportLab for this document. All data is synthetic and modeled "
        "on real Workday concepts — supervisory orgs, worktags, ledger accounts, EIB loads, "
        "and business-process approvals. Repository includes the full pipeline: "
        "<font color='#0e7c7b'>generate → govern → analyze → visualize</font>.", body))
    story.append(Paragraph("About the author", h2))
    story.append(Paragraph(
        "Sundara Prasanthi Movva is a Senior Financial Analyst in healthcare FP&amp;A — "
        "Financial Analyst at Humana (2025–present), Senior Financial Analyst at Optum / "
        "UnitedHealth Group (2021–2022), Financial Analyst at Cigna (2017–2021) — with an MBA "
        "in Business Analytics. Day-to-day work: budgeting, variance analysis, labor-spend "
        "analytics, and Workday cost-center governance across 40+ cost centers.", body))

    doc.build(story)
    print("docs/Workday_Cost_Center_Governance_Portfolio.pdf written")


if __name__ == "__main__":
    build()
