# 模板管理架构指南

## 一、核心文件结构

```
powerful-ppt/
├── templates/
│   └── styles/                          # 模板存储目录
│       ├── combo-1-neo-brutalism/       # 模板文件夹
│       │   ├── config.json              # 【必需】模板元数据 + CSS变量
│       │   ├── base.css                 # 【必需】基础样式、布局、字体
│       │   ├── components.css           # 【必需】组件样式（卡片、标签、步骤等）
│       │   ├── effects.css              # 【可选】背景效果、动画
│       │   └── preview.png              # 【自动生成】预览图
│       ├── combo-2-xxx/
│       ├── ...
│       └── styles_index.json            # 【自动生成】索引文件 ★ AI读取此文件发现模板
│
├── scripts/
│   ├── template_manager.py              # 【推荐】统一管理工具
│   ├── sync_styles_index.py             # 同步索引脚本
│   └── generate_previews.js             # 生成预览图脚本
│
└── references/
    ├── style-registry.md                # 【可选】人工参考文档（不影响AI）
    └── template-management.md           # 本文档
```

## 二、AI 如何发现模板

**重要：AI 不依赖 style-registry.md，而是直接读取源文件！**

```
AI 发现模板流程：
┌─────────────────────────────────────────────────────────────┐
│ 1. 读取 styles_index.json → 获取所有模板ID和路径            │
│                                                             │
│ 2. 读取 {style-folder}/config.json → 获取CSS变量和元数据    │
│                                                             │
│ 3. 读取 {style-folder}/*.css → 获取样式定义                 │
└─────────────────────────────────────────────────────────────┘
```

**style-registry.md 的作用**：
- ✅ 人工参考文档，方便开发者快速了解模板特性
- ✅ 包含详细的CSS变量说明和效果描述
- ❌ AI 不依赖此文件
- ❌ 添加新模板后无需更新此文件

## 三、添加模板后的完整流程

### 方式一：使用 template_manager.py（推荐）

```bash
# 1. 创建模板（自动生成骨架文件）
python scripts/template_manager.py create --name "My Style" --theme light

# 2. 编辑 CSS 文件，完善样式
# 编辑 templates/styles/combo-{n}-my-style/base.css
# 编辑 templates/styles/combo-{n}-my-style/components.css
# 编辑 templates/styles/combo-{n}-my-style/effects.css

# 3. 质量检查
python scripts/template_manager.py quality-check --id combo-{n}

# 4. 同步索引（如果修改了 config.json）
python scripts/template_manager.py sync

# 5. 生成预览
python scripts/template_manager.py preview

# 完成！AI 现在可以自动发现这个模板
```

### 方式二：手动操作

```bash
# 1. 创建文件夹和文件
mkdir templates/styles/combo-{n}-{name}
# 编写 config.json, base.css, components.css, effects.css

# 2. 同步索引（让 AI 能发现新模板）
python scripts/sync_styles_index.py

# 3. 生成预览
node scripts/generate_previews.js

# 完成！无需修改 style-registry.md
```

### 2.1 config.json（必需）

```json
{
  "id": "combo-12",                    // 唯一ID，格式：combo-{n}
  "name": "Vintage Newspaper",         // 英文名称
  "name_cn": "旧报纸复古风",            // 中文名称
  "version": "1.0.0",                  // 版本号
  "best_for": ["Editorial", "History"], // 适用场景标签
  "theme": "light",                    // light 或 dark
  "pptx_bg": "ddd5c0",                 // PPTX导出背景色（无#的6位hex）
  "chart_support": "svg+echarts",      // 图表支持类型
  "micro_interactions": [],            // 微交互名称列表
  "css_variables": {                   // CSS变量定义
    "--bg-primary": "#ddd5c0",
    "--text-primary": "#1e1a16",
    // ... 至少15个变量
    "--chart-color-1": "#7a2828",
    // ... 6个图表颜色
    "--chart-text": "#1e1a16",
    "--chart-text-secondary": "#5a5248",
    "--chart-grid": "#b8b098",
    "--chart-bg": "transparent"
  },
  "includes": ["base.css", "effects.css", "components.css"],
  "quality_score": 100.0               // 质量评分（自动生成）
}
```

**必需字段**：`id`, `name`, `version`, `best_for`, `theme`, `pptx_bg`, `css_variables`, `includes`

**CSS变量必需项**：
- 颜色变量：`--bg-primary`, `--text-primary`, `--text-secondary`, `--text-accent`
- 图表变量：`--chart-color-1` 到 `--chart-color-6`，`--chart-text`, `--chart-text-secondary`, `--chart-grid`, `--chart-bg`

### 2.2 base.css（必需）

```css
:root {
  /* 从 config.json 复制所有 CSS 变量 */
}

* { margin: 0; padding: 0; box-sizing: border-box; }

body { /* 字体、背景、颜色 */ }

.slide { /* 幻灯片基础样式 */ }
.slide.active { /* 激活状态 */ }

/* 排版样式 */
.hero-title { }
.hero-subtitle { }
.section-label { }
.section-title { }
.section-desc { }
.ending-title { }
.ending-subtitle { }
.ending-author { }

/* 必需包含 */
@media (max-width: 768px) { /* 响应式 */ }
@media (prefers-reduced-motion: reduce) { /* 无障碍 */ }
```

### 2.3 components.css（必需）

