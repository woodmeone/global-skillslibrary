# 全局技能库 · 清单

> **这份文档的作用**：在新环境里，只看这一页就知道这个库有什么、缺什么、怎么补齐。
>
> 本仓库**只收录不隶属任何独立仓库的技能**。下面「外部仓库」那一节的 4 个技能各有自己的
> git 远端，本库不收录它们的文件，只登记来源——这样它们各自的历史不会被外层库切碎。

---

## 一、本库直接收录（21 个）

clone 本仓即得，无需额外操作。

### AI / 浏览器 / 抓取

| 技能 | 路径 | 干什么 |
|---|---|---|
| `agent-browser` | `community-skills/agent-browser` | 浏览器自动化 CLI：导航、填表、点击、截图、抓数据、测 Web 应用 |
| `browser` | `community-skills/browser` | 自然语言驱动的浏览器操作 |
| `dev-browser` | `community-skills/dev-browser` | 带持久页面状态的浏览器自动化 |
| `screenshot` | `community-skills/screenshot` | 桌面/系统截图（全屏、指定窗口、局部区域） |
| `github-finder` | `community-skills/github-finder` | 按技术栈在 GitHub 搜可复用开源项目 |
| `skill-lookup` | `community-skills/skill-lookup` | 查找/安装 Agent Skills |
| `skill-creator` | `community-skills/skill-creator` | 创建或更新 skill |
| `skill-vetter` | `community-skills/skill-vetter` | 安装第三方 skill 前的安全审查 |

### 商业 / 电商 / 广告

| 技能 | 路径 | 干什么 |
|---|---|---|
| `amazon-product-scraper` | `community-skills/amazon-product-scraper` | 亚马逊竞品抓取：标题、价格、排名、五点描述、规格 |
| `linkfox-junglescout-keyword-by-keyword` | `community-skills/linkfox-junglescout-keyword-by-keyword` | Jungle Scout 关键词拓展（10 个亚马逊站点） |
| `meta-ads` | `community-skills/meta-ads` | Meta/FB 广告：campaign / adset / 素材 / 受众 / 预算 |

### 内容生产

| 技能 | 路径 | 干什么 |
|---|---|---|
| `keynote-ppt-generator-v4` | `community-skills/keynote-ppt-generator-v4` | Markdown → 乔布斯风 HTML 演示（ECharts + 动画） |
| `powerful-ppt-html-v6` | `community-skills/powerful-ppt-html-v6` | 18 视觉风格 / 27 CSS 动画 / 31 布局模板，可导出 PPTX |
| `product-manual` | `product-manual` | Web 产品多角色操作手册（Playwright 截图 + 逻辑图 + DOCX/PDF） |
| `opc-cli` | `community-skills/opc-cli` | 多引擎 TTS/ASR：文本转语音、字幕生成、按字幕剪视频 |

### 媒体 / 舆情 / 部署

| 技能 | 路径 | 干什么 |
|---|---|---|
| `media-downloader` | `media-downloader` | 视频链接 → 下载到工作区（yt-dlp，支持 B站/YouTube 等上千站点） |
| `bettafish-opinion-analysis` | `community-skills/bettafish-opinion-analysis` | 多智能体舆情分析（三引擎并行 + 协作讨论 → Word 报告） |
| `iga-pages` | `community-skills/iga-pages` | 前端/全栈项目部署到 IGA Pages |

### 学习 / 记忆链路

| 技能 | 路径 | 干什么 |
|---|---|---|
| `lead-learn` | `lead-learn` | 收藏夹 → 各角色长期内容：增量抓取 → 字幕/转录/抽帧 → 判给谁 → 派单。**派单落在工作区，不绑定记忆系统** |

### 代码理解 / 文档产出

| 技能 | 路径 | 干什么 |
|---|---|---|
| `codebase-blueprint` | `community-skills/codebase-blueprint` | **画图**：模型（节点+边）→ 一张可下钻的 HTML 图。业务流程图 / ETL / 决策树 / 状态机 / 架构图 / 代码结构通用。拥有渲染引擎 |
| `codebase-walkthrough` | `community-skills/codebase-walkthrough` | **讲解**：读懂陌生项目 → 场景案例 + 图 + 四问卡。多场景走遍每个分支，边覆盖率为计算值。**依赖 codebase-blueprint**（调用其 core.mjs，不持有引擎副本） |

---

## 二、外部仓库（3 个，各有自己的远端）

**本库不收录它们的文件。** 新环境里要单独 clone，然后软链进技能目录。

