# -*- coding: utf-8 -*-
"""产品操作手册 DOCX 排版工具库。

实测有效的排版方案：A4 / 微软雅黑 / 1.55 行距 / 绿色操作强调色 /
灰底提示块 / 表格化字段清单 / 超高截图自动切分。

用法：
    from docx_kit import *
    doc = new_doc()
    page_number_footer(doc)
    doc_title(doc, "产品名 · 角色端")
    h1(doc, "一、章节")
    para(doc, "正文")
    add_image(doc, "shot.png", "图 1-1　说明")
    doc.save("out.docx")

依赖：python-docx、Pillow
"""
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Emu, Pt, RGBColor
from PIL import Image

# ---------- 可按品牌替换 ----------
FONT_CN = "微软雅黑"
FONT_EN = "Segoe UI"
ACCENT = RGBColor(0x0F, 0x6B, 0x4F)      # 强调色（操作词、步骤序号）
GRAY = RGBColor(0x64, 0x6A, 0x73)        # 次要文字 / 图注
DARK = RGBColor(0x1F, 0x23, 0x29)        # 正文标题
BLUE = RGBColor(0x33, 0x6D, 0xF4)        # URL / 代码
BODY_PT, H1_PT, H2_PT, TITLE_PT = 11, 16, 13, 20

# 图片源目录，调用方可覆盖
# 图片源目录（相对项目根，调用方通常覆盖成绝对路径）
# 重要：SHOTS 必须指向**唯一的**截图目录（shoot.py 的 --out），
# 不要在流程里另建压缩目录再读那份 —— 曾因指向旧压缩目录，
# 换了品牌后文档里仍是旧截图，排查了两轮。
SHOTS = Path("shots")                     # 产品截图（jpg，长图需切分）
FIGS = Path("figures")                    # 逻辑示意图（png，满版贴出）
SPLIT_DIR = Path("_split")                # 长图切分临时目录

# 注意：必须是纯数字（厘米）。若写成 Cm(15.5) 会与内部 Cm() 二次换算，
# 导致图片宽度放大到 24cm 以上、超出页面被裁切。这个坑踩过一次。
CONTENT_W = 15.5                          # A4 21cm − 左右各 2.75cm
MAX_IMG_H = 20.5


def set_run_font(run, size=None, bold=None, color=None, cn=FONT_CN):
    run.font.name = FONT_EN
    run._element.rPr.rFonts.set(qn("w:eastAsia"), cn)
    if size is not None:
        run.font.size = Pt(size)
    if bold is not None:
        run.font.bold = bold
    if color is not None:
        run.font.color.rgb = color


def new_doc():
    doc = Document()
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Cm(21), Cm(29.7)
    sec.top_margin = sec.bottom_margin = Cm(2.2)
    sec.left_margin = sec.right_margin = Cm(2.75)
    st = doc.styles["Normal"]
    st.font.name = FONT_EN
    st.font.size = Pt(BODY_PT)
    st.element.rPr.rFonts.set(qn("w:eastAsia"), FONT_CN)
    st.paragraph_format.line_spacing = 1.55
    st.paragraph_format.space_after = Pt(4)
    return doc


# ---------- 页脚页码 ----------
def page_number_footer(doc, fmt="第 {n} 页"):
    p = doc.sections[0].footer.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    prefix, suffix = fmt.split("{n}")
    if prefix:
        set_run_font(p.add_run(prefix), 9, color=GRAY)
    _add_field(p, "PAGE")
    if suffix:
        set_run_font(p.add_run(suffix), 9, color=GRAY)


def _add_field(paragraph, field):
    run = paragraph.add_run()
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = field
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    for node in (begin, instr, end):
        run._r.append(node)
    set_run_font(run, 9, color=GRAY)


# ---------- 标题 ----------
def doc_title(doc, text, space_before=6):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(space_before)
    p.paragraph_format.space_after = Pt(14)
    set_run_font(p.add_run(text), TITLE_PT, bold=True, color=DARK)
    return p


def subtitle(doc, text):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(18)
    set_run_font(p.add_run(text), 10, color=GRAY)
    return p


def h1(doc, text, space_before=18):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(space_before)
    p.paragraph_format.space_after = Pt(8)
    p.paragraph_format.keep_with_next = True
    set_run_font(p.add_run(text), H1_PT, bold=True, color=DARK)
    return p


def h2(doc, text, space_before=12):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(space_before)
    p.paragraph_format.space_after = Pt(5)
    p.paragraph_format.keep_with_next = True
    set_run_font(p.add_run(text), H2_PT, bold=True, color=DARK)
    return p


# ---------- 正文 ----------
def _write_segments(p, segments, base_size=BODY_PT, base_color=None):
    if isinstance(segments, str):
        segments = [(segments, {})]
    for text, style in segments:
        r = p.add_run(text)
        set_run_font(
            r,
            style.get("size", base_size),
            bold=style.get("bold"),
            color=style.get("color", base_color),
            cn="Consolas" if style.get("mono") else FONT_CN,
        )
        if style.get("mono"):
            r.font.name = "Consolas"


def para(doc, segments, indent=True, space_after=6):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(space_after)
    if not indent:
        p.paragraph_format.first_line_indent = Pt(0)
    _write_segments(p, segments)
    return p


def bullet(doc, segments, level=0):
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Cm(0.75 + 0.6 * level)
    p.paragraph_format.space_after = Pt(3)
    p.paragraph_format.line_spacing = 1.5
    set_run_font(p.add_run("· "), BODY_PT, bold=True, color=ACCENT)
    _write_segments(p, segments)
    return p