```css
.brutal-card { }           /* 卡片组件 */
.brutal-card.card-red { }  /* 彩色卡片变体 */
.card-grid { }             /* 卡片网格 */

.hero-tag { }              /* 标签 */
.hero-tag.tag-red { }      /* 彩色标签变体 */

.step-group { }            /* 步骤组 */
.step-item { }             /* 步骤项 */
.step-num { }              /* 步骤数字 */
.step-badge { }            /* 步骤徽章 */

.case-list { }             /* 列表 */
.case-item { }             /* 列表项 */

.svg-chart-container { }   /* 图表容器 */
```

### 2.4 effects.css（可选）

```css
.slide::before { }         /* 背景效果层1 */
.slide::after { }          /* 背景效果层2 */

/* 动画定义 */
@keyframes fadeIn { }
.slide.active .section-label { animation: ... }
```

### 2.5 styles_index.json（自动生成）

```json
{
  "meta": { "total": 12, "updated": "2026-04-15" },
  "categories": {
    "light": ["combo-1", "combo-4", "combo-6", "combo-7", "combo-10", "combo-12"],
    "dark": ["combo-2", "combo-3", "combo-5", "combo-8", "combo-9", "combo-11"]
  },
  "quickLookup": {
    "tech": ["combo-1", "combo-2", ...],
    "business": ["combo-5", "combo-6"],
    "creative": ["combo-1", "combo-3", ...],
    "education": ["combo-4", "combo-7"]
  },
  "styles": {
    "combo-12": {
      "id": "combo-12",
      "name": "Vintage Newspaper",
      "name_cn": "旧报纸复古风",
      "best_for": ["Editorial content", "History & Culture"],
      "theme": "light",
      "pptx_bg": "ddd5c0",
      "preview": "combo-12-vintage-newspaper/preview.png",
      "config": "combo-12-vintage-newspaper/config.json"
    }
  }
}
```

## 三、增删改查操作指南

### 方式一：使用 template_manager.py（推荐）

```bash
# 创建模板（自动生成骨架文件）
python scripts/template_manager.py create --name "My Style" --theme light --name-cn "我的风格"

# 验证模板
python scripts/template_manager.py validate --id combo-13

# 质量检查（评分）
python scripts/template_manager.py quality-check --id combo-13

# 列出所有模板
python scripts/template_manager.py list

# 同步索引
python scripts/template_manager.py sync

# 生成预览
python scripts/template_manager.py preview

# 删除模板
python scripts/template_manager.py delete --id combo-13
```

### 方式二：手动操作

#### 添加模板

1. **创建文件夹**：`templates/styles/combo-{n}-{name}/`
2. **编写 config.json**：参考 2.1 节
3. **编写 base.css**：参考 2.2 节
4. **编写 components.css**：参考 2.3 节
5. **编写 effects.css**（可选）：参考 2.4 节
6. **同步索引**：`python scripts/sync_styles_index.py`
7. **生成预览**：`node scripts/generate_previews.js`

#### 删除模板

1. **删除文件夹**：`rm -rf templates/styles/combo-{n}-{name}/`
2. **同步索引**：`python scripts/sync_styles_index.py`

#### 修改模板

1. **编辑文件**：修改 CSS 或 config.json
2. **如修改了 config.json**：`python scripts/sync_styles_index.py`
3. **如需更新预览**：删除 preview.png 后运行 `node scripts/generate_previews.js`

## 四、质量评分标准

| 检查项 | 分数 | 要求 |
|--------|------|------|
| config_complete | 10 | config.json 包含所有必需字段 |
| css_files_exist | 10 | base.css 和 components.css 存在 |
| css_variables_defined | 10 | 至少定义 15 个 CSS 变量 |
| preview_exists | 10 | preview.png 存在 |
| no_syntax_errors | 10 | CSS 无语法错误 |
| responsive_design | 10 | 包含 @media 响应式断点 |
| reduced_motion | 10 | 包含 prefers-reduced-motion |
| color_contrast_ok | 10 | 文字与背景对比度足够 |

**等级**：
- A+ (90-100)：优秀，可发布
- A (80-89)：良好
- B (70-79)：合格
- C (60-69)：待改进
- D (<60)：不合格

## 五、常见问题

### Q: 修改 CSS 后需要同步索引吗？
A: 不需要。只有修改 config.json 才需要同步。

### Q: 预览图怎么更新？
A: 删除 preview.png 后运行 `node scripts/generate_previews.js`。

### Q: 如何添加新的适用场景分类？
A: 修改 `sync_styles_index.py` 中的 `keyword_map` 字典。

### Q: 用户模板存在哪里？
A: 建议使用 `templates/user-styles/` 目录，与系统模板分开。

## 六、文件依赖关系图

```
config.json ─────────────────────────────────────────┐
    │                                                 │
    ├── 读取 ──→ sync_styles_index.py ──→ styles_index.json
    │                                                 │
    ├── 读取 ──→ generate_previews.js ──→ preview.png │
    │                                                 │
    └── CSS变量 ──→ base.css ──┐                      │
                              ├──→ HTML生成 ──→ 演示页面
    effects.css ───────────────┤
                              │
    components.css ────────────┘
```

## 七、快速参考卡片

| 操作 | 命令 |
|------|------|
| 创建模板 | `python scripts/template_manager.py create --name "Name" --theme light` |
| 验证模板 | `python scripts/template_manager.py validate --id combo-N` |
| 质量评分 | `python scripts/template_manager.py quality-check --id combo-N` |
| 同步索引 | `python scripts/template_manager.py sync` |
| 生成预览 | `python scripts/template_manager.py preview` |
| 列出模板 | `python scripts/template_manager.py list` |
| 删除模板 | `python scripts/template_manager.py delete --id combo-N` |