| 技能 | 远端 | 说明 |
|---|---|---|
| `MidNight`（含 `recall`） | `https://github.com/woodmeone/MidNight.git` | 长期记忆：自动写日记 + 联想召回。**含 2161 MB 的 bge-m3 模型权重，不在 git 里** |
| `git-native-sop` | `https://github.com/woodmeone/git-native-sop` | Git 原生 AI 开发方法论（Issue / commit / PR / 真相文档五层） |
| `mattpocock-skills` | `https://github.com/mattpocock/skills` | 上游第三方技能包（engineering / productivity / misc 等约 40 个） |

> `lead-learn` 原来也在这个名单里（自带 `.git` 以便自优化回滚）。
> 2026-11-24 起它并入本库直接收录——它没有独立远端，且与全局库同生命周期。

---

## 三、模型权重与大数据（不进 git）

| 文件 | 大小 | 怎么补 |
|---|---|---|
| `MidNight/skills/recall/models/bge-m3/model.onnx_data` | 2161 MB | 跑 `recall/scripts/download_bge_m3.py` 自动拉取 |

GitHub 单文件硬限制 100 MB，免费 LFS 配额 1 GB，装不下。**一律本地生成，不进库。**

---

## 四、新环境接入（三步）

### 1. clone 本仓

```powershell
git clone https://github.com/woodmeone/global-skillslibrary.git D:\Project\globalSkills-library
```

### 2. clone 那 3 个外部仓库到同目录

```powershell
cd D:\Project\globalSkills-library
git clone https://github.com/woodmeone/MidNight.git
git clone https://github.com/woodmeone/git-native-sop.git
git clone https://github.com/mattpocock/skills.git mattpocock-skills
```

### 3. 把它们软链进技能目录

技能目录的位置**由各自的 harness 决定，不写死**。以 DSH 为例是 `~/.dsh/skills`：

```powershell
$SK = "$env:USERPROFILE\.dsh\skills"
$LIB = "D:\Project\globalSkills-library"

# 本库直接收录的
New-Item -ItemType Junction -Path "$SK\media-downloader"         -Target "$LIB\media-downloader"
New-Item -ItemType Junction -Path "$SK\product-manual"           -Target "$LIB\product-manual"
New-Item -ItemType Junction -Path "$SK\lead-learn"               -Target "$LIB\lead-learn"
New-Item -ItemType Junction -Path "$SK\codebase-blueprint"       -Target "$LIB\community-skills\codebase-blueprint"
New-Item -ItemType Junction -Path "$SK\codebase-walkthrough"     -Target "$LIB\community-skills\codebase-walkthrough"
Get-ChildItem "$LIB\community-skills" -Directory | ForEach-Object {
    New-Item -ItemType Junction -Path "$SK\$($_.Name)" -Target $_.FullName
}

# 外部仓库的
New-Item -ItemType Junction -Path "$SK\recall"         -Target "$LIB\MidNight\skills\recall"
New-Item -ItemType Junction -Path "$SK\git-native-sop" -Target "$LIB\git-native-sop"
```

### 4. 补模型权重

```powershell
python "$env:USERPROFILE\.dsh\skills\recall\scripts\download_bge_m3.py"
```

---

## 五、给新环境的自检

```powershell
# 技能数对不对。每一类按上面的流程软链完之后，实测数量是：
#   globalSkills 本库直接收录  18（community-skills 逐条）+ 4（顶层 media-downloader / product-manual / lead-learn / codebase-walkthrough）
#   globalSkills 外部仓库      mattpocock-skills 38（逐条软链，不是整目录）+ MidNight 1 + git-native-sop 1
#   TeacherPipeLine           10（独立库，不在本仓）
# 合计 71，其中指向本仓的 61。
(Get-ChildItem "$env:USERPROFILE\.dsh\skills" -Directory | Where-Object LinkType).Count

# 只看本仓的
(Get-ChildItem "$env:USERPROFILE\.dsh\skills" -Directory |
    Where-Object { $_.LinkType -and $_.Target -like '*globalSkills-library*' }).Count

# recall 能不能跑（模型在不在）
python "$env:USERPROFILE\.dsh\skills\recall\scripts\boot.py" --identity default

# lead-learn 能不能跑（路径解析对不对）
python "$env:USERPROFILE\.dsh\skills\lead-learn\scripts\dispatch.py" status
```

---

## 六、维护约定

- **新增技能**：放进 `community-skills/`（若是自己的）或顶层（若是主要工具），**同步在本文件加一行**。
- **带独立 git 的技能**：不放进本库，只在本文件第二节登记远端。
- **超大文件**（> 10 MB 或模型权重）：一律不进库，在本文件第三节登记获取方式。
- **凭据**：绝不进库。`.gitignore` 已挡 `*cookies*` / `cookiecloud.json` / `.env` / `*.pem`。

---

## 七、时间戳

- 建立：2026-11-24
- 本库收录：21 个技能
- 外部仓库：3 个（MidNight / git-native-sop / mattpocock-skills）
- 排除：模型权重 2161 MB、`node_modules`、`.venv`、`_backup`
