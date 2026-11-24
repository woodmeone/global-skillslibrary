# HTML 演示文稿生成指南

## 单文件 HTML 结构

```
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{标题}</title>
  <style>
    /* 1. 基础重置 */
    /* 2. CSS 变量（从 style-registry.md 选择风格） */
    /* 3. 通用组件样式 */
    /* 4. 风格专属样式 */
    /* 5. 导航系统样式 */
    /* 6. 编辑功能样式 */
    /* 7. 响应式样式 */
    /* 8. 无障碍样式 */
  </style>
</head>
<body>
  <!-- 风格专属背景层 -->
  <!-- 编辑热区 + 按钮 -->
  <div class="presentation">
    <div class="slide active" id="slide-1">...</div>
    <div class="slide" id="slide-2">...</div>
    ...
  </div>
  <div class="nav-container">...</div>
  <script>
    // 导航逻辑
    // 编辑逻辑
    // ECharts 条件加载（仅 combo-9）
  </script>
</body>
</html>
```

## 7 种幻灯片类型

### 1. 封面页 (Cover)

```html
<div class="slide active">
  <div class="hero-title fade-in-up">{主标题}</div>
  <div class="hero-subtitle fade-in-up delay-1">{副标题}</div>
  <div class="hero-tags fade-in-up delay-2">
    <span class="hero-tag">{标签1}</span>
    <span class="hero-tag">{标签2}</span>
  </div>
</div>
```

### 2. 内容页 (Content)

```html
<div class="slide">
  <div class="section-label fade-in-up">// {标签}</div>
  <div class="section-title fade-in-up delay-1">{标题}</div>
  <div class="section-desc fade-in-up delay-2">{描述}</div>
</div>
```

### 3. 卡片页 (Cards)

```html
<div class="slide">
  <div class="section-label fade-in-up">// {标签}</div>
  <div class="section-title fade-in-up delay-1">{标题}</div>
  <div class="card-grid fade-in-up delay-2">
    <div class="brutal-card">{卡片1}</div>
    <div class="brutal-card">{卡片2}</div>
  </div>
</div>
```

### 4. 步骤页 (Steps)

```html
<div class="slide">
  <div class="section-label fade-in-up">// STEP {N}-{M}</div>
  <div class="section-title fade-in-up delay-1">{标题}</div>
  <div class="step-group fade-in-up delay-2">
    <div class="step-item">
      <div class="step-num {level}">{N}</div>
      <div class="step-content">
        <div class="step-name">{名称}<span class="step-badge {cls}">{徽章}</span></div>
        <div class="step-detail">{详情}</div>
      </div>
    </div>
  </div>
</div>
```

### 5. 图表页 (Chart)

```html
<div class="slide">
  <div class="section-label fade-in-up">// {标签}</div>
  <div class="section-title fade-in-up delay-1">{标题}</div>
  <div class="svg-chart-container fade-in-up delay-2">
    <svg viewBox="0 0 600 400" xmlns="http://www.w3.org/2000/svg">
      <!-- SVG 图表内容 -->
    </svg>
  </div>
</div>
```

### 6. 列表页 (List)

```html
<div class="slide">
  <div class="section-label fade-in-up">// {标签}</div>
  <div class="section-title fade-in-up delay-1">{标题}</div>
  <div class="case-list fade-in-up delay-2">
    <div class="case-item">
      <div class="case-icon">{图标}</div>
      <div>{内容}</div>
    </div>
  </div>
</div>
```

### 7. 结束页 (Ending)

```html
<div class="slide">
  <div class="ending-title fade-in-up">{主标题}</div>
  <div class="ending-subtitle fade-in-up delay-1">{副标题}</div>
  <div class="ending-author fade-in-up delay-2">—— {作者}</div>
</div>
```

## 导航系统（通用）

```html
<div class="nav-container">
  <div class="nav-dots" id="navDots"></div>
  <div class="progress-bar"><div class="progress-fill" id="progressFill"></div></div>
  <div class="page-indicator"><span id="currentPage">1</span>/<span id="totalPages">N</span></div>
</div>
```

