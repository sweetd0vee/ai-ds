"""Экспорт гипотез в DOCX."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt, RGBColor

from .hypotheses import format_hypotheses_text

ACCENT = RGBColor(0x1D, 0x4E, 0xD8)
MUTED = RGBColor(0x6B, 0x72, 0x80)
BODY = RGBColor(0x1F, 0x29, 0x37)

_PRIORITY_COLORS = {
    "high": RGBColor(0xB9, 0x1C, 0x1C),
    "medium": RGBColor(0xB4, 0x5A, 0x00),
    "low": RGBColor(0x05, 0x76, 0x69),
}


def build_hypotheses_docx(
    hypotheses: list[dict],
    output_path: Path,
    *,
    source_file: str = "",
    raw_fallback: str = "",
):
    doc = Document()
    title = doc.add_heading("Гипотезы о данных", level=0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER

    meta = doc.add_paragraph()
    meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = meta.add_run(
        f"Сформировано: {datetime.now().strftime('%d.%m.%Y %H:%M')}"
        + (f" · Файл: {source_file}" if source_file else "")
    )
    run.font.size = Pt(9)
    run.font.color.rgb = MUTED

    doc.add_paragraph()

    if hypotheses:
        for item in hypotheses:
            heading = doc.add_heading(f"{item.get('id', '?')}. {item.get('title', 'Гипотеза')}", level=2)
            for run in heading.runs:
                run.font.color.rgb = ACCENT

            priority = item.get("priority", "medium")
            p_line = doc.add_paragraph()
            p_run = p_line.add_run(f"Приоритет: {item.get('priority_label', priority)}")
            p_run.bold = True
            p_run.font.color.rgb = _PRIORITY_COLORS.get(priority, BODY)

            for label, key in (
                ("Формулировка", "statement"),
                ("Основание", "rationale"),
                ("Как проверить", "verification"),
            ):
                value = item.get(key, "")
                if not value:
                    continue
                para = doc.add_paragraph()
                label_run = para.add_run(f"{label}: ")
                label_run.bold = True
                label_run.font.color.rgb = BODY
                para.add_run(value)

            columns = item.get("columns") or []
            if columns:
                para = doc.add_paragraph()
                label_run = para.add_run("Столбцы: ")
                label_run.bold = True
                para.add_run(", ".join(columns))

            doc.add_paragraph()
    else:
        for line in (raw_fallback or format_hypotheses_text([])).splitlines():
            if line.strip():
                doc.add_paragraph(line)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(output_path))
