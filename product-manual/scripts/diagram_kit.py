# -*- coding: utf-8 -*-
"""逻辑示意图绘制库（matplotlib）。

手册的文字讲"是什么"，逻辑图讲"怎么串起来"。截图不能替代图：
截图告诉读者按钮长什么样，图告诉读者自己在整个流程的哪一格。

四类图覆盖绝大多数需要：
- 流程条  一条主干上读者的行走路径
- 状态机  一个实体有几种状态、怎么合法流转
- 结构图  实体之间的包含 / 拆分关系
- 决策图  一个操作有几种分支、各分支后果

用法：
    from diagram_kit import *
    cv = Canvas(h_cm=8.0)
    cv.box(2, 10, 20, 8, "草稿")
    cv.arrow((23, 14), (30, 14))
    cv.save("fig-A.png")

坐标：横向 0–100 固定，纵向上限由 h_cm 决定（ymax = 100 * h_cm / w_cm），
且 y 轴已翻转（从上往下递增），与阅读顺序一致。

排版铁律（血的教训）：
1. 先规划纵向分带，每带留够空隙，再往里放东西。边画边凑必然重叠。
2. 箭头标签不要压在方框或连线上——文字的 bbox 会盖住线，看起来像断了。
3. 分支线别穿过其他方框，宁可绕远路。
4. 每个注释用独立 y 值，不要依附在某个元素上算。
"""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

# ---------- 中文字体：跨平台探测 ----------
import pathlib

FONT_CANDIDATES = [
    r"C:\Windows\Fonts\msyh.ttc",                                          # 微软雅黑
    r"C:\Windows\Fonts\msyhbd.ttc",
    "/System/Library/Fonts/PingFang.ttc",                                  # macOS
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",              # Linux
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
]
FONT_PATH = next((p for p in FONT_CANDIDATES if pathlib.Path(p).exists()), None)


def fp(size, bold=False):
    """返回指定字号的字体属性。找不到中文字体时退回默认（会显示方块，需装字体）。"""
    if FONT_PATH:
        f = font_manager.FontProperties(fname=FONT_PATH, size=size)
        if bold:
            f.set_weight("bold")
        return f
    return font_manager.FontProperties(size=size, weight="bold" if bold else "normal")


# ---------- 配色（howashine 品牌色板，见仓库 docs/brand-color.md） ----------
# 规范硬约束 R1：有色相 token 的 oklch H 必须落在 [0°,96°] ∪ [330°,360°)。
# 也就是**禁止蓝绿色相**——台湾市场语境下蓝绿会被读成政治符号。
# 所以"成功/主流程"用品牌橙，不用传统的绿色；"平台侧"用暖砖色，不用蓝色。
ACCENT = "#C9510F"        # 主流程 / 成功（品牌橙压深一档，白底对比度达 AA）
ACCENT_BG = "#FBEADF"
GRAY_D = "#382218"        # 正文（品牌深文字褐）
GRAY = "#6B5A50"          # 次要说明
GRAY_BG = "#F5F0E8"
AMBER = "#8A6116"         # 待处理 / 补件（held 深琥珀）
AMBER_BG = "#FBF0DC"
GOLD = "#B8860B"          # 点缀金（仅装饰，不承载文字）
BLUE = "#9A4A28"          # 平台侧 / 资金（暖砖色，命名沿用便于替换）
BLUE_BG = "#F7E8E1"
RED = "#8F2D1B"           # 终止 / 拒绝（绛红）
RED_BG = "#F9E6E2"
LINE = "#B8A99C"          # 箭头与边框

# 无歧义别名：与 docx_kit 同时使用时用这组（docx_kit 里有同名 RGBColor 常量）
DK_ACCENT, DK_ACCENT_BG = ACCENT, ACCENT_BG
DK_GRAY_D, DK_GRAY, DK_GRAY_BG = GRAY_D, GRAY, GRAY_BG
DK_AMBER, DK_AMBER_BG = AMBER, AMBER_BG
DK_GOLD = GOLD
DK_BLUE, DK_BLUE_BG = BLUE, BLUE_BG
DK_RED, DK_RED_BG = RED, RED_BG
DK_LINE = LINE


