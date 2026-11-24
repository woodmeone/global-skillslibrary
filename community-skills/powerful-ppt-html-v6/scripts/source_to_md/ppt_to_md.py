#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ppt_to_md.py - PowerPoint (PPTX) to Markdown Converter

Usage:
    python scripts/source_to_md/ppt_to_md.py <input.pptx>
    python scripts/source_to_md/ppt_to_md.py <input.pptx> -o output.md

Dependencies:
    pip install python-pptx
"""

import argparse
import os
import re
import sys
import zipfile
from pathlib import Path

try:
    from pptx import Presentation
    from pptx.util import Inches, Pt
except ImportError:
    print("Error: This script requires 'python-pptx'.")
    print("Please run: pip install python-pptx")
    sys.exit(1)


def extract_slide_number(slide_name: str) -> int:
    """Extract slide number from slide XML filename like 'slide12.xml'."""
    match = re.search(r'(\d+)', slide_name)
    return int(match.group(1)) if match else 0


def get_slide_layout_name(slide) -> str:
    """Get the layout name of a slide."""
    try:
        return slide.slide_layout.name or ""
    except Exception:
        return ""


def detect_heading_level(shape, layout_name: str) -> int:
    """Detect heading level based on shape type and font size."""
    if not shape.has_text_frame:
        return 0

    text = shape.text_frame.text.strip()
    if not text:
        return 0

    layout_lower = layout_name.lower()

    if any(kw in layout_lower for kw in ['title', 'cover']):
        return 1

    for para in shape.text_frame.paragraphs:
        for run in para.runs:
            if run.font.size:
                pt_size = run.font.size.pt
                if pt_size >= 36:
                    return 1
                elif pt_size >= 28:
                    return 2
                elif pt_size >= 22:
                    return 3
                elif pt_size >= 18:
                    return 4
                break
        break

    return 0


def is_title_shape(shape) -> bool:
    """Check if shape is a title placeholder."""
    if hasattr(shape, 'placeholder_format') and shape.placeholder_format:
        idx = shape.placeholder_format.idx
        return idx in (0, 1)
    return False


def extract_text_from_shape(shape) -> str:
    """Extract formatted text from a shape."""
    if not shape.has_text_frame:
        return ""

    lines = []
    for para in shape.text_frame.paragraphs:
        parts = []
        for run in para.runs:
            text = run.text
            if not text.strip():
                parts.append(text)
                continue

            if run.font.bold:
                text = f"**{text}**"
            if run.font.italic:
                text = f"*{text}*"
            if run.font.underline:
                text = f"<u>{text}</u>"
            parts.append(text)

        line = "".join(parts).strip()
        if line:
            level = para.level
            indent = "  " * level
            if para.level > 0:
                line = f"{indent}- {line}"
            lines.append(line)

    return "\n".join(lines)


def extract_table_from_shape(shape) -> str:
    """Extract table from a shape and convert to Markdown table."""
    if not shape.has_table:
        return ""

    table = shape.table
    rows_data = []

    for row_idx, row in enumerate(table.rows):
        cells = []
        for cell in row.cells:
            cell_text = cell.text.strip().replace("\n", " ")
            cells.append(cell_text)
        rows_data.append(cells)

    if not rows_data:
        return ""

    max_cols = max(len(r) for r in rows_data)
    for row in rows_data:
        while len(row) < max_cols:
            row.append("")

    md_lines = []
    header = "| " + " | ".join(rows_data[0]) + " |"
    separator = "| " + " | ".join(["---"] * max_cols) + " |"
    md_lines.append(header)
    md_lines.append(separator)

    for row in rows_data[1:]:
        md_lines.append("| " + " | ".join(row) + " |")

    return "\n".join(md_lines)


def process_slide(slide, slide_idx: int) -> str:
    """Process a single slide and return Markdown content."""
    layout_name = get_slide_layout_name(slide)
    parts = []

    has_title = False

    for shape in slide.shapes:
        if shape.has_table:
            table_md = extract_table_from_shape(shape)
            if table_md:
                parts.append(f"\n{table_md}\n")
            continue

        if not shape.has_text_frame:
            continue

        text = shape.text_frame.text.strip()
        if not text:
            continue

        if is_title_shape(shape) and not has_title:
            heading_level = detect_heading_level(shape, layout_name)
            if heading_level == 0:
                heading_level = 2 if slide_idx > 0 else 1
            parts.append(f"\n{'#' * heading_level} {text}\n")
            has_title = True
        else:
            extracted = extract_text_from_shape(shape)
            if extracted:
                parts.append(f"\n{extracted}\n")

    if not parts:
        parts.append(f"\n<!-- Slide {slide_idx + 1}: (empty or image-only) -->\n")

    return "\n".join(parts)


def extract_notes(slide) -> str:
    """Extract speaker notes from a slide."""
    try:
        if slide.has_notes_slide:
            notes_slide = slide.notes_slide
            text = notes_slide.notes_text_frame.text.strip()
            if text:
                return text
    except Exception:
        pass
    return ""


def pptx_to_markdown(input_path: str, include_notes: bool = False) -> str:
    """Convert a PPTX file to Markdown."""
    prs = Presentation(input_path)
    sections = []

    sections.append(f"<!-- Source: {os.path.basename(input_path)} -->")
    sections.append(f"<!-- Slides: {len(prs.slides)} -->\n")

    for idx, slide in enumerate(prs.slides):
        slide_md = process_slide(slide, idx)
        sections.append(slide_md)

        if include_notes:
            notes = extract_notes(slide)
            if notes:
                sections.append(f"\n> **Notes:** {notes}\n")

        if idx < len(prs.slides) - 1:
            sections.append("\n---\n")

    return "\n".join(sections)


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="PowerPoint (PPTX) to Markdown Converter")
    parser.add_argument("input", help="Input PPTX file path")
    parser.add_argument("-o", "--output", help="Output Markdown file path")
    parser.add_argument("--notes", action="store_true",
                        help="Include speaker notes")

    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: File not found: {input_path}")
        sys.exit(1)

    if not input_path.suffix.lower() == '.pptx':
        print(f"Error: Only .pptx files are supported (got {input_path.suffix})")
        sys.exit(1)

    print(f"[Converting] {input_path.name}")

    try:
        markdown = pptx_to_markdown(str(input_path), include_notes=args.notes)
    except Exception as e:
        print(f"Error: Failed to convert: {e}")
        sys.exit(1)

    if args.output:
        output_path = args.output
    else:
        output_path = str(input_path.with_suffix('.md'))

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(markdown)

    slide_count = markdown.count("---") + 1
    print(f"[Done] {slide_count} slides -> {output_path}")
    print(f"       {len(markdown)} characters")


if __name__ == "__main__":
    main()
