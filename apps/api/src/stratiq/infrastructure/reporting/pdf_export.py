from __future__ import annotations

from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
from io import BytesIO

from stratiq.domain.entities import DecisionCard, ExecutiveReport


def build_executive_pdf(report: ExecutiveReport, cards: list[DecisionCard]) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=LETTER, title="StratIQ Executive Report")
    styles = getSampleStyleSheet()
    story = [
        Paragraph("StratIQ Executive Report", styles["Title"]),
        Spacer(1, 0.2 * inch),
        Paragraph(
            f"Business Health: {report.health_label.value.upper()} ({report.health_score}/100) "
            f"· confidence {report.confidence:.2f}",
            styles["Heading2"],
        ),
        Spacer(1, 0.1 * inch),
        Paragraph("Executive Summary", styles["Heading2"]),
        Paragraph(report.summary.replace("\n", "<br/>"), styles["BodyText"]),
        Spacer(1, 0.2 * inch),
        Paragraph("Decision Timeline", styles["Heading2"]),
    ]
    for event in report.timeline:
        story.append(
            Paragraph(
                f"<b>{event.get('title', '')}</b> [{event.get('severity', 'medium')}]"
                f"<br/>{event.get('detail', '')}",
                styles["BodyText"],
            )
        )
        story.append(Spacer(1, 0.08 * inch))

    story.append(Spacer(1, 0.15 * inch))
    story.append(Paragraph("Decision Cards", styles["Heading2"]))
    for card in cards:
        story.append(Paragraph(f"{card.topic or card.kpi_name}", styles["Heading3"]))
        story.append(Paragraph(f"<b>KPI signal:</b> {card.kpi_signal}", styles["BodyText"]))
        story.append(
            Paragraph(
                f"<b>Mode:</b> {card.evidence_mode.value} · <b>Confidence:</b> {card.confidence:.2f}",
                styles["BodyText"],
            )
        )
        story.append(Paragraph(f"<b>What happened:</b> {card.what_happened}", styles["BodyText"]))
        story.append(Paragraph(f"<b>Why:</b> {card.why_it_happened}", styles["BodyText"]))
        story.append(Paragraph(f"<b>Business impact:</b> {card.business_impact}", styles["BodyText"]))
        if card.risks:
            story.append(Paragraph("<b>Risks:</b> " + "; ".join(card.risks), styles["BodyText"]))
        if card.opportunities:
            story.append(
                Paragraph("<b>Opportunities:</b> " + "; ".join(card.opportunities), styles["BodyText"])
            )
        story.append(Paragraph(f"<b>Recommendation:</b> {card.recommendation}", styles["BodyText"]))
        story.append(
            Paragraph(f"<b>Expected outcome:</b> {card.expected_outcome}", styles["BodyText"])
        )
        if card.forecast_value or card.forecast_explanation:
            story.append(
                Paragraph(
                    "<b>Forecast:</b> "
                    f"{card.forecast_value or ''} ({card.forecast_horizon or 'n/a'}) — "
                    f"{card.forecast_explanation or ''}",
                    styles["BodyText"],
                )
            )
        story.append(Spacer(1, 0.12 * inch))

    doc.build(story)
    return buffer.getvalue()
