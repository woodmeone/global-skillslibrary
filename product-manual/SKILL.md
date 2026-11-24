---
name: product-manual
description: 为 Web 产品生成带真实截图和逻辑示意图的多角色操作手册（DOCX + PDF）。当用户要求"写操作手册/使用手册/操作指引/用户指南"，或提供参考模板要求照着做，或说"给某个网站/系统写文档"、"手册要配截图/配图"、"按角色分开写"、"补逻辑图/流程图"时使用。适用于中后台系统、SaaS、电商平台等多角色产品；涵盖代码盘点、本地起站、Playwright 批量截图、逻辑图绘制、DOCX 排版、转 PDF 全流程。
---

# 产品操作手册生成

## 核心原则

**截图必须来自真实运行的产品，章节必须来自代码盘点，逻辑图必须自己画。** 三者都不能编。

三者分工不要混：

- **截图**说"按钮长什么样、在哪"
- **逻辑图**说"你在整个流程的哪一格、状态怎么流转"
- **文字**说"填错了会怎样、做错了多久能发现"

一份手册的价值不在"按钮在哪"，在"填错了会怎样"。写每一节都问：读者会不会在这里卡住？

## 工作流

### 阶段 0：先摸清角色，再定文档数

角色数 = 文档数。用 [references/role-discovery.md](references/role-discovery.md) 的方法从代码里盘：

1. 抓所有 `page.tsx` 路由
2. 读导航组件里的 role 标记
3. 从 `lib/domain/` 抓状态机常量
4. 用 `requireAdmin` / `requireContext` 确认权限边界

输出一张盘点表（角色 / 入口 / 流程 / 状态机 / 不可逆操作）。**填不出来的格子先回代码补，别急着写。**

盘点表里"状态机"和"流程"两列，就是后面要画图的地方——**先记下来，别等写完文字才想图**。

### 阶段 1：确认三件事

动手前必须问清，一次问完：

1. **截图从哪来** — 线上站点能访问就用线上的；不能访问就本地起仓库。两者渲染一致。
2. **读者是谁、什么语言** — 界面语言和正文语言可能不同（如繁中界面对台湾买家）。
3. **有没有参考模板** — 有模板就读它的版式（标题层级、强调色、图注写法、字段表格），照搬。用户说"给你个模板"时，模板的**结构**比内容重要。

### 阶段 2：本地起站

```bash
python scripts/bootstrap.py --dir <repo> --check
python scripts/bootstrap.py --dir <repo> --start --port 3000
```

`--check` 会报告 node_modules、next bin、.env、可用 Chrome、端口占用。

卡住了先看 [references/pitfalls.md](references/pitfalls.md) 的"截图"节。最常见的三个：pnpm shim 失效（改走 `node node_modules/next/dist/bin/next`）、`next build` 因 Google Fonts 失败（直接用 dev）、端口不是 3000 导致登录态异常。

**需要登录态的流程必须先备好账号。** 注册账号、绑定数据、提权到管理员，这些都要在截图前做完。

### 阶段 3：批量截图

写一份 JSON 配置，交给 `scripts/shoot.py`：

```json
{
  "viewport": [1440, 900],
  "accounts": {
    "admin": {"email": "a@x.com", "password": "***", "login": "/sign-in"}
  },
  "anon": [
    {"name": "u01-home", "url": "/", "full": true}
  ],
  "sessions": {
    "admin": [
      {"name": "a01-overview", "url": "/console"},
      {"name": "a02-detail", "follow": "a[href^='/console/orders/']", "from": "/console/orders"}
    ]
  },
  "compress": 1240
}
```

```bash
python scripts/shoot.py --config shots.json --base http://localhost:3000 \
                        --out docs/manual-shots --chrome "<chrome.exe>"
```

脚本已内置：隐藏开发浮标、每个角色独立 context、详情页自动跟随链接、压缩到 1240px JPEG。

**截图前必读 [references/pitfalls.md](references/pitfalls.md)。** Cookie 被丢弃、签名凭证、长图切分这些问题会让你白跑几轮。

命名规范 `角色前缀+序号+页面`（`u01-home` / `m01-overview` / `a01-merchants`），后面写文档时按名取图。

### 阶段 4：画逻辑图

截图只说明"按钮在哪"，说明不了"我在流程的哪一格"。这一步补上图形。

用 `scripts/diagram_kit.py` 画，输出 PNG 到 `docs/manual-figures/`。**必读 [references/diagrams.md](references/diagrams.md)** —— 里面有该画哪五类图、画布分带方法、六种排版事故的修法。

最常用的五张（几乎每个多角色产品都需要）：

| 图 | 内容 | 放哪 |
|---|---|---|
| 角色边界 | 几类使用者、各自看得到什么 | 每份手册开头 |
| 主线流程 | 该角色从进入到完成的路径 | 每份手册开头 |
| 结构拆解 | 一个东西怎么被拆成多个 | 有子单/子任务的产品 |
| 状态机 | 实体有几种状态、怎么流转 | 有审核/审批的产品 |
| 分工对照 | 两方各做什么，用户为什么找不到按钮 | 有审核环节的产品 |

