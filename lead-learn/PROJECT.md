# lead-learn · 项目真相

> 本文件回答「**现在是什么样**」。为什么变成这样，看 `docs/issue-*.md` + `git log`。
> 术语见 `CONTEXT.md`；难逆转的决策见 `docs/adr/`。

## 目标

把 B站/抖音收藏夹里的内容，批量转化成各角色（recall agent）的长期内容。

一句话链路：**抓收藏 → 取文字/画面 → 判给谁 → 各角色自己消化**。

**不替倒角色学习。** 本 skill 的产物止于「派单文件 + 素材稿」，判断「值不值得学」是各 agent 的活。

## 模块地图

| 模块 | 代码区域 | 职责 |
|---|---|---|
| 凭据 | `scripts/cc_fetch.py` `cc_verify.py` `export_cookies.py` | 从 CookieCloud 拉登录态，导出 yt-dlp / Playwright 两种格式 |
| 抓取 | `scripts/bili_grab3.py` `favorites.py` | B站走 `resource/ids`（避 412），抖音走 Playwright 拦 XHR |
| 处理 | `scripts/pipeline.py` | 增量检测 → 下载 → 字幕/ASR/抽帧 → 落 staged 稿 |
| 分流 | `scripts/dispatch.py` | **不做打分**。落派单文件、核盘面、管状态 |
| 路径 | `scripts/paths.py` | **所有路径与环境变量的唯一出处** |
| 体检 | `scripts/health.py` | CookieCloud / 凭据 / 数据新鲜度 / 流水线 |

## 核心流程

```
收藏夹 ──①抓取──▶ bilibili-latest40.json / douyin-favorites.json
                  │
                  ├─②增量：detect_new() 按 key 差集（bili:BVxxx / dy:数字）
                  ▼
              新增条目 ──③按材料类型分流──
                  ├─ 有中文字幕 ──▶ yt-dlp 下字幕（约 2 秒）
                  ├─ 无字幕 ──────▶ ASR 转录（约 20 秒，必剪 bcut）
                  ├─ 转录失败 ────▶ storyboard 抽帧（>600s 跳过）
                  └─ 纯配乐 ──────▶ no_speech（不算失败）
                  ▼
              .favorites-out/longterm-staging/*.staged.md
                  │
                  ├─④人/模型判断归属，写 plan.json（一条可派多人）
                  ▼
              <DISPATCH>/<显示名>_staging.md + _ledger.md
                  │
                  ├─⑤派子智能体（逐字用 assets/学习任务模板.md）
                  ▼
              各 agent 的 longterm/<类目>/
```

## 数据布局

**派单落在工作区，与 recall 记忆区无关。** 这是 2026-11-24 的架构决定，判据见 `docs/adr/0003`。

```
<工作区>/                              ← ~/.lead-learn/config.json 的 home
├── .favorites-out/
│   ├── cookiecloud.json             # 凭据（.gitignore，不入库）
│   ├── *-cookies.{txt,json}         # 同上
│   ├── bilibili-latest40.json       # 收藏列表（FAV_LIMIT 条）
│   ├── douyin-favorites.json
│   ├── pipeline-state.json          # 已处理条目（增量依据）
│   ├── longterm-staging/*.staged.md # **素材真源，一份都不许删**
│   └── logs/                        # 夜间任务日志
├── media-downloads/                 # mp4/m4a 中间产物 + txt/png 产物
└── dispatch/                        # **派单队列 + 台账**（过程状态，学完即清）
```

### recall 记忆区（可选增强，不是依赖）

```
~/.midnight/recall/<agent>/longterm/
├── criteria/    判据   ← 留（下次还要用的判断）
├── roster/      花名册 ← 留
├── roundup/     汇总   ← 留
└── dispatch/    ✗ 不放这里（已迁到工作区）
```

**分界线**：「这轮的待办」进工作区，「下次还要用的判断」进记忆区。
没有 recall 时整条链路照跑，只是少两件事（核盘面、在 LONGTERM.md 留指路）。

## 必须遵守的约束

1. **`staging` 有两个意思**，写提示词时必须区分：
   - `.favorites-out/longterm-staging/` = **素材真源**，mp4 清掉后是唯一兜底，一份都不许删
   - `<DISPATCH>/<agent>_staging.md` = **派单队列**，学完划条目，全清才删文件
2. **分流不写脚本打分。** 三次实测硬伤：词表漏人 / max() 只留一个赢家 / 字面计数看不懂语义。
3. **写盘操作默认 dry-run**，`--confirm` 才真写。脚本能改别人记忆区，第一版必须先预览。
4. **`paths.py` 是路径唯一出处。** 任何脚本不许再硬编码 YTDLP / FFMPEG / SKILL 路径——曾因此让 4 个环境变量全部失效。
5. **子智能体只动自己的记忆区**，不许碰别的 agent 目录。
6. **测试不许碰真实盘**：fixture 必须先 `assert DISPATCH == tmpdir` 再干活。

## 状态机（源稿 status）

| 值 | 含义 | `dispatch.py list` 是否返回 |
|---|---|---|
| `staged_needs_review` | 待判归属 | ✅ 返回 |
| `staged_brief_needs_review` | 同上，正文很短（<300 字） | ✅ 返回 |
| `dispatched:<agents>` | 已派单 | ❌ 跳过 |
| `dropped` | 判定无价值，丢弃 | ❌ 跳过 |
| `undecided` | 有价值但成本高，等人工点头 | ❌ 跳过 |

**这五个值必须只有一套写法。** 早期 `apply` 写 `dispatched:` 而 `_items()` 只跳过 `routed:`，一条都没跳过，导致每晚重复派单。

## 当前功能

- 增量抓取（B站 / 抖音，窗口 `FAV_LIMIT` 默认 100）
- 字幕优先 / ASR 兜底 / 抽帧兜底 / no_speech 标记
- 按语义分流到 13 个 agent（**判断在人，脚本只做机械活**）
- 派单状态机 + 盘面核查（`status` / `verify`）
- `clean` 清媒体（含孤儿），`retry` 重试，`reset` 撤错重派
- 13 个回归测试（`tests/`）

## 演进方向

- 定时任务（见 `docs/adr/0002`）
- `outcome.json`：让子智能体交活时写结构化结果，台账自动回填
- `plan.json` 的 schema 校验（现在只校验 key / agent / reason 非空）

## 外部真源（不搬进来）

- YG 自媒体知识库（外部真源，路径由用户环境决定，本 skill 不引用）
- 原工作区素材：由 `~/.lead-learn/config.json` 的 `home` 指向（外部真源，本 skill 被它调用）。**本文件不写具体路径**——那是用户账户的数据，不是 skill 的。
