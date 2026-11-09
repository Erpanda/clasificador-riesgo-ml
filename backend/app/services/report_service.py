from __future__ import annotations

import io
from typing import Any

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet


def build_csv(results: list[dict[str, Any]]) -> bytes:
    flattened = []
    for result in results:
        flattened.append({
            "estudiante_id": result.get("estudiante_id"),
            **(result.get("datos_entrada") or {}),
            "riesgo_predicho": result.get("estado_predicho"),
            "probabilidad_riesgo": result.get("probabilidad_riesgo"),
            "estado_real": result.get("estado_real"),
            "version_modelo": result.get("version_modelo"),
        })
    return pd.DataFrame(flattened).to_csv(index=False).encode("utf-8-sig")


def build_pdf(results: list[dict[str, Any]], batch_id: str | None = None) -> bytes:
    buffer = io.BytesIO()
    document = SimpleDocTemplate(buffer, pagesize=landscape(A4), rightMargin=24, leftMargin=24, topMargin=28, bottomMargin=24)
    styles = getSampleStyleSheet()
    story = [Paragraph("Reporte de clasificación de riesgo académico", styles["Title"]), Spacer(1, 10)]
    risk_count = sum(row["estado_predicho"] == "En riesgo" for row in results)
    story.append(Paragraph(f"Registros procesados: {len(results)} | En riesgo: {risk_count} | Sin riesgo: {len(results) - risk_count}", styles["BodyText"]))
    if batch_id:
        story.append(Paragraph(f"Código de carga: {batch_id}", styles["BodyText"]))
    story.append(Spacer(1, 14))
    data = [["Código", "Predicción", "Prob. riesgo", "Estado real", "Indicadores", "Versión"]]
    data.extend([
        [str(row["estudiante_id"]), str(row["estado_predicho"]), f"{float(row['probabilidad_riesgo']):.1%}", str(row.get("estado_real") or "—"), ", ".join(item.get("variable", "") for item in row.get("factores", [])[:2]) or "—", str(row["version_modelo"])]
        for row in results
    ])
    table = Table(data, repeatRows=1, colWidths=[92, 92, 82, 92, 150, 105])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#183153")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#d8e0eb")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f4f7fb")]),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(table)
    document.build(story)
    return buffer.getvalue()