**关键特性**:
- 导航栏默认隐藏(opacity:0)，交互时显示，3秒后自动隐藏
- 键盘: →/空格(下一页)、←(上一页)、Home/End(首尾页)
- 触摸: 左右滑动，阈值 50px
- 滚轮: 800ms 防抖
- 导航点: 点击跳转，当前页高亮

## 编辑功能（可选）

```html
<div class="edit-hotzone"></div>
<button class="edit-toggle" id="editToggle" title="Edit mode (E)">EDIT</button>
```

**逻辑**:
- 左上角热区悬停显示 EDIT 按钮
- 点击或按 E 键切换 contentEditable
- 退出编辑时自动保存到 localStorage
- 页面加载时恢复 localStorage 内容

## SVG 图表模板

33 种图表模板位于 `templates/charts/` 目录，每种图表有独立的 SVG 文件。使用时需根据所选风格调整颜色。

查询 `templates/charts/charts_index.json` 获取完整图表元数据（7个分类、17个快速查找关键词、适用场景）。

### 图表选择指南

| 数据类型 | 推荐图表 | SVG 文件 |
|----------|----------|----------|
| 类别对比 | 柱状图/分组柱状图/堆叠柱状图 | bar_chart / grouped_bar_chart / stacked_bar_chart |
| 排名对比 | 横向柱状图/子弹图 | horizontal_bar_chart / bullet_chart |
| 多系列对比 | 分组柱状图 | grouped_bar_chart |
| 双向对比 | 蝴蝶图/哑铃图 | butterfly_chart / dumbbell_chart |
| 增量分解 | 瀑布图 | waterfall_chart |
| 占比分析 | 饼图/环形图/矩形树图 | pie_chart / donut_chart / treemap_chart |
| 趋势变化 | 折线图/面积图/堆叠面积图 | line_chart / area_chart / stacked_area_chart |
| 双指标趋势 | 双轴折线图 | dual_axis_line_chart |
| 多维评估 | 雷达图 | radar_chart |
| 相关性分析 | 散点图/气泡图 | scatter_chart / bubble_chart |
| 分布分析 | 箱线图/热力图 | box_plot_chart / heatmap_chart |
| 关键指标 | KPI 卡片/仪表盘/进度条 | kpi_cards / gauge_chart / progress_bar_chart |
| 80/20分析 | 帕累托图 | pareto_chart |
| 流程分析 | 桑基图 | sankey_chart |
| 里程碑 | 时间线 | timeline |
| 流程步骤 | 流程图 | process_flow |
| 战略分析 | SWOT / 波特五力 | swot_analysis / porter_five_forces |
| 定位分析 | 2x2 矩阵 | matrix_2x2 |
| 转化分析 | 漏斗图 | funnel_chart |
| 项目排期 | 甘特图 | gantt_chart |
| 组织架构 | 组织架构图 | org_chart |

### 图表颜色适配

每个风格定义了 10 个统一的图表 CSS 变量，嵌入图表 SVG 时将默认颜色替换为这些变量：

**标准图表变量**（所有风格均定义）：
| 变量 | 用途 |
|------|------|
| `--chart-color-1` ~ `--chart-color-6` | 数据系列颜色（6色） |
| `--chart-text` | 图表标题和主要文字 |
| `--chart-text-secondary` | 标签、轴文字、图例 |
| `--chart-grid` | 网格线和轴线 |
| `--chart-bg` | 图表背景（通常为 transparent） |

**替换示例**：
```svg
<!-- 替换前（默认色） -->
<rect fill="#2196F3" .../>
<text fill="#2C3E50">标题</text>
<line stroke="#E0E0E0" .../>

<!-- 替换后（使用图表变量） -->
<rect fill="var(--chart-color-1)" .../>
<text fill="var(--chart-text)">标题</text>
<line stroke="var(--chart-grid)" .../>
```

**渐变处理**：linearGradient 的两个 stop-color 替换为同一 CSS 变量，渐变效果通过 opacity 差异保持。

完整映射参考：`templates/charts/chart_color_map.json`

