# CONTEXT · 术语表

> 纯词汇表。只放术语和区分，不放实现细节（那是 `PROJECT.md`）、不放决策理由（那是 `docs/adr/`）。

## staging（**两个意思，最容易踩**）

| 写法 | 指什么 | 能不能删 |
|---|---|---|
| `.favorites-out/longterm-staging/` | **抓取侧素材真源**。mp4 清掉后是唯一兜底，链接失效就靠它 | **一份都不许删** |
| `<DISPATCH>/<agent>_staging.md` | **派单队列**，待办清单 | 学完划掉条目；全清才删整份 |

写子智能体提示词时，凡是涉及「删 staging」都必须指明是后一个。

## 源稿状态（`status:` frontmatter）

- **staged_needs_review** —— 待判归属
- **staged_brief_needs_review** —— 待判归属，但正文很短（<300 字）
- **dispatched:\<agents\>** —— 已派单，如 `dispatched:liangliang|shangshang`
- **dropped** —— 判定无价值，丢弃
- **undecided** —— 有价值但成本高，等人工点头

前两个会被 `dispatch.py list` 返回，后三个跳过。

## route（处理路径）

- **subtitle** —— 有中文字幕轨，yt-dlp 直接下（约 2 秒，最准）
- **asr** —— 无字幕，走必剪 bcut 转录（约 20 秒）
- **storyboard** —— 转录失败，抽宫格帧（画面可判内容时用）
- **no_speech** —— ASR 确认无人声（纯配乐），不算失败

## agent 标识

| 概念 | 例子 | 用在哪 |
|---|---|---|
| **目录名** | `liangliang` | 记忆区路径、`by_agent` 键、`--identity` |
| **显示名** | `量量` | 派单文件名、给人看的输出 |

**两者混用会撞车**：`liangliang` 和 `量量` 曾写成同一个 `量量_staging.md`，后写覆盖先写。`dispatch.py` 用 `_canonical()` 一律归一到目录名。

## 其他

- **staged 稿** —— `.favorites-out/longterm-staging/*.staged.md`，带 frontmatter 的转录正文
- **派单** —— 把一条材料判给某个 agent，落成 `<agent>_staging.md` 里的一个条目
- **台账** —— `_ledger.md`，记「标题 + 链接 + 派给谁 + 状态」，不删
- **盘面核查** —— 不听子智能体回报，直接看它 `longterm/` 有没有多文件、`LONGTERM.md` 有没有多索引行
- **孤儿媒体** —— 已处理但没有文本产物的 mp4/m4a（storyboard / no_speech / fail 这几类）
- **FAV_LIMIT** —— 每平台每次抓多少条收藏，唯一出处 `paths.py`，默认 100
