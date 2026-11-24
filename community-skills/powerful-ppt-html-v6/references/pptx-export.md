# PPTX 导出指南

## 依赖

```bash
npm install playwright pptxgenjs adm-zip
npx playwright install chromium
```

## 脚本用法

```bash
node scripts/html-to-pptx.js <html文件路径> [--bg=背景色] [--title=标题]
```

示例:
```bash
# Neo-Brutalism 风格（浅色背景）
node scripts/html-to-pptx.js output/presentation.html --bg=fef9ef --title="我的演示"

# Retro-Futurism 风格（深色背景）
node scripts/html-to-pptx.js output/presentation.html --bg=0d0221 --title="我的演示"

# Keynote Dark 风格（纯黑背景）
node scripts/html-to-pptx.js output/presentation.html --bg=000000 --title="我的演示"
```

## 转换流程

```
HTML → Playwright 渲染(1280×720, 2x DPI)
→ 隐藏导航栏/编辑按钮/扫描线
→ 禁用所有 slide 的 CSS transition
→ 逐页激活幻灯片(visibility:hidden 隐藏非活跃页)
→ 等待 800ms 确保渲染完成
→ 截图为 JPEG 95%(2560×1440)
→ PptxGenJS 创建 16:9 画布(10" × 5.625")
→ 每页添加全屏背景图 + 背景色兜底
→ 提取文本写入备注栏
→ 生成 .pptx
```

## 关键参数

| 参数 | 值 | 说明 |
|------|-----|------|
| VIEWPORT_W | 1280 | 浏览器视口宽度 |
| VIEWPORT_H | 720 | 浏览器视口高度 |
| DPR | 2 | 设备像素比 |
| SLIDE_W | 10 | PPTX 宽度(英寸) |
| SLIDE_H | 5.625 | PPTX 高度(英寸) |
| JPEG_QUALITY | 95 | 截图质量 |
| 等待时间 | 800ms | 切换后等待渲染 |

## 各风格背景色对照

| 风格 | --bg-primary | --bg 参数 |
|------|-------------|-----------|
| combo-1 Neo-Brutalism | #fef9ef | fef9ef |
| combo-2 Retro-Futurism | #0d0221 | 0d0221 |
| combo-3 Maximalism | #0a0a0a | 0a0a0a |
| combo-4 Naive | #faf8f5 | faf8f5 |
| combo-5 Bento 3D Glass | #0f0f23 | 0f0f23 |
| combo-6 Neo-Minimalism | #ffffff | ffffff |
| combo-7 Memphis | #fffbe6 | fffbe6 |
| combo-8 Blueprint | #0a1628 | 0a1628 |
| combo-9 Keynote Dark | #000000 | 000000 |

## 已知限制

- dom-to-pptx 库不支持 clip-path、filter/blur、复杂 text-shadow
- 截图方案保证视觉 100% 保真，但文字不可编辑
- 文件大小取决于页数和图片质量（约 0.15-0.5 MB/页）
- 需要安装 Chromium（约 200MB）

## 截图虚影修复

转换脚本已内置以下修复：
1. 禁用所有 slide 的 CSS `transition`
2. 非活跃页使用 `visibility: hidden` 彻底隐藏
3. 切换后等待 800ms 再截图
4. 冻结 fade-in-up 动画到终态

## 导航栏残留修复

HTML 模板已内置导航栏 auto-hide：
- 默认 `opacity: 0` 隐藏
- 交互时添加 `.visible` 类显示
- 3 秒无操作后自动隐藏
- 转换脚本会 `display: none` 彻底移除