### 内联柱状图（简化版）

```svg
<svg viewBox="0 0 600 400" xmlns="http://www.w3.org/2000/svg">
  <line x1="80" y1="40" x2="80" y2="340" stroke="var(--chart-grid)" stroke-width="1"/>
  <line x1="80" y1="340" x2="560" y2="340" stroke="var(--chart-grid)" stroke-width="1"/>
  <rect x="120" y="{y}" width="60" height="{h}" fill="var(--chart-color-1)" rx="4"/>
  <text x="150" y="360" text-anchor="middle" font-size="12" fill="var(--chart-text-secondary)">{label}</text>
</svg>
```

### 内联雷达图（简化版）

```svg
<svg viewBox="0 0 600 400" xmlns="http://www.w3.org/2000/svg">
  <polygon points="300,60 480,160 440,340 160,340 120,160" fill="none" stroke="var(--chart-grid)"/>
  <polygon points="{计算}" fill="rgba(R,G,B,0.15)" stroke="var(--chart-color-1)" stroke-width="2.5"/>
  <circle cx="{x}" cy="{y}" r="5" fill="var(--chart-color-1)"/>
  <text x="{x}" y="{y}" text-anchor="middle" font-size="12" font-weight="bold" fill="var(--chart-color-1)">{label}</text>
</svg>
```

## 图标使用

3 种图标库位于 `templates/icons/`：

| 库 | 数量 | 风格 | 适用场景 |
|----|------|------|----------|
| tabler-outline | 5039 | 描边、简洁 | 专业、科技、通用 |
| tabler-filled | 1053 | 实心填充 | 强调、状态、徽标 |
| chunk | 640 | 简化几何 | 创意、活泼、现代 |

**嵌入方式**：读取 SVG 文件内容，内联到 HTML 中。

```html
<!-- 列表页图标示例 -->
<div class="case-item">
  <div class="case-icon">
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="var(--text-accent)" stroke-width="2">
      <path d="M12 2L2 7l10 5 10-5-10-5z"/>
    </svg>
  </div>
  <div>{内容}</div>
</div>
```

**颜色适配**：将图标 SVG 中的 `stroke` 或 `fill` 替换为 `var(--text-accent)`、`var(--text-primary)` 等风格变量。

**常用图标**：arrow-right, check, x, chevron-right, chevron-down, circle-check, alert-triangle, info-circle, chart-bar, chart-line, users, target, rocket, lightbulb, settings, star, heart, bookmark, download, share

## ECharts 交互式图表

当需要交互式图表（动画、tooltip、缩放）时，使用 ECharts 替代 SVG 静态图表。

### 模板文件

`templates/charts/echarts_templates.json` 包含 20 种图表的 ECharts option 模板。

### 使用步骤

1. 读取 `echarts_templates.json`，选择对应图表类型的 option 模板
2. 从所选风格的 `config.json` 中解析 CSS 变量到 hex 值（ECharts 不支持 CSS 变量）
3. 用实际数据替换模板中的示例数据
4. 在 HTML 中引入 ECharts CDN 并初始化图表

### HTML 嵌入模板

```html
<div id="chart-{slideId}" style="width: 100%; height: 400px;"></div>
<script src="https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js"></script>
<script>
  (function() {
    var chart = echarts.init(document.getElementById('chart-{slideId}'));
    var option = {OPTION_PLACEHOLDER};
    chart.setOption(option);
    window.addEventListener('resize', function() { chart.resize(); });
  })();
</script>
```

### 颜色解析

ECharts 不支持 CSS 变量，需在生成时从风格 config.json 解析：

```javascript
// 从 config.json css_variables 中读取
color: ['#60a5fa', '#a78bfa', '#f093fb', '#34d399', '#fbbf24', '#f87171'],
textStyle: { color: '#ffffff' },
// axisLabel, splitLine 等同理
```

### 支持的图表类型

bar_chart, horizontal_bar_chart, grouped_bar_chart, stacked_bar_chart, line_chart, area_chart, stacked_area_chart, dual_axis_line_chart, pie_chart, donut_chart, radar_chart, scatter_chart, funnel_chart, gauge_chart, heatmap_chart, treemap_chart, sankey_chart, waterfall_chart, kpi_cards (gauge variant), bubble_chart

