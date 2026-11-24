---
name: keynote-ppt-generator-v4
description: 将Markdown/文本内容转换为乔布斯风格HTML演示文稿（v4.0版本）。生成单文件HTML应用，支持ECharts数据可视化、流畅动画、键盘/触摸导航、浮动光斑背景、底部进度条、淡入淡出页面切换效果。当用户需要：(1) 创建演示文稿/幻灯片/PPT，(2) 将报告转换为可视化演示，(3) 制作数据可视化展示，(4) 生成Keynote风格HTML演示，(5) 优化PPT页面切换效果时使用此Skill。
---

# Keynote PPT Generator v4.0

将Markdown或文本内容转换为精美的乔布斯风格HTML演示文稿。

## 工作流程

1. **分析内容结构** - 识别标题层级、列表、数据表格等元素
2. **规划幻灯片** - 根据内容类型选择合适的幻灯片模板
3. **生成HTML** - 基于模板生成单文件HTML应用
4. **配置图表** - 为数据内容配置ECharts可视化

## 核心特性

- 纯黑背景 + 多层径向渐变
- 三个浮动光斑动画（紫/粉/青）
- 底部进度条
- 响应式设计（桌面/移动端）
- 键盘/触摸/鼠标导航
- **淡入淡出页面切换效果（0.8s ease）**

## 切换效果（v4.0优化）

页面切换采用渐隐+上下移动效果，前一页渐隐下移，后一页渐显上移：

```css
.slide {
    opacity: 0;
    visibility: hidden;
    transform: translateY(-30px);
    transition: opacity 0.6s ease, transform 0.6s ease, visibility 0.6s ease;
}

.slide.active {
    opacity: 1;
    visibility: visible;
    transform: translateY(0);
}

.slide.exiting {
    opacity: 0;
    visibility: hidden;
    transform: translateY(30px);
}
```

切换时自动重置元素动画，确保每次进入页面动画都能播放：

```javascript
function goToSlide(index) {
    if (index === currentSlide) return;
    
    const prevSlide = slides[currentSlide];
    const nextSlideEl = slides[index];
    
    prevSlide.classList.remove('active');
    prevSlide.classList.add('exiting');
    navDots[currentSlide].classList.remove('active');
    
    currentSlide = index;
    
    setTimeout(() => {
        prevSlide.classList.remove('exiting');
    }, 600);
    
    nextSlideEl.classList.add('active');
    navDots[currentSlide].classList.add('active');
    updateProgress();
    
    const animatedElements = nextSlideEl.querySelectorAll('.fade-in-up');
    animatedElements.forEach(el => {
        el.style.animation = 'none';
        el.offsetHeight;
        el.style.animation = null;
    });
}
```

## 幻灯片类型

### 1. 封面页 (Cover)

```html
<div class="slide active" data-slide="0">
    <p class="text-sm tracking-widest text-gray-500 mb-6 uppercase fade-in-up">副标题</p>
    <h1 class="hero-title fade-in-up delay-1">主标题</h1>
    <p class="subtitle fade-in-up delay-2">描述文字</p>
    <div class="fade-in-up delay-3 mt-12 flex gap-4 flex-wrap justify-center">
        <span class="tag tag-primary">标签1</span>
        <span class="tag tag-secondary">标签2</span>
    </div>
</div>
```

### 2. 内容页 (Content)

```html
<div class="slide" data-slide="n">
    <p class="text-sm tracking-widest text-gray-500 mb-6 uppercase fade-in-up">章节标签</p>
    <h2 class="section-title fade-in-up delay-1">章节标题</h2>
    <p class="subtitle fade-in-up delay-2">内容描述<span class="highlight">重点文字</span></p>
</div>
```

### 3. 图表页 (Chart)

支持ECharts图表类型，详见 [chart-configs.md](references/chart-configs.md)

### 4. 流程页 (Process)

