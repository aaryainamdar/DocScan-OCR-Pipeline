"""
pipeline/pdf_exporter.py
------------------------
Generates a formatted PDF report from the structured OCR output.
Uses reportlab for PDF generation (no external binary required).
"""

import os
from datetime import datetime


def export_to_pdf(result: dict, output_dir: str, doc_id: str) -> str:
    """
    Create a formatted PDF from OCR result dict.

    Returns the path to the generated PDF.
    """
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.lib import colors
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
            HRFlowable
        )
        from reportlab.lib.enums import TA_LEFT, TA_CENTER

    except ImportError:
        raise RuntimeError("reportlab is not installed. Run: pip install reportlab")

    pdf_path = os.path.join(output_dir, f"{doc_id}_export.pdf")
    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm
    )

    styles = getSampleStyleSheet()
    story = []

    # ── Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Title'],
        fontSize=20,
        textColor=colors.HexColor('#1a1a2e'),
        spaceAfter=6
    )
    story.append(Paragraph("Document OCR Export", title_style))
    story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#4361ee')))
    story.append(Spacer(1, 0.4 * cm))

    # ── Metadata table
    output = result.get('output', {})
    ocr = result.get('ocr', {})
    preprocessing = result.get('preprocessing', {})

    meta_data = [
        ['Document ID', result.get('doc_id', 'N/A')[:16] + '...'],
        ['OCR Engine', ocr.get('engine', 'N/A').capitalize()],
        ['Language', ocr.get('language', 'N/A')],
        ['Confidence', f"{ocr.get('confidence', 0):.1f}%"],
        ['Word Count', str(output.get('word_count', 'N/A'))],
        ['Processing Time', f"{result.get('processing_time_s', 'N/A')}s"],
        ['Processed At', output.get('processed_at', 'N/A')],
        ['Steps Applied', ', '.join(preprocessing.get('steps_applied', []))],
    ]

    meta_table = Table(meta_data, colWidths=[4 * cm, 12 * cm])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#eef2ff')),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#1a1a2e')),
        ('ROWBACKGROUNDS', (1, 0), (-1, -1), [colors.white, colors.HexColor('#f8f9ff')]),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#c7d2fe')),
        ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.HexColor('#e0e7ff')),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 0.5 * cm))

    # ── Summary
    if output.get('summary'):
        story.append(Paragraph("Summary", styles['Heading2']))
        story.append(Paragraph(output['summary'], styles['Normal']))
        story.append(Spacer(1, 0.4 * cm))

    # ── Detected Entities
    entities = output.get('entities', {})
    entity_rows = []
    for etype, values in entities.items():
        if values:
            entity_rows.append([etype.replace('_', ' ').title(), ', '.join(values)])

    if entity_rows:
        story.append(Paragraph("Detected Entities", styles['Heading2']))
        ent_table = Table([['Type', 'Values']] + entity_rows, colWidths=[4 * cm, 12 * cm])
        ent_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4361ee')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9ff')]),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#c7d2fe')),
            ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.HexColor('#e0e7ff')),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(ent_table)
        story.append(Spacer(1, 0.4 * cm))

    # ── Full Extracted Text
    story.append(Paragraph("Full Extracted Text", styles['Heading2']))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#c7d2fe')))
    story.append(Spacer(1, 0.2 * cm))

    cleaned = output.get('cleaned_text', ocr.get('raw_text', ''))
    body_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontSize=10,
        leading=15,
        spaceAfter=8
    )
    for para in cleaned.split('\n\n'):
        if para.strip():
            story.append(Paragraph(para.strip().replace('\n', ' '), body_style))

    doc.build(story)
    return pdf_path