### 注意事项

- ECharts 适用于所有风格，不限于 combo-9
- PPTX 导出时 Playwright 会执行 JavaScript，ECharts 图表可正确截图
- 单文件 HTML 中 ECharts CDN 需要网络连接
- 建议同一页面最多 2-3 个 ECharts 图表，避免性能问题

## 动画系统

### fade-in-up（通用入场动画）

```css
.fade-in-up {
  opacity: 0;
  transform: translateY(20px);
  animation: fadeInUp 0.6s ease forwards;
}
@keyframes fadeInUp {
  to { opacity: 1; transform: translateY(0); }
}
.delay-1 { animation-delay: 0.1s; }
.delay-2 { animation-delay: 0.2s; }
/* ... delay-8: 0.8s */
```

### prefers-reduced-motion

```css
@media (prefers-reduced-motion: reduce) {
  .slide { transition: opacity 0.3s ease; transform: none !important; }
  .fade-in-up { animation: none; opacity: 1; transform: none; }
}
```

## 动画系统集成

### CSS 动画集成

在 `<style>` 中引入 `templates/animations/animations.css` 的内容，或内联关键动画类：

```css
/* 从 animations.css 引入需要的动画 */
.anim-fade-up { animation: kf-fade-up var(--anim-dur, .7s) cubic-bezier(.4,0,.2,1) both; }
.anim-rise-in { animation: kf-rise .9s cubic-bezier(.4,0,.2,1) both; }
.anim-stagger-list > * { opacity: 0; animation: kf-rise .65s cubic-bezier(.4,0,.2,1) both; }
/* ... 按需引入 */
```

在幻灯片元素上应用动画类：

```html
<div class="slide active anim-blur-in">
  <h1 class="hero-title anim-rise-in">标题</h1>
  <ul class="anim-stagger-list">
    <li>第一项</li>
    <li>第二项</li>
  </ul>
</div>
```

### Canvas FX 集成

在 `</body>` 前引入 FX 运行时和模块：

```html
<script>
// 内联 _util.js 内容
(function(){var U=(window.PPX=window.PPX||{});U._u={};...})();
</script>
<script>
// 内联 fx-runtime.js 内容（或仅引入需要的 FX 模块）
</script>
```

在幻灯片容器上添加 `data-fx` 属性：

```html
<div class="slide active" data-fx="constellation">
  <!-- constellation 效果将在此幻灯片激活时自动启动 -->
</div>

<div class="slide" data-fx="particle-burst">
  <!-- 粒子爆发效果 -->
</div>
```

### 智能动画推荐

根据 `animations_index.json` 的三个映射表选择动画：

1. **slide_type_mapping**: 根据幻灯片类型推荐
   - cover → anim-rise-in / anim-blur-in + galaxy-swirl / constellation
   - ending → anim-confetti-burst + confetti-cannon / firework
   - chart → anim-fade-up / anim-zoom-pop + counter-explosion

2. **style_theme_mapping**: 根据风格主题推荐
   - dark_tech → matrix-rain / data-stream / neural-net + anim-glitch-in
   - light_minimal → anim-fade-up / anim-stagger-list（无 Canvas FX）
   - cyberpunk → matrix-rain / letter-explode + anim-neon-glow

3. **content_type_mapping**: 根据内容类型推荐
   - data_metrics → anim-counter-up / anim-zoom-pop + counter-explosion
   - architecture → anim-path-draw + knowledge-graph / neural-net
   - celebration → anim-confetti-burst + confetti-cannon / firework

**优先级**: content_type > slide_type > style_theme

## 响应式断点

```css
@media (max-width: 768px) {
  .slide { padding: 40px 24px; }
  .hero-title { font-size: 2rem; }
  .card-grid, .risk-grid, .exp-grid { grid-template-columns: 1fr; }
  .nav-container { padding: 8px 16px 12px; gap: 10px; }
}
```