```python
from diagram_kit import *
cv = Canvas(h_cm=9.8)          # 高度先定死，再规划纵向分带
cv.box(2, 12, 18, 8, "草稿", fc=GRAY_BG, ec=GRAY)
cv.arrow((20.8, 16), (27.2, 16))
cv.sub(24, 30, "提交审核", fs=8, color=GRAY)   # 标签单独放，不用 arrow 的 label
cv.save("figures/fig-D-onboarding.png")
```

**三条铁律**（都是重画过才对的）：

1. **先定画布高度，再按带位放元素。** 边画边凑必然重叠。
2. **箭头标签用 `sub()` 单独放**，不要用 `arrow(label=...)` —— 后者容易压在连线或方框上。
3. **示意图贴文档时用满版宽 15.5cm**，不要缩到 12cm，否则图内 8pt 字变成 5pt，等于白画。

### 阶段 5：写文档

用 `scripts/docx_kit.py`。它封装了实测有效的版式：A4 / 微软雅黑 / 1.55 行距 / 绿色强调 / 灰底提示块 / 字段表格 / 长图自动切分。

```python
import sys; sys.path.insert(0, "scripts")
from docx_kit import *

import docx_kit
docx_kit.SHOTS = Path("docs/manual-shots")
docx_kit.FIGS = Path("docs/manual-figures")

doc = new_doc()
page_number_footer(doc)
doc_title(doc, "产品名 · 商户端")
subtitle(doc, "注册 · 开户 · 上架 · 履约 · 回款 · 操作指引")

h1(doc, "零、先看两张图")
add_figure(doc, "fig-A-roles.png", "图 0-1　三类使用者与各自的权限边界")
add_figure(doc, "fig-B-buyer-flow.png", "图 0-2　买家主线")

h1(doc, "一、注册账号")
para(doc, "打开 https://x.com/sign-up 填写信息。")
table(doc, ["字段", "要求", "说明"], [["邮箱", "必填", "登录账号"]], widths=[4.6, 3.4, 7.5])
add_image(doc, "u08-signup.png", "图 1-1　注册页")
note(doc, [("注册不等于能卖货。", {"bold": True}), ("还要完成开户审核。", {})])
faq_list(doc, [("注册完为什么不能上架？", "需先完成开户审核。")])
doc.save("out.docx")
```

`add_figure()` 贴逻辑图（满版宽、不切分），`add_image()` 贴截图（超高自动切 2–3 段）。

章节结构和写法见 [references/manual-structure.md](references/manual-structure.md)。

**一份文档一个脚本。** 三个角色就写三个 `build_*.py`，共用 `docx_kit`。这样改哪份不影响其他份。

**开篇加一节「零、先看两张图」**：给角色全景 + 主线流程，读者先知道自己站在哪，再往下看具体步骤。原来直接进"一、进入商城"，读者不知道后面还有什么。

### 阶段 6：交付

```bash
python scripts/to_pdf.py --dir docs/manuals
```

**先确认 DOCX 内容正确，再转 PDF。** Word COM 可能卡死，PDF 只当最后一步。转之前把图片压到 1240px，否则 20MB 的文档能让 Word 挂十分钟。

出稿前扫一遍敏感词：`localhost`、端口、演示密码、`.local` 域名、`TODO`、`占位`。

交付时 DOCX（可编辑）+ PDF（可直接发）都给。

## 脚本

| 脚本 | 用途 |
|---|---|
| `scripts/bootstrap.py` | 起站体检 / 启动 / 迁移 |
| `scripts/shoot.py` | 按 JSON 配置批量截图 |
| `scripts/diagram_kit.py` | 逻辑示意图绘制（流程条 / 状态机 / 结构 / 分工梯） |
| `scripts/docx_kit.py` | DOCX 排版函数库 |
| `scripts/to_pdf.py` | DOCX → PDF，带超时与残留清理 |

## 参考

| 文件 | 何时读 |
|---|---|
| [references/role-discovery.md](references/role-discovery.md) | 阶段 0，从代码盘角色和流程 |
| [references/diagrams.md](references/diagrams.md) | 阶段 4，决定画什么图、怎么不画歪 |
| [references/pitfalls.md](references/pitfalls.md) | 阶段 2–6，遇到任何卡点先查这里 |
| [references/manual-structure.md](references/manual-structure.md) | 阶段 5，定章节和写法 |

## 交付前自检

内容：

- [ ] 每份文档的每个章节都有对应截图？
- [ ] 字段表格第三列写的是"填错什么后果"，不是同义反复？
- [ ] 权限差异说清了？（"看不到某菜单是正常的"）
- [ ] 管理员手册有不可逆操作清单？
- [ ] 常见问题都是会让人卡住的，答案给了原因+动作？

图形：

- [ ] 每份手册开头有角色边界图 + 主线流程图？
- [ ] 有审核/审批的产品画了状态机？
- [ ] 有子单/子任务的产品画了结构拆解？
- [ ] 每张示意图的两处元素都不重叠？
- [ ] 示意图满版宽 15.5cm，不是缩到 12cm？

交付：

- [ ] 无 `localhost`、演示密码、`TODO` 残留？
- [ ] 长图切成 2–3 段且每段有图注？
- [ ] 图号章内连续、无重号？
- [ ] DOCX 和 PDF 都生成了？
