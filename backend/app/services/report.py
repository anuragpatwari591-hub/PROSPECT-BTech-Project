"""PDF report generation with ReportLab (pure Python, no browser or system fonts needed)."""

from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.graphics.charts.lineplots import LinePlot
from reportlab.graphics.shapes import Drawing, Rect, String
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.engines.metrics import METRIC_DEFINITIONS

INK = colors.HexColor("#1B2733")
MUTED = colors.HexColor("#5B6B7A")
RULE = colors.HexColor("#D5DCE3")
LEVEL_COLORS = {"LOW": "#2F7D6B", "MEDIUM": "#B7892B", "HIGH": "#C2551F", "CRITICAL": "#8E1F2F"}
DIM_COLORS = ["#2F5D8A", "#4F8A8B", "#B7892B", "#8C5A9E", "#6B7A3A"]


def _styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("t", parent=base["Title"], fontName="Helvetica-Bold", fontSize=20, textColor=INK,
                                alignment=0, spaceAfter=2),
        "h2": ParagraphStyle("h2", parent=base["Heading2"], fontName="Helvetica-Bold", fontSize=13, textColor=INK,
                             spaceBefore=10, spaceAfter=4),
        "body": ParagraphStyle("b", parent=base["BodyText"], fontName="Helvetica", fontSize=9.5, leading=13,
                               textColor=INK),
        "small": ParagraphStyle("s", parent=base["BodyText"], fontName="Helvetica", fontSize=8, leading=10.5,
                                textColor=MUTED),
        "cell": ParagraphStyle("c", fontName="Helvetica", fontSize=8, leading=10, textColor=INK),
        "big": ParagraphStyle("big", fontName="Helvetica-Bold", fontSize=22, leading=26, textColor=INK),
        "mid": ParagraphStyle("mid", fontName="Helvetica-Bold", fontSize=14, leading=26, textColor=INK),
    }