class Canvas:
    """一块画布。横向坐标固定 0–100。"""

    def __init__(self, w_cm=15.5, h_cm=8.0, dpi=300):
        self.w_in, self.h_in = w_cm / 2.54, h_cm / 2.54
        self.fig = plt.figure(figsize=(self.w_in, self.h_in), dpi=dpi)
        self.ax = self.fig.add_axes([0, 0, 1, 1])
        self.xmax = 100.0
        self.ymax = 100.0 * (h_cm / w_cm)
        self.ax.set_xlim(0, self.xmax)
        self.ax.set_ylim(0, self.ymax)
        self.ax.axis("off")
        self.ax.invert_yaxis()          # y 从上往下递增，符合阅读顺序

    # ---- 基元 ----
    def box(self, x, y, w, h, text, fc=ACCENT_BG, ec=ACCENT, tc=GRAY_D,
            fs=10, bold=True, r=1.0, lw=1.3, zorder=3):
        self.ax.add_patch(FancyBboxPatch(
            (x, y), w, h,
            boxstyle=f"round,pad=0,rounding_size={r}",
            facecolor=fc, edgecolor=ec, linewidth=lw, zorder=zorder))
        self.ax.text(x + w / 2, y + h / 2, text, ha="center", va="center",
                     fontproperties=fp(fs, bold), color=tc, zorder=zorder + 1,
                     linespacing=1.5)

    def sub(self, x, y, text, fs=8.5, color=GRAY, ha="center", va="center", bold=False):
        """纯文字注释。每处注释都给独立 y，不要依附在元素上计算。"""
        self.ax.text(x, y, text, ha=ha, va=va, fontproperties=fp(fs, bold),
                     color=color, linespacing=1.5)

    def container(self, x, y, w, h, label=None, fc="none", ec=LINE, lw=1.0,
                  ls=(0, (4, 3)), label_fs=8.5, label_color=GRAY):
        """虚线容器。label 放在左上内角，不压边框也不压内容。"""
        self.ax.add_patch(FancyBboxPatch(
            (x, y), w, h, boxstyle="round,pad=0,rounding_size=1.4",
            facecolor=fc, edgecolor=ec, linewidth=lw, linestyle=ls, zorder=1))
        if label:
            self.ax.text(x + 2.2, y + 1.6, label, ha="left", va="top",
                         fontproperties=fp(label_fs, True), color=label_color,
                         zorder=4)

    def arrow(self, p1, p2, label=None, color=LINE, lw=1.4, style="-|>",
              rad=0.0, fs=8, label_offset=(0, 0), label_color=None, zorder=2):
        self.ax.add_patch(FancyArrowPatch(
            p1, p2, arrowstyle=style, mutation_scale=12,
            color=color, linewidth=lw,
            connectionstyle=f"arc3,rad={rad}",
            shrinkA=1, shrinkB=1, zorder=zorder))
        if label:
            mx = (p1[0] + p2[0]) / 2 + label_offset[0]
            my = (p1[1] + p2[1]) / 2 + label_offset[1]
            # 白底压住箭头，避免文字与线糊在一起
            self.ax.text(mx, my, label, ha="center", va="center",
                         fontproperties=fp(fs), color=label_color or color,
                         zorder=zorder + 1, linespacing=1.4,
                         bbox=dict(boxstyle="round,pad=0.28", fc="white",
                                   ec="none", alpha=0.92))

    def save(self, path):
        self.fig.savefig(path, dpi=self.fig.dpi, facecolor="white",
                         bbox_inches=None, pad_inches=0)
        plt.close(self.fig)
        return path


# ---------- 复合图元 ----------
def center(box_x, box_y, box_w, box_h):
    return (box_x + box_w / 2, box_y + box_h / 2)


def flow_row(cv, items, y, h, x0=2, x1=98, gap=3.2, **box_kw):
    """等宽横向流程条。items = [(标题, 副标题或 None), ...]，副标题自动落在框下。"""
    n = len(items)
    w = (x1 - x0 - gap * (n - 1)) / n
    boxes = []
    for i, item in enumerate(items):
        title, detail = item if isinstance(item, tuple) else (item, None)
        x = x0 + i * (w + gap)
        cv.box(x, y, w, h, title, **box_kw)
        if detail:
            cv.sub(x + w / 2, y + h + 2.0, detail, fs=8, color=GRAY)
        boxes.append((x, y, w, h))
        if i < n - 1:
            cv.arrow((x + w + 0.5, y + h / 2), (x + w + gap - 0.5, y + h / 2))
    return boxes


def ladder(cv, rows, y0, row_h=8.2, x_label=4, x_left=16, x_right=51,
           w_left=26, w_right=34, h=6, left_color=ACCENT, right_color=AMBER):
    """左右对照的分工梯。rows = [(名称, 左侧文本, 右侧文本), ...]

    用于表达"同一件事两方各做一半"，比表格更直观地看出接力关系。
    """
    y = y0
    for name, left, right in rows:
        cv.sub(x_label, y + h / 2, name, fs=9.5, color=GRAY_D, bold=True, ha="left")
        cv.box(x_left, y, w_left, h, left, fc="white", ec=left_color, fs=8.6, bold=False, r=0.7)
        cv.arrow((x_left + w_left + 1, y + h / 2), (x_right - 0.5, y + h / 2), color=LINE)
        cv.box(x_right, y, w_right, h, right, fc="white", ec=right_color, fs=8.6, bold=False, r=0.7)
        y += row_h
    return y