def numbered(doc, idx, segments):
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Cm(0.9)
    p.paragraph_format.first_line_indent = Cm(-0.9)
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.line_spacing = 1.5
    set_run_font(p.add_run(f"{idx}. "), BODY_PT, bold=True, color=ACCENT)
    _write_segments(p, segments)
    return p


def _shade(cell, hex_fill):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_fill)
    tcPr.append(shd)


def note(doc, segments, fill="F5F7F8"):
    """灰底提示块。用单格表格模拟，比边框段落稳。"""
    t = doc.add_table(rows=1, cols=1)
    t.alignment = WD_TABLE_ALIGNMENT.LEFT
    cell = t.cell(0, 0)
    _shade(cell, fill)
    p = cell.paragraphs[0]
    p.paragraph_format.space_before = Pt(3)
    p.paragraph_format.space_after = Pt(3)
    p.paragraph_format.line_spacing = 1.45
    _write_segments(p, segments, base_size=10, base_color=GRAY)
    spacer(doc, 6)


def spacer(doc, pt=6):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(0)
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.line_spacing = 1
    set_run_font(p.add_run(""), pt)
    return p


def divider(doc):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(2)
    pBdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), "6")
    bottom.set(qn("w:color"), "D8DEE3")
    pBdr.append(bottom)
    p._p.get_or_add_pPr().append(pBdr)
    spacer(doc, 4)


def table(doc, headers, rows, widths=None):
    t = doc.add_table(rows=1, cols=len(headers))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.LEFT
    for i, head in enumerate(headers):
        cell = t.rows[0].cells[i]
        _shade(cell, "EDF2F1")
        p = cell.paragraphs[0]
        p.paragraph_format.space_before = Pt(2)
        p.paragraph_format.space_after = Pt(2)
        set_run_font(p.add_run(head), 9.5, bold=True)
    for row in rows:
        cells = t.add_row().cells
        for i, val in enumerate(row):
            p = cells[i].paragraphs[0]
            p.paragraph_format.space_before = Pt(2)
            p.paragraph_format.space_after = Pt(2)
            p.paragraph_format.line_spacing = 1.35
            set_run_font(p.add_run(str(val)), 9.5)
    if widths:
        for row in t.rows:
            for i, w in enumerate(widths):
                row.cells[i].width = Cm(w)
    spacer(doc, 10)
    return t


def faq_list(doc, pairs):
    """Q/A 列表。pairs = [(问题, 回答), ...]"""
    for i, (q, a) in enumerate(pairs, 1):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(8)
        p.paragraph_format.space_after = Pt(2)
        p.paragraph_format.keep_with_next = True
        set_run_font(p.add_run(f"Q{i}　{q}"), 11, bold=True, color=DARK)
        p2 = doc.add_paragraph()
        p2.paragraph_format.left_indent = Cm(0.55)
        p2.paragraph_format.space_after = Pt(4)
        p2.paragraph_format.line_spacing = 1.5
        set_run_font(p2.add_run(a), 10.5, color=RGBColor(0x3A, 0x40, 0x46))


# ---------- 图片 ----------
def _place_pic(doc, path, width_cm, max_h_cm, caption):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after = Pt(3)
    p.paragraph_format.keep_with_next = True
    with Image.open(path) as im:
        w, h = im.size
    ratio = h / w
    # 统一转成 EMU 整数再比较，避免 Cm 对象与 float 混算时单位歧义
    width_emu = int(Cm(width_cm))
    if width_emu * ratio > int(Cm(max_h_cm)):
        width_emu = int(int(Cm(max_h_cm)) / ratio)
    p.add_run().add_picture(str(path), width=Emu(width_emu))
    if caption:
        c = doc.add_paragraph()
        c.alignment = WD_ALIGN_PARAGRAPH.CENTER
        c.paragraph_format.space_before = Pt(1)
        c.paragraph_format.space_after = Pt(10)
        set_run_font(c.add_run(caption), 9, color=RGBColor(0x8A, 0x91, 0x99))


def add_figure(doc, filename, caption=None, max_h_cm=20.0):
    """插入逻辑示意图（diagram_kit 产出的 PNG）。满版宽贴出，保证图中文字可读。"""
    stem = filename.rsplit(".", 1)[0]
    path = FIGS / (stem + ".png")
    if not path.exists():
        print(f"  [缺示意图] {filename}")
        return
    _place_pic(doc, path, CONTENT_W, max_h_cm, caption)


def add_image(doc, filename, caption=None):
    """贴图。宽高比 > 1.5 的整页长图自动纵向切 2–3 段，避免缩小后看不清。"""
    stem = filename.rsplit(".", 1)[0]
    path = SHOTS / (stem + ".jpg")
    if not path.exists():
        path = SHOTS / filename
    if not path.exists():
        print(f"  [缺图] {filename}")
        return

    with Image.open(path) as im:
        w, h = im.size
    ratio = h / w

    if ratio <= 1.5:
        _place_pic(doc, path, CONTENT_W, MAX_IMG_H, caption)
        return

    parts = 2 if ratio <= 3.2 else 3
    labels = ["上半", "下半"] if parts == 2 else ["上", "中", "下"]
    SPLIT_DIR.mkdir(parents=True, exist_ok=True)
    seg_h = h // parts
    for i in range(parts):
        top = i * seg_h
        bottom = h if i == parts - 1 else (i + 1) * seg_h
        out = SPLIT_DIR / f"{stem}_p{i}.jpg"
        Image.open(path).convert("RGB").crop((0, top, w, bottom)).save(
            out, "JPEG", quality=88, optimize=True
        )
        cap = caption
        if caption and i > 0:
            cap = f"{caption}（{labels[i]}）"
        _place_pic(doc, out, CONTENT_W, MAX_IMG_H, cap)