def _table(rows, widths, header=True):
    table = Table(rows, colWidths=widths, repeatRows=1 if header else 0)
    style = [("FONT", (0, 0), (-1, -1), "Helvetica", 8), ("TEXTCOLOR", (0, 0), (-1, -1), INK),
             ("LINEBELOW", (0, 0), (-1, -1), 0.4, RULE), ("VALIGN", (0, 0), (-1, -1), "TOP"),
             ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]
    if header:
        style += [("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 8), ("LINEBELOW", (0, 0), (-1, 0), 0.8, INK)]
    table.setStyle(TableStyle(style))
    return table


def _fmt(value, unit=""):
    if value is None:
        return "—"
    text = f"{value:.0f}" if float(value).is_integer() or abs(value) >= 100 else f"{value:.2f}"
    return f"{text} {unit}".strip()


def _contribution_bar(dimensions: list[dict], score: float) -> Drawing:
    width, height = 170 * mm, 22 * mm
    d = Drawing(width, height)
    d.add(Rect(0, 8 * mm, width, 7 * mm, fillColor=colors.HexColor("#EEF1F4"), strokeColor=None))
    x = 0.0
    for i, dim in enumerate(x for x in dimensions if x.get("status") == "scored"):
        w = width * dim["contribution"] / 100
        d.add(Rect(x, 8 * mm, w, 7 * mm, fillColor=colors.HexColor(DIM_COLORS[i % 5]), strokeColor=colors.white))
        if w > 18 * mm:
            d.add(String(x + 2, 1.5 * mm, f"{dim['label'].replace(' risk', '')} {dim['contribution']:.1f}",
                         fontName="Helvetica", fontSize=7, fillColor=MUTED))
        x += w
    d.add(String(0, 17 * mm, f"Where the {score:.0f} risk points come from (scale 0–100)",
                 fontName="Helvetica-Bold", fontSize=8, fillColor=INK))
    return d


def _history_chart(points) -> Drawing:
    d = Drawing(170 * mm, 50 * mm)
    lp = LinePlot()
    lp.x, lp.y, lp.width, lp.height = 12 * mm, 8 * mm, 150 * mm, 36 * mm
    lp.data = [[(i, p.risk_score) for i, p in enumerate(points)]]
    lp.lines[0].strokeColor = INK
    lp.lines[0].strokeWidth = 1.5
    lp.yValueAxis.valueMin, lp.yValueAxis.valueMax, lp.yValueAxis.valueStep = 0, 100, 25
    lp.xValueAxis.valueMin, lp.xValueAxis.valueMax = 0, max(1, len(points) - 1)
    lp.xValueAxis.valueStep = max(1, len(points) // 6)
    lp.xValueAxis.labelTextFormat = lambda i: f"#{points[int(i)].run_id}" if int(i) < len(points) else ""
    d.add(lp)
    return d


def build_report(project, run, history, scenarios, disclaimer: str) -> bytes:
    s = _styles()
    a = run.assessment
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm, topMargin=18 * mm,
                            bottomMargin=18 * mm, title=f"PROSPECT risk report — {project.name}",
                            author="PROSPECT")
    level_color = LEVEL_COLORS.get(a.risk_level, "#1B2733")
    story = [
        Paragraph(f"Risk report: {escape(project.name)}", s["title"]),
        Paragraph(f"{escape(project.url)} — analysis run #{run.id}, completed "
                  f"{run.finished_at:%d %b %Y %H:%M} UTC", s["small"]),
        Spacer(1, 6 * mm),
        _table([["Risk score", "Risk level", "Health score", "Data coverage"],
                [Paragraph(f"{a.risk_score:.0f}", s["big"]),
                 Paragraph(f"<font color='{level_color}'>{a.risk_level}</font>", s["mid"]),
                 Paragraph(f"{a.health_score:.0f}", s["big"]),
                 Paragraph(f"{a.coverage * 100:.0f}% of weight", s["mid"])]],
               [42 * mm, 42 * mm, 42 * mm, 44 * mm]),
        Spacer(1, 4 * mm),
        _contribution_bar(a.dimensions, a.risk_score),
        Paragraph(escape(disclaimer), s["small"]),
    ]
    if project.description:
        story += [Spacer(1, 2 * mm), Paragraph(f"Repository description: {escape(project.description)}", s["small"])]
    if run.collection_notes:
        story += [Paragraph("Data notes: " + escape(" ".join(run.collection_notes)), s["small"])]

    story.append(Paragraph("Main risk factors", s["h2"]))
    top = sorted((f for f in a.factors if f.contribution > 0), key=lambda f: f.contribution, reverse=True)
    rows = [["Factor", "Value", "Score", "Points", "Explanation"]]
    for f in top[:10]:
        name = METRIC_DEFINITIONS.get(f.metric_key, {}).get("name", f.metric_key)
        rows.append([Paragraph(f"{escape(name)}<br/><font color='#5B6B7A' size=6.5>{escape(f.signal_key)}</font>",
                               s["cell"]), _fmt(f.metric_value), f"{f.score:.0f}", f"{f.contribution:.1f}",
                     Paragraph(escape(f.explanation), s["cell"])])
    story.append(_table(rows, [40 * mm, 15 * mm, 13 * mm, 13 * mm, 89 * mm]))
    story.append(Paragraph("Score = this signal's 0–100 risk; Points = what it adds to the overall risk score.",
                           s["small"]))

    story.append(Paragraph("Recommendations", s["h2"]))
    if a.recommendations:
        for r in sorted(a.recommendations, key=lambda r: r.priority != "HIGH"):
            story.append(Paragraph(f"<b>[{r.priority}] {escape(r.title)}</b> — {escape(r.detail)} "
                                   f"<font color='#5B6B7A'>(triggered by {escape(r.signal_key)})</font>", s["body"]))
            story.append(Spacer(1, 1.5 * mm))
    else:
        story.append(Paragraph("No signal reached the recommendation threshold (score ≥ 50).", s["body"]))

    story += [PageBreak(), Paragraph("Metrics", s["h2"])]
    rows = [["Metric", "Value", "Definition"]]
    for m in sorted(run.metrics, key=lambda m: list(METRIC_DEFINITIONS).index(m.key)):
        definition = METRIC_DEFINITIONS[m.key]
        rows.append([Paragraph(escape(definition["name"]), s["cell"]), _fmt(m.value, m.unit),
                     Paragraph(escape(definition["definition"]), s["cell"])])
    story.append(_table(rows, [45 * mm, 30 * mm, 95 * mm]))

    story.append(Paragraph("Historical trend", s["h2"]))
    if len(history) >= 2:
        story.append(_history_chart(history))
    else:
        story.append(Paragraph("Only one completed analysis is stored, so no trend is shown. "
                               "Trends appear after repeated analyses over time.", s["body"]))

    story.append(Paragraph("What-If simulations (estimates)", s["h2"]))
    if scenarios:
        rows = [["Changed metrics", "Baseline", "Simulated", "Difference"]]
        for sc in scenarios:
            changes = ", ".join(f"{k} = {v:g}" for k, v in sc.overrides.items())
            rows.append([Paragraph(escape(changes), s["cell"]), f"{sc.baseline_score:.1f}",
                         f"{sc.simulated_score:.1f}", f"{sc.simulated_score - sc.baseline_score:+.1f}"])
        story.append(_table(rows, [100 * mm, 22 * mm, 22 * mm, 26 * mm]))
        story.append(Paragraph("SIMULATION / ESTIMATE: shows how the rule-based score responds to hypothetical "
                               "values. It is not a prediction of future risk.", s["small"]))
    else:
        story.append(Paragraph("No simulations were run for this analysis.", s["body"]))

    ml = run.ml_output or {}
    dorm = ml.get("dormancy") or {}
    story.append(Paragraph("Experimental machine learning output", s["h2"]))
    if dorm.get("status") in ("ok", "unreliable"):
        story.append(Paragraph(
            f"Estimated probability of no commits in the next 180 days: {dorm['probability_dormant_180d']:.2f} "
            f"({escape(dorm['message'])}) This model is experimental; on held-out repositories it did not "
            "clearly outperform a simple recency rule. It is not used in the risk score.", s["body"]))
    else:
        story.append(Paragraph(escape(dorm.get("message", "Not available.")), s["body"]))
    anomalies = (ml.get("anomaly") or {}).get("anomalies") or []
    story.append(Paragraph(f"Unusual weeks detected by Isolation Forest: {len(anomalies)}.", s["body"]))

    story.append(KeepTogether([
        Paragraph("Methodology", s["h2"]),
        Paragraph("Data is collected from the GitHub REST API (commits on the default branch, issues, pull requests, "
                  "contributors, releases). Metrics are computed over 30/90/365-day windows. Each risk signal maps "
                  "one metric to 0–100 by piecewise-linear interpolation between configured thresholds; dimension "
                  "scores are averages of their signals; the overall score is the weighted sum of dimension scores, "
                  "with weights renormalised over dimensions that have data. Signal contributions add up to the "
                  "overall score. Health score = 100 − risk score.", s["body"]),
        Paragraph("Limitations", s["h2"]),
        Paragraph("Thresholds and weights are heuristic and not empirically validated. GitHub activity is a partial "
                  "view of a project (private discussions, other trackers and non-code work are invisible). Commit "
                  "counts are a proxy for contribution. Page caps can truncate large repositories. Scores are best "
                  "compared with the same project's own history rather than across projects.", s["body"]),
    ]))

    def footer(canvas, _doc):
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(MUTED)
        canvas.drawString(20 * mm, 10 * mm, f"PROSPECT — {project.name} — run #{run.id}")
        canvas.drawRightString(190 * mm, 10 * mm, f"Page {_doc.page}")

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return buf.getvalue()
