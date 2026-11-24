# Style Registry — 18 种风格完整配置

## 目录

1. [combo-1: Neo-Brutalism + 3D](#combo-1)
2. [combo-2: Retro-Futurism](#combo-2)
3. [combo-3: Maximalism + Typography](#combo-3)
4. [combo-4: Naive + Typography](#combo-4)
5. [combo-5: Bento + 3D Glass](#combo-5)
6. [combo-6: Neo-Minimalism](#combo-6)
7. [combo-7: Memphis](#combo-7)
8. [combo-8: Blueprint](#combo-8)
9. [combo-9: Keynote Dark](#combo-9)
10. [combo-10: Coffee Editorial](#combo-10)
11. [combo-11: Immersive 3D Scene](#combo-11)
12. [combo-12: Vintage Newspaper](#combo-12)
13. [combo-13: Tokyo Night](#combo-13)
14. [combo-14: Dracula](#combo-14)
15. [combo-15: Corporate Clean](#combo-15)
16. [combo-16: Pitch Deck VC](#combo-16)
17. [combo-17: Glassmorphism](#combo-17)
18. [combo-18: Aurora](#combo-18)

---

## combo-1 {#combo-1}

**名称**: 数字粗野建筑 Neo-Brutalism + 3D
**适用场景**: 创意机构、Web3、科技初创、安全/警示主题
**图表支持**: SVG 静态
**微交互**: magnetic-btn, text-scramble, parallax-card

### CSS 变量

```css
:root {
  --bg-primary: #fef9ef;
  --bg-secondary: #f0e6d3;
  --bg-card: #ffffff;
  --brutal-black: #1a1a1a;
  --brutal-red: #ff4444;
  --brutal-yellow: #ffe14d;
  --brutal-blue: #4dabf7;
  --brutal-green: #51cf66;
  --brutal-purple: #cc5de8;
  --brutal-orange: #ff922b;
  --text-primary: #1a1a1a;
  --text-secondary: #6b6b6b;
  --text-accent: #ff4444;
  --shadow-brutal: 4px 4px 0px var(--brutal-black);
  --shadow-brutal-lg: 6px 6px 0px var(--brutal-black);
  --shadow-brutal-hover: 8px 8px 0px var(--brutal-black);
  --border-brutal: 3px solid var(--brutal-black);
  --radius: 0px;
}
```

### 背景效果

几何形状装饰（圆形/方形，极低透明度），无动画。

### 组件样式

- **卡片**: 白底 + 3px 粗边框 + 硬阴影(4px 4px 0px) + hover 弹跳
- **彩色卡片**: 对应颜色边框 + 对应颜色硬阴影
- **标题**: Arial Black 900 / 大写 / text-shadow 黄色
- **标签**: 彩色色块 + 粗边框 + 硬阴影
- **步骤**: 数字方块(红/橙/黄) + 必做/重要/进阶徽章

### PPTX 背景色

`fef9ef`

---

## combo-2 {#combo-2}

**名称**: 80年代未来 Retro-Futurism
**适用场景**: 科技主题、赛博朋克风格、AI/编程教程
**图表支持**: SVG 静态
**微交互**: glitch-text, neon-pulse, cyber-scan

### CSS 变量

```css
:root {
  --bg-primary: #0d0221;
  --bg-secondary: #150535;
  --bg-card: rgba(13,2,33,0.85);
  --neon-cyan: #00fff5;
  --neon-pink: #ff2a6d;
  --neon-purple: #b537f2;
  --neon-yellow: #ffe135;
  --neon-green: #05ffa1;
  --text-primary: #e0d7ff;
  --text-secondary: #8b7fb0;
  --text-accent: #00fff5;
  --scanline-opacity: 0.03;
  --glow-cyan: 0 0 10px #00fff5, 0 0 40px rgba(0,255,245,0.3);
  --glow-pink: 0 0 10px #ff2a6d, 0 0 40px rgba(255,42,109,0.3);
  --glow-purple: 0 0 10px #b537f2, 0 0 40px rgba(181,55,242,0.3);
  --radius: 4px;
  --radius-lg: 8px;
}
```

### 背景效果

1. **扫描线**: `repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(0,0,0,0.03) 2px, rgba(0,0,0,0.03) 4px)`
2. **暗角**: `radial-gradient(ellipse at center, transparent 60%, rgba(13,2,33,0.6) 100%)`
3. **移动扫描线**: 4px 高度，6s linear infinite 从上到下
4. **网格背景**: `linear-gradient(rgba(0,255,245,0.03) 1px, transparent 1px)` 40px 间隔

### 组件样式

- **霓虹文字**: text-shadow 多层 glow（青/粉/紫）
- **赛博朋克切角卡片**: `clip-path: polygon(8px 0, 100% 0, calc(100% - 8px) 100%, 0 100%)`
- **等宽字体**: Courier New / SF Mono

### PPTX 背景色

`0d0221`

---

## combo-3 {#combo-3}

**名称**: 极繁主义排版 Maximalism + Typography
**适用场景**: 时尚品牌、艺术展览、文化评论
**图表支持**: SVG 静态
**微交互**: marquee-text, rotate-hover, split-reveal

### CSS 变量

```css
:root {
  --bg-primary: #0a0a0a;
  --bg-secondary: #141414;
  --bg-card: rgba(255,255,255,0.04);
  --accent-1: #ff3d00;
  --accent-2: #00e5ff;
  --accent-3: #ffea00;
  --accent-4: #d500f9;
  --text-primary: #ffffff;
  --text-secondary: #888888;
  --text-accent: #ff3d00;
  --radius: 2px;
}
```

### 背景效果

多层渐变叠加 + 噪点纹理 + 大字装饰

### 组件样式

- **超大标题**: clamp(3rem, 10vw, 8rem)，letter-spacing: -0.05em
- **混合字体**: 衬线 + 无衬线混排
- **文字叠层**: 多行文字重叠，不同颜色/透明度
- **色块分割**: 大面积纯色区域

### PPTX 背景色

`0a0a0a`

---

## combo-4 {#combo-4}

**名称**: 朴素排版 Naive + Typography
**适用场景**: 个人博客、手作品牌、教育内容
**图表支持**: SVG 静态
**微交互**: hand-draw-border, wiggle-hover, stamp-appear

### CSS 变量

```css
:root {
  --bg-primary: #faf8f5;
  --bg-secondary: #f0ece4;
  --bg-card: #ffffff;
  --accent-1: #e85d3a;
  --accent-2: #2d6a4f;
  --accent-3: #264653;
  --text-primary: #2c2c2c;
  --text-secondary: #7a7a7a;
  --text-accent: #e85d3a;
  --radius: 12px;
}
```

### 背景效果

米白底 + 微妙纸纹 + 手绘线条装饰

### 组件样式

- **手绘边框**: border-radius 不规则 + 虚线
- **圆角卡片**: 12px 圆角，柔和阴影
- **手写风格字体**: cursive / 手写体
- **贴纸效果**: 旋转 + 半透明 + 阴影

### PPTX 背景色

`faf8f5`

---

## combo-5 {#combo-5}

**名称**: 便当盒 3D 玻璃 Bento + 3D Glass
**适用场景**: 产品展示、SaaS 介绍、数据仪表盘
**图表支持**: SVG 静态 + ECharts
**微交互**: glass-tilt, depth-parallax, glow-border

### CSS 变量

```css
:root {
  --bg-primary: #0f0f23;
  --bg-secondary: #1a1a3e;
  --bg-card: rgba(255,255,255,0.06);
  --bg-glass: rgba(255,255,255,0.08);
  --accent-1: #6c63ff;
  --accent-2: #00d4aa;
  --accent-3: #ff6b9d;
  --text-primary: #f0f0f0;
  --text-secondary: #8888aa;
  --text-accent: #6c63ff;
  --glass-border: 1px solid rgba(255,255,255,0.12);
  --glass-blur: blur(20px);
  --radius: 16px;
  --radius-lg: 24px;
}
```

### 背景效果

深色底 + 渐变光斑 + 网格线

### 组件样式

- **玻璃卡片**: `backdrop-filter: blur(20px)` + 半透明边框
- **Bento 网格**: CSS Grid 不等宽布局
- **3D 悬浮**: `transform: perspective(1000px) rotateX/Y` + hover
- **发光边框**: box-shadow 渐变发光

### PPTX 背景色

`0f0f23`

---

## combo-6 {#combo-6}

**名称**: 新极简主义 Neo-Minimalism
**适用场景**: 企业报告、高端品牌、投资路演
**图表支持**: SVG 静态 + ECharts
**微交互**: underline-expand, count-up, fade-slide

### CSS 变量

```css
:root {
  --bg-primary: #ffffff;
  --bg-secondary: #f5f5f7;
  --bg-card: #ffffff;
  --accent-1: #1d1d1f;
  --accent-2: #0071e3;
  --accent-3: #34c759;
  --text-primary: #1d1d1f;
  --text-secondary: #86868b;
  --text-accent: #0071e3;
  --radius: 12px;
  --radius-lg: 20px;
}
```

### 背景效果

纯白/浅灰 + 极细线条 + 大量留白

### 组件样式

- **细线卡片**: 1px 边框，无阴影
- **大号数字**: clamp(2rem, 6vw, 5rem)，font-weight: 300
- **下划线链接**: 2px 底线 + hover 扩展
- **分段线**: 1px solid #e5e5e7

### PPTX 背景色

`ffffff`

---

## combo-7 {#combo-7}

**名称**: 孟菲斯 Memphis
**适用场景**: 创意设计、儿童教育、趣味科普
**图表支持**: SVG 静态
**微交互**: bounce-in, confetti, zigzag-border

### CSS 变量

```css
:root {
  --bg-primary: #fffbe6;
  --bg-secondary: #fff5cc;
  --bg-card: #ffffff;
  --memphis-pink: #ff6b9d;
  --memphis-blue: #4ecdc4;
  --memphis-yellow: #ffe66d;
  --memphis-purple: #a855f7;
  --memphis-green: #22c55e;
  --memphis-orange: #fb923c;
  --text-primary: #1a1a1a;
  --text-secondary: #666666;
  --text-accent: #ff6b9d;
  --radius: 8px;
}
```

### 背景效果

浅黄底 + 几何图案（三角/圆/锯齿/波浪）+ 彩色装饰

### 组件样式

- **锯齿边框**: `clip-path: polygon()` 锯齿形
- **彩色圆点**: 大号彩色圆点装饰
- **斜条纹**: `repeating-linear-gradient(45deg)` 条纹背景
- **波浪分割**: SVG wave 路径

### PPTX 背景色

`fffbe6`

---

## combo-8 {#combo-8}

**名称**: 蓝图 Blueprint
**适用场景**: 技术文档、架构设计、工程教程
**图表支持**: SVG 静态
**微交互**: draw-line, blueprint-grid, measure-appear

### CSS 变量

```css
:root {
  --bg-primary: #0a1628;
  --bg-secondary: #0f1f3a;
  --bg-card: rgba(16,40,74,0.6);
  --blueprint-line: #2a6cb8;
  --blueprint-dim: #1a4a7a;
  --blueprint-accent: #4fc3f7;
  --blueprint-warn: #ffb74d;
  --blueprint-danger: #ef5350;
  --text-primary: #b8d4f0;
  --text-secondary: #5a7fa0;
  --text-accent: #4fc3f7;
  --radius: 2px;
}
```

### 背景效果

深蓝底 + 网格线（主次两级）+ 坐标标注

### 组件样式

- **蓝图网格**: `linear-gradient` 双层网格（大格 100px + 小格 20px）
- **虚线边框**: `border: 1px dashed var(--blueprint-line)`
- **标注线**: 带箭头的尺寸标注
- **技术字体**: 'Courier New', monospace
- **圆形节点**: 小圆点连接线

### PPTX 背景色

`0a1628`

---

## combo-9 {#combo-9}

**名称**: 乔布斯深色科技 Keynote Dark
**适用场景**: 产品发布会、数据报告、科技演讲
**图表支持**: ECharts 交互 + SVG 静态
**微交互**: orb-float, count-up, spotlight

### CSS 变量

```css
:root {
  --bg-primary: #000000;
  --bg-secondary: #0a0a0a;
  --bg-card: rgba(255,255,255,0.05);
  --color-primary: #60a5fa;
  --color-secondary: #a78bfa;
  --color-accent: #f093fb;
  --color-success: #34d399;
  --color-warning: #fbbf24;
  --color-danger: #f87171;
  --text-primary: #ffffff;
  --text-secondary: #9ca3af;
  --text-tertiary: #6b7280;
  --radius: 24px;
  --radius-sm: 12px;
}
```

### 背景效果

1. **浮动光斑**: 3 层，blur(80px)，径向渐变，8s ease-in-out infinite
   - 紫: `radial-gradient(circle, rgba(167,139,250,0.3), transparent 70%)`
   - 粉: `radial-gradient(circle, rgba(240,147,251,0.2), transparent 70%)`
   - 青: `radial-gradient(circle, rgba(96,165,250,0.2), transparent 70%)`

### 组件样式

- **大圆角卡片**: border-radius 24px，毛玻璃效果
- **渐变文字**: `background: linear-gradient()` + `-webkit-background-clip: text`
- **ECharts 图表**: 双 CDN 备用加载，onerror 降级
- **HTML 导出按钮**: Blob + download（可选）

### PPTX 背景色

`000000`

### ECharts 条件加载

```html
<script src="https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js"
        onerror="document.write('<script src=&quot;https://unpkg.com/echarts@5/dist/echarts.min.js&quot;><\/script>')"></script>
```

---

## Combo 制作注意点

### 导航系统规范

- **禁止使用明显的按钮导航**（如"上一页"/"下一页"按钮），所有 combo 模板必须使用无感导航
- 导航系统由 `.nav-container` + `.nav-dots` + `.progress-bar` + `.page-indicator` 组成
- **自动隐藏**：导航栏默认 `opacity: 0`，用户交互时短暂显示，3秒后自动隐藏（Critical：防止 PPTX 导出残留文字）
- 导航交互支持：键盘（→/←/Space/Home/End）、滚轮（800ms防抖）、触摸滑动（阈值50px）、导航点点击
- 当前页导航点使用 `.active` 类高亮，样式应与风格主题协调
- 进度条 `.progress-fill` 使用风格强调色渐变

### 3D 空间与视角控制（combo-11+）

- 支持 `data-perspective` 属性控制每页的3D空间视角：`center`（正视）、`left`（左偏）、`right`（右偏）、`top`（俯视）
- 切换幻灯片时，`perspective-origin` 随视角属性平滑过渡，营造3D空间移动感
- 鼠标移动驱动3D场景视差：`.scene-3d`、`.depth-grid`、`.particle-field` 等层根据鼠标位置微调 transform
- 幻灯片退出动画使用 `.exit-left` / `.exit-right` 类，实现方向感知的3D空间退场
- 各3D效果层需设置 `transition: transform 0.12s ease-out` 确保鼠标视差流畅

### 通用规范

- 每个 combo 必须包含 `config.json`、`base.css`、`components.css`，`effects.css` 可选
- `config.json` 必须定义 `--chart-color-1` 到 `--chart-color-6` 共6个图表颜色 + 4个图表辅助变量
- 所有风格共享相同的组件类名（`.brutal-card`、`.step-num`、`.hero-tag` 等），通过 CSS 变量差异化
- 必须包含 `prefers-reduced-motion` 媒体查询和 768px 响应式断点
- 幻灯片切换基础机制：`.slide` 默认隐藏 → `.slide.active` 显示，通过 CSS class 切换

---

## combo-10 {#combo-10}

**名称**: 咖啡编辑风 Coffee Editorial
**适用场景**: 创意作品集、生活方式品牌、编辑内容、餐饮
**图表支持**: SVG 静态 + ECharts 交互
**微交互**: warm-fade, serif-reveal, mono-label

### CSS 变量

```css
:root {
  --bg-primary: #fffcf5;
  --bg-secondary: #e5dece;
  --bg-card: #ffffff;
  --bg-warm: #f5efe3;
  --color-burgundy: #511f20;
  --color-coral: #ff4a62;
  --color-red: #ff2c47;
  --color-brown: #785449;
  --color-beige: #d4c5a9;
  --text-primary: #511f20;
  --text-secondary: #785449;
  --text-tertiary: #a08c7a;
  --text-accent: #ff2c47;
  --radius: 12px;
  --radius-sm: 6px;
  --radius-lg: 20px;
}
```

### 背景效果

暖色径向渐变光斑 + SVG 噪点纹理 + 编辑中线。

### 组件样式

- **卡片**: 白底 + 米色边框 + 柔和阴影 + hover 上浮
- **彩色卡片**: 左侧色条（红/棕/珊瑚/米色）
- **标题**: Fraunces 衬线体 400 / Nunito Sans 无衬线
- **标签**: Fragment Mono + 小写 + 圆角背景
- **步骤**: Fraunces 数字方块 + 必做/重要/进阶徽章

### PPTX 背景色

`fffcf5`

---

## combo-11 {#combo-11}

**名称**: 沉浸式3D场景 Immersive 3D Scene
**适用场景**: 娱乐、品牌展示、沉浸式叙事、高端活动
**图表支持**: SVG 静态 + ECharts 交互
**微交互**: parallax-depth, 3d-tilt, scene-transition

### CSS 变量

```css
:root {
  --bg-primary: #111111;
  --bg-secondary: #1a1a1a;
  --bg-card: rgba(255,255,255,0.05);
  --color-accent-1: #6366f1;
  --color-accent-2: #8b5cf6;
  --color-accent-3: #ec4899;
  --text-primary: #f5f5f5;
  --text-secondary: #a3a3a3;
  --text-accent: #6366f1;
  --radius: 16px;
  --radius-sm: 8px;
  --radius-lg: 24px;
}
```

### 背景效果

3D 透视网格 + 粒子场 + 鼠标视差 + 方向感知切换动画。

### 组件样式

- **卡片**: 毛玻璃效果 + 3D 倾斜交互
- **3D 场景层**: `.scene-3d` / `.depth-grid` / `.particle-field`
- **视角控制**: `data-perspective` 属性（center/left/right/top）

### PPTX 背景色

`111111`

---

## combo-12 {#combo-12}

**名称**: 旧报纸复古风 Vintage Newspaper
**适用场景**: 编辑内容、历史文化、文学分析、新闻报道、复古品牌
**图表支持**: SVG 静态 + ECharts 交互
**微交互**: ink-reveal, column-sweep, typestamp-appear

### CSS 变量

```css
:root {
  --bg-primary: #ddd5c0;
  --bg-secondary: #c8bfa0;
  --bg-card: #e8e0cc;
  --bg-aged: #d0c8b0;
  --color-ink: #1e1a16;
  --color-ink-light: #3a342c;
  --color-burgundy: #7a2828;
  --color-rust: #9a4a32;
  --color-olive: #6a6a4a;
  --color-sage: #8a8a68;
  --color-rule: #a09880;
  --color-rule-light: #b8b098;
  --text-primary: #1e1a16;
  --text-secondary: #5a5248;
  --text-tertiary: #8a7e70;
  --text-accent: #7a2828;
  --radius: 0px;
  --radius-sm: 0px;
  --radius-lg: 2px;
  --chart-color-1: #7a2828;
  --chart-color-2: #6a6a4a;
  --chart-color-3: #9a4a32;
  --chart-color-4: #8a8a68;
  --chart-color-5: #a09880;
  --chart-color-6: #5a5248;
  --chart-text: #1e1a16;
  --chart-text-secondary: #5a5248;
  --chart-grid: #b8b098;
  --chart-bg: transparent;
}
```

### 背景效果

1. **纸张噪点**: SVG feTurbulence 分形噪声，opacity 0.5，mix-blend-mode: multiply，模拟泛黄新闻纸质感
2. **墨迹晕染**: 径向渐变光斑（勃艮第红 + 橄榄绿），低透明度缓慢脉动动画
3. **栏线分隔**: `.newspaper-columns` 伪元素在 33.33% 和 66.66% 位置绘制竖线，opacity 0.08
4. **墨渍装饰**: `.ink-stain` 圆形径向渐变，缓慢缩放脉动动画

### 组件样式

- **卡片**: 米色底 + 规则线边框 + 2px 硬阴影 + hover 上浮，顶部色条（勃艮第/铁锈/橄榄/鼠尾草）
- **标题**: Playfair Display 900 / 大写 / 紧凑字距
- **标签**: Courier Prime + 大写 + 方框边框（非填充背景），呼应报纸分类标签
- **步骤**: Playfair Display 数字方块 + 必做(勃艮第)/重要(墨色)/可选(橄榄)徽章
- **列表项**: 米色底 + 左侧3px色条 + 规则线边框
- **分割线**: `.editorial-divider` 带 ◆ 菱形装饰 / `.newspaper-rule` 虚线样式
- **首字下沉**: `.drop-cap` 首字母放大3.5em + 勃艮第红 + Playfair Display 900
- **报头边框**: `.masthead-border` 双层边框（外2px墨色 + 内1px规则线）

### 微交互动画

- `ink-reveal`: 标题从模糊到清晰的墨迹显现效果（blur 2px → 0 + translateY）
- `stampAppear`: 标签盖章式出现（scale 0.9 → 1 + translateY）
- `typeFade`: 正文打字机式淡入（translateY 8px → 0）

### PPTX 背景色

`ddd5c0`

---

## combo-13 {#combo-13}

**名称**: 东京夜色 Tokyo Night
**适用场景**: 技术分享、基础设施、DevOps、冷色调科技
**图表支持**: SVG 静态 + ECharts 交互
**微交互**: neon-glow, fade-up, stagger-list

### CSS 变量

```css
:root {
  --bg-primary: #1a1b26;
  --bg-secondary: #16161e;
  --bg-card: #24283b;
  --accent-1: #7aa2f7;
  --accent-2: #bb9af7;
  --accent-3: #7dcfff;
  --text-primary: #c0caf5;
  --text-secondary: #a9b1d6;
  --text-accent: #7aa2f7;
  --radius: 12px;
  --radius-lg: 20px;
  --chart-color-1: #7aa2f7;
  --chart-color-2: #bb9af7;
  --chart-color-3: #7dcfff;
  --chart-color-4: #9ece6a;
  --chart-color-5: #e0af68;
  --chart-color-6: #f7768e;
  --chart-text: #c0caf5;
  --chart-text-secondary: #a9b1d6;
  --chart-grid: rgba(192,202,245,.12);
  --chart-bg: transparent;
}
```

### 背景效果

1. **底部分隔线**: 渐变透明 → 蓝色 → 透明，1px 水平线

### 组件样式

- **卡片**: 深蓝灰底 + 低透明度边框 + hover 蓝色边框
- **标签**: 紫色下划线样式
- **步骤**: 紫色数字圆形 + 低透明度边框

### PPTX 背景色

`1a1b26`

---

## combo-14 {#combo-14}

**名称**: 德古拉暗夜 Dracula
**适用场景**: 代码密集型技术、开发者演讲、暗色主题爱好者
**图表支持**: SVG 静态 + ECharts 交互
**微交互**: neon-glow, glitch-in, fade-up

### CSS 变量

```css
:root {
  --bg-primary: #282a36;
  --bg-secondary: #21222c;
  --bg-card: #343746;
  --accent-1: #bd93f9;
  --accent-2: #ff79c6;
  --accent-3: #8be9fd;
  --text-primary: #f8f8f2;
  --text-secondary: #bdbde0;
  --text-accent: #bd93f9;
  --radius: 12px;
  --radius-lg: 18px;
  --chart-color-1: #bd93f9;
  --chart-color-2: #ff79c6;
  --chart-color-3: #8be9fd;
  --chart-color-4: #50fa7b;
  --chart-color-5: #f1fa8c;
  --chart-color-6: #ff5555;
  --chart-text: #f8f8f2;
  --chart-text-secondary: #bdbde0;
  --chart-grid: rgba(248,248,242,.12);
  --chart-bg: transparent;
}
```

### 背景效果

1. **底部分隔线**: 渐变透明 → 紫色 → 透明，1px 水平线

### 组件样式

- **卡片**: 深灰底 + 低透明度边框 + hover 紫色边框
- **标签**: 粉色下划线样式
- **步骤**: 紫色数字圆形

### PPTX 背景色

`282a36`

---

## combo-15 {#combo-15}

**名称**: 企业商务 Corporate Clean
**适用场景**: 董事会、B2B 销售、金融、保险
**图表支持**: SVG 静态 + ECharts 交互
**微交互**: count-up, fade-slide, underline-expand

### CSS 变量

```css
:root {
  --bg-primary: #ffffff;
  --bg-secondary: #f5f7fa;
  --bg-card: #ffffff;
  --accent-1: #0a2540;
  --accent-2: #1d4ed8;
  --accent-3: #64748b;
  --text-primary: #0a2540;
  --text-secondary: #425466;
  --text-accent: #1d4ed8;
  --radius: 6px;
  --radius-lg: 10px;
  --chart-color-1: #1d4ed8;
  --chart-color-2: #0a2540;
  --chart-color-3: #64748b;
  --chart-color-4: #0e9f6e;
  --chart-color-5: #d97706;
  --chart-color-6: #dc2626;
  --chart-text: #0a2540;
  --chart-text-secondary: #425466;
  --chart-grid: rgba(10,37,64,.1);
  --chart-bg: transparent;
}
```

### 背景效果

1. **底部分隔线**: 渐变透明 → 深蓝灰 → 透明，1px 水平线

### 组件样式

- **卡片**: 白底 + 深蓝灰边框 + hover 蓝色边框，小圆角（6px）
- **标签**: 蓝色下划线样式
- **步骤**: 蓝色数字圆形，字重 700

### PPTX 背景色

`ffffff`

---

## combo-16 {#combo-16}

**名称**: 融资路演 Pitch Deck VC
**适用场景**: 融资路演、创业推介、投资人会议、种子轮
**图表支持**: SVG 静态 + ECharts 交互
**微交互**: count-up, zoom-pop, gradient-flow

### CSS 变量

```css
:root {
  --bg-primary: #ffffff;
  --bg-secondary: #fafbfc;
  --bg-card: #ffffff;
  --accent-1: #0070f3;
  --accent-2: #7928ca;
  --accent-3: #ff4ecb;
  --text-primary: #0b0d12;
  --text-secondary: #4a5270;
  --text-accent: #0070f3;
  --radius: 14px;
  --radius-lg: 22px;
  --chart-color-1: #0070f3;
  --chart-color-2: #7928ca;
  --chart-color-3: #ff4ecb;
  --chart-color-4: #0cce6b;
  --chart-color-5: #f5a524;
  --chart-color-6: #ee0000;
  --chart-text: #0b0d12;
  --chart-text-secondary: #4a5270;
  --chart-grid: rgba(20,30,50,.1);
  --chart-bg: transparent;
}
```

### 背景效果

1. **底部渐变条**: 4px 蓝→紫渐变色条，大边距（120px）
2. **section-label 渐变文字**: 蓝→紫渐变背景裁切文字

### 组件样式

- **卡片**: 白底 + 浅灰边框 + hover 蓝色边框 + 阴影浮起
- **标签**: 蓝→紫渐变文字
- **步骤**: 蓝色数字圆形，字重 800
- **标题**: 超粗字重（800），负字间距（-0.035em）

### PPTX 背景色

`ffffff`

---

## combo-17 {#combo-17}

**名称**: 毛玻璃 Glassmorphism
**适用场景**: 苹果风格发布会、产品特性、现代设计、高端展示
**图表支持**: SVG 静态 + ECharts 交互
**微交互**: glass-tilt, glow-border, blur-in

### CSS 变量

```css
:root {
  --bg-primary: #0b1024;
  --bg-secondary: #0e1530;
  --bg-card: rgba(255,255,255,.06);
  --accent-1: #7dd3fc;
  --accent-2: #c084fc;
  --accent-3: #f0abfc;
  --text-primary: #f2f4ff;
  --text-secondary: #c3c8e6;
  --text-accent: #7dd3fc;
  --radius: 22px;
  --radius-lg: 30px;
  --chart-color-1: #7dd3fc;
  --chart-color-2: #c084fc;
  --chart-color-3: #f0abfc;
  --chart-color-4: #86efac;
  --chart-color-5: #fde68a;
  --chart-color-6: #fca5a5;
  --chart-text: #f2f4ff;
  --chart-text-secondary: #c3c8e6;
  --chart-grid: rgba(255,255,255,.12);
  --chart-bg: transparent;
}
```

### 背景效果

1. **三色径向渐变**: 蓝/紫/粉三个大尺寸径向渐变叠加在深蓝底色上
2. **底部分隔线**: 蓝→紫渐变透明线
3. **毛玻璃卡片**: backdrop-filter: blur(28px) saturate(180%) + 半透明边框

### 组件样式

- **卡片**: 毛玻璃效果（blur 28px + saturate 180%）+ 半透明白色边框 + hover 浮起
- **标签**: 天蓝色下划线样式
- **步骤**: 紫色数字圆形 + 毛玻璃效果
- **列表项**: 低透明度背景 + 毛玻璃效果

### PPTX 背景色

`0b1024`

---

## combo-18 {#combo-18}

**名称**: 极光渐变 Aurora
**适用场景**: 封面页、CTA 页、结尾页、视觉冲击
**图表支持**: SVG 静态 + ECharts 交互
**微交互**: blur-in, gradient-flow, shimmer-sweep

### CSS 变量

```css
:root {
  --bg-primary: #06091c;
  --bg-secondary: #0a1130;
  --bg-card: rgba(255,255,255,.05);
  --accent-1: #5ef2c6;
  --accent-2: #7aa2ff;
  --accent-3: #c984ff;
  --text-primary: #e8f0ff;
  --text-secondary: #b4c4e4;
  --text-accent: #5ef2c6;
  --radius: 20px;
  --radius-lg: 28px;
  --chart-color-1: #5ef2c6;
  --chart-color-2: #7aa2ff;
  --chart-color-3: #c984ff;
  --chart-color-4: #ffd27a;
  --chart-color-5: #ff8ab0;
  --chart-color-6: #a78bfa;
  --chart-text: #e8f0ff;
  --chart-text-secondary: #b4c4e4;
  --chart-grid: rgba(180,220,255,.14);
  --chart-bg: transparent;
}
```

### 背景效果

1. **极光三色径向渐变**: 绿/蓝/紫三个大尺寸径向渐变叠加在深蓝底色上
2. **底部分隔线**: 绿→蓝→紫渐变透明线
3. **毛玻璃卡片**: backdrop-filter: blur(24px) saturate(160%) + 半透明边框

### 组件样式

- **卡片**: 毛玻璃效果（blur 24px + saturate 160%）+ 半透明蓝白边框 + hover 浮起
- **标签**: 绿色下划线样式
- **步骤**: 蓝色数字圆形 + 毛玻璃效果
- **列表项**: 低透明度背景 + 毛玻璃效果

### PPTX 背景色

`06091c`
