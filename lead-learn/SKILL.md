---
name: lead-learn
description: 把 B站/抖音收藏夹里的内容批量转化成各角色的长期内容。增量抓取收藏 → 下载 → 字幕/转录/抽帧 → 按语义判给对应角色 → 派单给子智能体消化。当用户要「学我的收藏」「让 AI 学习收藏的视频」「收藏夹自动学习」「把视频喂给智能体」「批量消化收藏内容」「分流这些材料」时使用。支持 CookieCloud 同步登录态、增量检测、语义分流（不用关键词打分）。派单落在工作区，不绑定任何记忆系统；有 recall 时额外能核盘面、在 LONGTERM.md 留指路。
---

# lead-learn

收藏夹 → 各角色长期内容的完整链路。

**不依赖 recall。** 有 recall 时多两件事（核盘面时看各 agent 的 `longterm/`、在它们的 `LONGTERM.md` 留一行指路）；没有就跳过这两件，其余全一样。**派单文件始终落在工作区。**

**不写「手账」概念。** recall 只有两层：`dailynote`（日记）和 `longterm`（长期内容）。本 skill 的产物最终落在 longterm。

## 一句话

抓收藏 → 取文字/画面 → **判给谁** → 角色自己消化成长期内容。

## 配置（不用环境变量也行）

**skill 里没有任何绝对路径。** 三级解析，从「跟着谁搬家」倒推：

| 优先级 | 位置 | 跟着谁搬家 |
|---|---|---|
| 1 | 环境变量 `LEAD_LEARN_HOME` / `BILI_UID` / `LEAD_LEARN_AGENT` | 单次会话 |
| 2 | `~/.lead-learn/config.json` | **用户账户**（换盘只改一处） |
| 3 | `<当前目录>/lead-learn-data` | 在哪跑就在哪建 |

推荐写配置文件，一次配好长期有效：

```json
// ~/.lead-learn/config.json
{
  "home": "<你的工作区绝对路径>",
  "bili_uid": "<你的B站UID>",
  "midnight_base_dir": ""
}
```

`bili_uid` **必填**——skill 不再内置任何人的 UID。没配时抓取会明确报错并告诉你怎么办，不会静默抓到别人的收藏夹。

### 派单落哪：只在工作区

```
LEAD_LEARN_DISPATCH         显式指定，任何目录（最高优先）
<HOME>/dispatch             默认，且这是唯一的默认
```

**派单不进 recall 记忆区。** 判据：这轮的待办 → 工作区；下次还要用的判断 → 记忆区。
详见 `docs/adr/0003`。

`LEAD_LEARN_AGENT` 仍然有用，但它只决定两件事：核盘面时看谁的 `longterm/`、
在谁的 `LONGTERM.md` 里留一行指路。**它不再决定派单文件落在哪。**

`paths.py` 统一解析，所有脚本共用。

## 依赖（都可缺，缺了报错会指明缺什么）

| 用途 | skill / 工具 |
|---|---|
| 下载视频 | `media-downloader`（B站走 yt-dlp） |
| 转录 | `asr-subtitle`（必剪 bcut） |
| 抽帧 | `dsh-video-storyboard` |
| 长期内容 | `recall`（可选） |
| 抖音下载 | 自带 `scripts/douyin_dl.py`（Playwright） |

**不用 bili-humanism 插件。** 它的能力已被上面覆盖，且每天只能写 2 篇手账，批量学习不够用。

## 七步链路

### 1. 刷凭据

```powershell
python scripts/cc_fetch.py show              # CookieCloud 里有什么
python scripts/cc_fetch.py export bilibili
python scripts/cc_fetch.py export douyin
```

配置见 [references/cookiecloud.md](references/cookiecloud.md)。首次要填凭据；配好之后每次自动同步登录态。

### 2. 抓收藏

```powershell
python scripts/bili_grab3.py 40
python scripts/favorites.py grab douyin
```

**B站用 `bili_grab3.py`，不要用 `favorites.py grab bilibili`** —— 后者的 `resource/list` 会吃 HTTP 412 风控。

### 3. 处理新增

```powershell
python scripts/pipeline.py check            # 有多少新增（增量，跳过已处理的）
python scripts/pipeline.py run --limit 5
```

分派规则：

```
有中文字幕 → yt-dlp 下字幕（2 秒，最准）
无字幕     → asr-subtitle 转录（20 秒）
转录失败   → storyboard 抽帧（>600s 跳过）
纯配乐     → 记 no_speech，不算失败
```

产物落到 `$LEAD_LEARN_HOME/.favorites-out/longterm-staging/*.staged.md`。

### 4. 看花名册

```powershell
python scripts/dispatch.py roster           # 谁管什么（从 self.md 的 position 读）
python scripts/dispatch.py list 80          # 待分流的稿子（标题 + 前 80 字，够判归属）
```

`roster` 有个坑它会自己标出来：`agent.json` 里 `description` 等于自己名字的都是**占位空壳**，真定位在 `self.md` 的 `position`。

### 5. 判给谁 —— 这一步是人（或模型）的活

**分流是判断，不是计数。** 写一个 `plan.json`：