```html
<div class="process-flow fade-in-up delay-3 mt-8">
    <div class="card process-step wave">
        <svg class="icon-large" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <!-- SVG图标 -->
        </svg>
        <p class="text-lg font-bold">步骤名</p>
        <p class="text-sm text-gray-400">描述</p>
    </div>
    <svg class="process-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M5 12h14M12 5l7 7-7 7" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>
    <!-- 更多步骤... -->
</div>
```

### 5. 卡片页 (Cards)

```html
<div class="stat-grid fade-in-up delay-3 mt-8">
    <div class="card stat-card wave">
        <p class="big-number">数据</p>
        <p class="text-gray-400 mt-2">标签</p>
    </div>
    <!-- 更多卡片... -->
</div>
```

### 6. 列表页 (List)

```html
<div class="card">
    <h3 class="text-xl font-bold mb-4 text-blue-400">标题</h3>
    <ul class="feature-list">
        <li>列表项<span class="highlight">重点</span></li>
        <!-- 更多列表项... -->
    </ul>
</div>
```

### 7. 时间线页 (Timeline)

```html
<div class="timeline fade-in-up delay-3 mt-8">
    <div class="timeline-item">
        <div class="timeline-marker">1</div>
        <div class="timeline-content card">
            <p class="font-bold text-lg">标题</p>
            <p class="text-gray-400 mt-2">描述</p>
        </div>
    </div>
    <!-- 更多时间线项... -->
</div>
```

## 设计约束

### 颜色系统

```css
--color-primary: #60a5fa;    /* 主色调：蓝色 */
--color-secondary: #a78bfa;  /* 次要色：紫色 */
--color-accent: #f093fb;     /* 强调色：粉色 */
--color-success: #34d399;    /* 成功色：绿色 */
--color-warning: #fbbf24;    /* 警告色：黄色 */
--color-danger: #f87171;     /* 危险色：红色 */
```

### 动画约束

- 浮动幅度：≤5px (wave动画)
- 脉冲幅度：≤1.02倍 (pulse动画)
- 动画时长：1-3秒
- 延迟间隔：100-500ms
- 页面切换时长：0.8s ease（淡入淡出）

### 布局约束

- 卡片圆角：24px
- 内边距：40px(桌面) / 30px(移动端)
- 图表高度：450px(桌面) / 350px(移动端)
- 字体大小：使用clamp()实现响应式

## CDN依赖

```html
<script src="https://cdn.tailwindcss.com"></script>
<script src="https://unpkg.com/echarts@5.4.3/dist/echarts.min.js"></script>
<script>
    if (typeof echarts === 'undefined') {
        var script = document.createElement('script');
        script.src = 'https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js';
        document.head.appendChild(script);
    }
</script>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@100;200;300;400;500;600;700;800;900&display=swap" rel="stylesheet">
```

## 导航系统

### 键盘导航

- `→` / `空格`：下一页
- `←`：上一页
- `Home`：首页
- `End`：末页

### 触摸导航

- 左右滑动切换页面

### 鼠标导航

- 滚轮上下切换
- 点击底部导航点跳转

## 模板文件

使用 [ppt-template.html](assets/ppt-template.html) 作为基础模板，包含：
- 完整的CSS样式系统
- 背景动画效果（浮动光斑）
- 导航组件
- 进度条
- 图表初始化框架
- **淡入淡出切换效果**
- **切换时动画自动重置**

## 图表配置

详细的ECharts配置请参考 [chart-configs.md](references/chart-configs.md)，包含：
- 折线图配置
- 柱状图配置
- 仪表盘配置
- 饼图配置
- 热点图配置
- 雷达图配置

## 高亮样式

```html
<span class="highlight">蓝色高亮</span>
<span class="highlight-accent">粉色高亮</span>
<span class="highlight-success">绿色高亮</span>
<span class="highlight-warning">黄色高亮</span>
```

## 标签样式

```html
<span class="tag tag-primary">蓝色标签</span>
<span class="tag tag-secondary">紫色标签</span>
<span class="tag tag-accent">粉色标签</span>
<span class="tag tag-success">绿色标签</span>
```