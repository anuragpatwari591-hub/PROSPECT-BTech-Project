"""Generates a PDF risk report from an analysis result dict."""
import io
from datetime import datetime, timezone

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

CLASSIFICATION_COLORS = {
    "LOW": colors.HexColor("#2e7d32"),
    "MEDIUM": colors.HexColor("#f9a825"),
    "HIGH": colors.HexColor("#ef6c00"),
    "CRITICAL": colors.HexColor("#c62828"),
}


def generate_pdf_report(analysis: dict) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        rightMargin=1.5 * cm,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("TitleX", parent=styles["Title"], fontSize=20)
    h2 = styles["Heading2"]
    body = styles["BodyText"]

    story = []
    story.append(Paragraph("PROSPECT Risk Analysis Report", title_style))
    story.append(Paragraph(analysis["repo_full_name"], h2))
    story.append(Paragraph(analysis.get("repo_url", ""), body))
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    story.append(Paragraph(f"Generated: {generated}", body))
    story.append(Spacer(1, 0.6 * cm))

    classification = analysis["classification"]
    color = CLASSIFICATION_COLORS.get(classification, colors.grey)
    score_table = Table(
        [
            ["Risk Score", "Health Score", "Classification"],
            [
                f"{analysis['risk_score']} / 100",
                f"{analysis['health_score']} / 100",
                classification,
            ],
        ],
        colWidths=[5.5 * cm] * 3,
    )
    score_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a1a2e")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("BACKGROUND", (2, 1), (2, 1), color),
                ("TEXTCOLOR", (2, 1), (2, 1), colors.white),
                ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 1), (-1, 1), 13),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.append(score_table)
    story.append(Spacer(1, 0.8 * cm))

    story.append(Paragraph("Risk Factors", h2))
    factor_rows = [["Category", "Points", "% of Max", "Explanation"]]
    for f in analysis["factors"]:
        reasons = " ".join(f["reasons"]) if f["reasons"] else "-"
        factor_rows.append(
            [
                f["label"],
                f"{f['points']}/{f['max_points']}",
                f"{f['pct_of_max']}%",
                Paragraph(reasons, body),
            ]
        )
    factor_table = Table(factor_rows, colWidths=[3.8 * cm, 2.2 * cm, 2.2 * cm, 8 * cm])
    factor_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eeeeee")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.append(factor_table)
    story.append(Spacer(1, 0.8 * cm))

    story.append(Paragraph("Recommendations", h2))
    for rec in analysis["recommendations"]:
        story.append(Paragraph(f"• {rec}", body))
    story.append(Spacer(1, 0.8 * cm))

    story.append(Paragraph("Repository Snapshot", h2))
    m = analysis.get("metrics", {})
    snapshot_rows = [
        ["Stars", str(analysis.get("stars", 0))],
        ["Forks", str(analysis.get("forks", 0))],
        ["Contributors sampled", str(m.get("contributor_count", 0))],
        ["Top contributor share", f"{m.get('top_contributor_pct', 0)}%"],
        ["Open issues", str(m.get("open_issue_count", 0))],
        ["Closed issues", str(m.get("closed_issue_count", 0))],
        ["Open pull requests", str(m.get("open_pr_count", 0))],
        ["Merged pull requests", str(m.get("merged_pr_count", 0))],
        ["Releases", str(m.get("release_count", 0))],
        ["Days since last push", str(m.get("days_since_last_push", "N/A"))],
        ["Days since last release", str(m.get("days_since_last_release", "N/A"))],
    ]
    snapshot_table = Table(snapshot_rows, colWidths=[6 * cm, 6 * cm])
    snapshot_table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(snapshot_table)

    doc.build(story)
    return buffer.getvalue()