```json
{
  "round": "2026-11-24 第一轮",
  "items": [
    {
      "key": "bili:BV1LxGv6xEYo",
      "title": "一图看我20年的运营功力",
      "url": "https://www.bilibili.com/video/BV1LxGv6xEYo",
      "to": [
        { "agent": "liangliang", "reason": "用户画像三层、内容矩阵四阶段——注意力为什么被拿走" },
        { "agent": "shangshang", "reason": "RFM 分层、生命周期、投产比账——卖的那一摊" },
        { "agent": "贸贸",     "reason": "机制设计四步、二次传播三种理由——谈成一单的外围" }
      ]
    }
  ],
  "dropped":   [ { "title": "...", "why": "纯歌词，无方法" } ],
  "undecided": [ { "key": "...", "title": "...", "why": "8 万字长剧情，成本高，待你点头" } ]
}
```

完整样例见 [references/plan-example.json](references/plan-example.json)（18 条真实派单）。

**判法（详见 [references/routing.md](references/routing.md)）**：

| 问题 | 判法 |
|---|---|
| 先看什么 | 先看标题，再看简介前 300 字。**只在判不出归属时才读正文** |
| 一条能归几人 | 判据是「**是不是他的活**」，不是「像不像他的领域」。三个是他的活就派三个人，不挑最像的 |
| 判不出怎么办 | 丢掉。塞给「最接近」的人会污染它的标签共现网，比不派更糟 |
| 能不能写脚本打分 | **不能。** 三处实测硬伤：词表漏人 / max() 只留一个赢家 / 字面计数看不懂语义 |

### 6. 落单

```powershell
python scripts/dispatch.py apply plan.json                 # 预览（默认不写）
python scripts/dispatch.py apply plan.json --confirm       # 实际写入
python scripts/dispatch.py apply plan.json --confirm --mark-index   # 同时在各角色 LONGTERM.md 登记
```

产出（一个角色一份，学完由角色自己划掉条目；全清才删文件）：

```
<DISPATCH>/
├── 量量_staging.md     ← 3 条，每条带链接 + 派给它的理由 + 还派给了谁
├── 商商_staging.md
├── _ledger.md          ← 台账，不删；最后汇总的骨架
└── ...
```

**派单文件里未划掉的条目数 = 还没学的活。** `dispatch.py status` 一眼看进度。

**`apply` 是追加不是覆盖。** 第二个轮次派单时，上一轮没学完的条目会原样留着，新条目附在后面（带 `<!-- 以下为 … 新派 -->` 分隔）。早期版本整份覆盖，会把上一轮的派单**静默抹掉**——agent 根本不知道那些活存在过。

**同一个 agent 只认目录名。** `plan.json` 里写 `liangliang` 或 `量量` 都行，脚本会归一到目录名再落盘。早期版本按 plan 里的原文分文件，于是 `liangliang` 和 `量量` 写成同一个 `量量_staging.md`，**后写的整份覆盖先写的**，plan 里 2 条只落 1 条、还不报错。

### 7. 派子智能体

对每个有派单的角色开新上下文，提示词**逐字用** `assets/学习任务模板.md`，只填 `<AGENT>` 和 `N`：

```
/recall <AGENT>

staging 里有 N 篇从收藏抓来的稿子，按你自己的规矩消化：
...
```

**不改写、不缩写。** 上一版自己编了八步长模板，子智能体跑不完，零产物。

**没有 recall 的角色**：把 `/recall <AGENT>` 那行换成它的 `self.md` 路径，其余照旧。

## 核活：不听回报，看盘面

```powershell
python scripts/dispatch.py status                        # 剩几家没交、各剩几条
python scripts/dispatch.py verify --since 2026-11-24     # 各角色实际变了什么（增量）
```

三个判据：

1. `dispatch/` 里还有几条**未划掉的条目** —— `status` 数的是条目不是文件头
2. 各角色的 `longterm/` 该日之后**新增/修改**了几个文件、`LONGTERM.md` 是否多了索引行（**索引没写等于没建**）
3. 各角色的 `dailynote/` 是否多了今天的日记

回报说「收了 3 篇」但盘面没变，以盘面为准。

**⚠ `verify` 的 longterm 列必须是增量，不是总数。** 早期版本数的是 `longterm` 下全部文件，于是开编（29 个文件）、商商（22 个）这类基数大的角色，涨没涨根本看不出来；反过来基数 1 的角色写了一个文件也显示 "1"，跟没干活一样。现在按 `--since` 的 mtime 过滤。

## 汇总

`_ledger.md` 是骨架。收回各家回话后压成一份给人看的资料：

```
这次学了什么 / 收了哪几篇归到哪 / 丢了哪些为什么 / 有没有跟已有认识冲突
```

## 维护

```powershell
python scripts/pipeline.py status         # 流水线统计
python scripts/pipeline.py retry [key]    # 重试失败条目
python scripts/pipeline.py clean          # 删 mp4 只留文本
python scripts/dispatch.py reset [key]    # 派错了想重派：把源稿状态清回去
python scripts/health.py                  # 全链路体检
```

## 已知坑

见 [references/pitfalls.md](references/pitfalls.md)。32 条实测踩出来的，按平台分：B站 9 / 抖音 10 / 处理 7 / 服务器 6。

## 数据布局

```
$LEAD_LEARN_HOME/
├── .favorites-out/
│   ├── cookiecloud.json           CookieCloud 凭据
│   ├── *-cookies.{txt,json}       cookie（yt-dlp 与 Playwright 两种格式）
│   ├── bilibili-latest40.json     收藏列表
│   ├── douyin-favorites.json
│   ├── pipeline-state.json        已处理条目（增量依据）
│   └── longterm-staging/          待分流的稿件（.staged.md）
└── media-downloads/               视频与文本产物（mp4 用完即删）
```
