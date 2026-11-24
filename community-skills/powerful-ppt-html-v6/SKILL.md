---
name: powerful-ppt-html-v6
description: "Generate stunning HTML presentations with 18 visual styles, 27 CSS animations + 20 Canvas FX, 31 layout templates, 33 chart templates (SVG + ECharts), 6700+ icons, smart animation recommendations, multi-format input (PDF/DOCX/Web/PPT), AI image generation, and export to PPTX. Use when users need to: (1) Create presentations from video scripts, markdown, PDF, DOCX, PPT, web pages, or text content, (2) Generate HTML slideshows with specific visual styles and animations, (3) Export presentations to PPTX format, (4) Build interactive presentations with browser editing, (5) Generate AI images for slides. Triggers: 'create presentation', 'make slides', 'generate PPT', 'PPTX', 'HTML presentation', '视频脚本转PPT', '做演示文稿', '生成幻灯片'."
---

# PowerfulPPT — HTML Presentation Generator

Generate single-file HTML presentations from text/video scripts with 18 visual styles, 27 CSS animations + 20 Canvas FX, 31 layout templates, 33 chart templates (SVG static + ECharts interactive), 6700+ icons, smart animation recommendations, multi-format input, AI image generation, and PPTX export.

## Workflow

```
Input → Step 1: Mode Detection → Step 2: Discover Styles → Step 3: Design Planning (BLOCKING) → Step 4: Preview → Step 5: HTML Generation → Step 6: Delivery → Step 7: PPTX Export (optional)
```

### Step 1: Mode Detection & Input Analysis

**Mode A** (default): New presentation from Markdown/text/video script.
- Analyze: topic, audience, structure (segments → slides), key data, key concepts
- Estimate slide count: ~1.2-1.5 slides per content segment

**Mode B**: Edit existing HTML presentation.
- Read existing file, apply modifications, preserve style.

**Mode C**: New presentation from external source.
- PDF: `python scripts/source_to_md/pdf_to_md.py <input>`
- DOCX/EPUB/HTML/LaTeX: `python scripts/source_to_md/doc_to_md.py <input>`
- Web page: `python scripts/source_to_md/web_to_md.py <url>` (or `node scripts/source_to_md/web_to_md.cjs <url>` for WeChat/high-security sites)
- PPTX: `python scripts/source_to_md/ppt_to_md.py <input>`
- Then proceed as Mode A with the converted Markdown

### Step 2: Discover Available Styles

**CRITICAL: Read styles dynamically, do NOT use hardcoded list!**

1. Read `templates/styles/styles_index.json` to get all available styles
2. For each style, read its `config.json` to get detailed info
3. Build the style selection list dynamically

**Style categories from styles_index.json**:
- `categories.light`: Light-themed styles
- `categories.dark`: Dark-themed styles
- `quickLookup.tech`: Tech-oriented styles
- `quickLookup.business`: Business-oriented styles
- `quickLookup.creative`: Creative styles
- `quickLookup.education`: Education styles

**Each style has**:
- `id`: Style identifier (e.g., "combo-12")
- `name`: English name
- `name_cn`: Chinese name
- `best_for`: Use case tags
- `theme`: "light" or "dark"
- `pptx_bg`: Background color for PPTX export
- `preview`: Path to preview image
- `config`: Path to config.json

### Step 3: Design Planning (BLOCKING — ask user)

Use AskUserQuestion with these choices:

**Style selection**: Dynamically build from styles_index.json, group by theme (light/dark). Show format:
| ID | Name | Best For | Theme |
|----|------|----------|-------|
| combo-N | Name (中文名) | Use cases | light/dark |

**Animation level**: Auto (smart recommendations from animations_index.json) | Full (all CSS animations + Canvas FX) | Minimal (fade-in-up only) | None

**Layout selection**: When content structure is clear, select from 31 layout templates (see Layout Templates below). Auto (smart mapping from layouts_index.json) | Manual selection | Default 7-type mapping

**Chart selection**: When content contains data/comparison/analysis, select from 33 chart types (see Chart Templates below). SVG static (recommended, zero-dependency) | ECharts interactive (any style, needs CDN) | None

**Icon selection**: When slides need icons, select from 3 icon libraries (see Icon Library below).

**Editing**: Enable browser inline editing (contentEditable + localStorage) | Read-only

**Aspect ratio**: 16:9 (default) | 4:3

### Step 4: ASCII Preview

Show slide structure preview:
```
┌─────────────────────────┐
│  P01  Cover             │
│  P02  Problem Statement │
│  P03  Key Points        │
│  ...                    │
│  P0N  Ending            │
└─────────────────────────┘
```

### Step 5: HTML Generation

Read the selected style's files from `templates/styles/`:
1. Read `templates/styles/{style-folder}/config.json` for CSS variables and metadata
2. Read `templates/styles/{style-folder}/base.css` for base styles
3. Read `templates/styles/{style-folder}/effects.css` for background effects
4. Read `templates/styles/{style-folder}/components.css` for component styles
5. Optionally read `templates/styles/{style-folder}/preview.png` for visual reference

Read [references/html-generation.md](references/html-generation.md) for HTML structure, slide types, navigation, and editing implementation.

For chart slides:
- **SVG static charts**: Read the chart SVG from `templates/charts/{chart_key}.svg` and adapt colors using the chart CSS variables defined in the style's config.json. Query `templates/charts/charts_index.json` to find the right chart type. See `templates/charts/chart_color_map.json` for the complete color mapping reference.
- **ECharts interactive charts**: Read `templates/charts/echarts_templates.json` for option templates. Resolve CSS variables to hex values from the style's config.json before generating ECharts option. Include ECharts CDN in the HTML.

**Generate a single-file HTML** with:
1. CSS variables from selected style's config.json (including chart variables)
2. Style-specific background effects (from effects.css)
3. Content mapped to 7 slide types (Cover/Content/Cards/Steps/Chart/List/Ending) or 31 layout templates
4. Navigation system (keyboard + touch + scroll + dots)
5. Optional contentEditable editing with localStorage
6. CSS animations from `templates/animations/animations.css` (27 classes) — apply based on animation level
7. Canvas FX from `templates/animations/fx/` (20 effects) — apply `data-fx="effect-name"` attribute on slide containers, include `fx-runtime.js` + `_util.js` + specific FX modules
8. Smart animation recommendations from `templates/animations/animations_index.json` (slide_type_mapping, style_theme_mapping, content_type_mapping)
9. prefers-reduced-motion and responsive (768px breakpoint)
10. Icons from `templates/icons/` where needed

**Critical**: Navigation bar must auto-hide (opacity:0 by default, show on interaction, hide after 3s). This prevents residual text in PPTX export.

### Step 5: Delivery

- Write HTML file to output directory
- Start local server for preview
- Report: file path, page count, style, features

### Step 6: PPTX Export (optional)

Run `scripts/html-to-pptx.js`:
```bash
node scripts/html-to-pptx.js <html-path> --bg=<bgcolor> --title=<title>
```

Read [references/pptx-export.md](references/pptx-export.md) for export details, background colors per style, and troubleshooting.

**Prerequisites**: `npm install playwright pptxgenjs adm-zip && npx playwright install chromium`

### Step 7: AI Image Generation (optional)

When slides need custom images, use `scripts/image_gen.py`:
```bash
python scripts/image_gen.py "prompt" --aspect_ratio 16:9 -o images/
```

Configure backend in `.env`:
```
IMAGE_BACKEND=openai
OPENAI_API_KEY=your-key
```

Supported backends: gemini, openai, qwen, zhipu, volcengine, stability, bfl, ideogram, siliconflow, fal, replicate. Run `python scripts/image_gen.py --list-backends` for details.

## Style Quick Reference

| Style | bg-primary | --bg param | Key Visual |
|-------|-----------|------------|------------|
| 1 Neo-Brutalism | #fef9ef | fef9ef | Bold borders + hard shadows |
| 2 Retro-Futurism | #0d0221 | 0d0221 | Scanlines + neon glow |
| 3 Maximalism | #0a0a0a | 0a0a0a | Oversized type + color blocks |
| 4 Naive | #faf8f5 | faf8f5 | Hand-drawn + soft corners |
| 5 Bento Glass | #0f0f23 | 0f0f23 | Glassmorphism + grid layout |
| 6 Neo-Minimalism | #ffffff | ffffff | Thin lines + whitespace |
| 7 Memphis | #fffbe6 | fffbe6 | Geometric patterns + bright colors |
| 8 Blueprint | #0a1628 | 0a1628 | Grid lines + dashed borders |
| 9 Keynote Dark | #000000 | 000000 | Floating orbs + ECharts |
| 10-12 | (see styles_index.json) | | |
| 13 Tokyo Night | #1a1b26 | 1a1b26 | Blue-purple accent + dark tech |
| 14 Dracula | #282a36 | 282a36 | Purple-pink accent + dev favorite |
| 15 Corporate Clean | #ffffff | ffffff | Navy blue + formal business |
| 16 Pitch Deck VC | #ffffff | ffffff | Gradient accent + startup pitch |
| 17 Glassmorphism | #0b1024 | 0b1024 | Frosted glass + blur backdrop |
| 18 Aurora | #06091c | 06091c | Aurora gradient + cosmic glow |

## Animation System

27 CSS animation classes + 20 Canvas FX effects. Query `templates/animations/animations_index.json` for full metadata and smart recommendations.

### CSS Animations (27 classes)

Apply via class names on elements. All respect `prefers-reduced-motion`.

**Directional Fades**: `anim-fade-up`, `anim-fade-down`, `anim-fade-left`, `anim-fade-right`

**Dramatic Entries**: `anim-rise-in`, `anim-drop-in`, `anim-zoom-pop`, `anim-blur-in`, `anim-glitch-in`

**Text Effects**: `anim-typewriter`, `anim-neon-glow`, `anim-shimmer-sweep`, `anim-gradient-flow`

**Lists & Numbers**: `anim-stagger-list` (on parent, children animate one-by-one), `counter` + `data-to` (number ticks 0→target)

**SVG Geometry**: `anim-path-draw` (strokes draw themselves), `anim-morph-shape` (path d morph)

**3D Perspective**: `anim-parallax-tilt` (hover 3D tilt), `anim-card-flip-3d`, `anim-cube-rotate-3d`, `anim-page-turn-3d`, `anim-perspective-zoom`

**Ambient**: `anim-marquee-scroll`, `anim-kenburns`, `anim-confetti-burst`, `anim-spotlight`, `anim-ripple-reveal`

### Canvas FX (20 effects)

Apply via `data-fx="effect-name"` attribute on slide or container elements. Include `fx-runtime.js` in HTML to auto-initialize.

**Celebration**: `particle-burst`, `confetti-cannon`, `firework`

**Space/Sci-Fi**: `starfield`, `galaxy-swirl`, `orbit-ring`

**Tech/Data**: `matrix-rain`, `data-stream`, `knowledge-graph`, `neural-net`

**Ambient/Decorative**: `constellation`, `gradient-blob`, `magnetic-field`

**Text/Interactive**: `word-cascade`, `letter-explode`, `typewriter-multi`, `counter-explosion`

**Impact/Flow**: `chain-react`, `shockwave`, `sparkle-trail`

### Smart Animation Recommendations

`animations_index.json` provides 3 mapping tables for AI-driven animation selection:

**slide_type_mapping**: Maps slide types (cover, content, cards, steps, chart, list, ending, quote, comparison, timeline, section-divider, kpi) to recommended CSS animations and Canvas FX.

**style_theme_mapping**: Maps style themes (dark_tech, dark_premium, light_minimal, light_creative, light_business, cyberpunk) to matching FX and CSS animations.

**content_type_mapping**: Maps content types (data_metrics, architecture, process_flow, celebration, storytelling) to appropriate animations.

**Usage**: When animation level is "Auto", query these 3 tables and merge recommendations. Prioritize: content_type > slide_type > style_theme.

### HTML Integration

```html
<!-- In <head> -->
<link rel="stylesheet" href="animations.css">

<!-- In <body>, before </body> -->
<script src="fx/_util.js"></script>
<script src="fx-runtime.js"></script>

<!-- On slides -->
<div class="slide active anim-blur-in" data-fx="constellation">
  <h1 class="anim-rise-in">Title</h1>
  <ul class="anim-stagger-list">...</ul>
</div>
```

## Layout Templates

31 layout templates for diverse content structures. Query `templates/layouts/layouts_index.json` for full metadata.

### Categories

| Category | Layouts |
|----------|---------|
| Openers & Transitions | cover, toc, section-divider |
| Text-Centric | bullets, two-column, three-column, big-quote |
| Numbers & Data | stat-highlight, kpi-grid, table, chart-bar, chart-line, chart-pie, chart-radar |
| Code & Terminal | code, diff, terminal |
| Diagrams & Flows | flow-diagram, arch-diagram, process-steps, mindmap |
| Plans & Comparisons | timeline, roadmap, gantt, comparison, pros-cons, todo-checklist |
| Visuals | image-hero, image-grid |
| Closers | cta, thanks |

### Picking Guide

- **Opener**: cover → toc
- **Section break**: section-divider before every major section
- **Core content**: bullets, two-column, three-column
- **Show numbers**: stat-highlight (single) or kpi-grid (4-up)
- **Show plot**: chart-bar / chart-line / chart-pie / chart-radar
- **Show diff**: comparison, diff, pros-cons
- **Show plan**: timeline, roadmap, gantt, process-steps
- **Show architecture**: arch-diagram, flow-diagram, mindmap
- **Code demo**: code, terminal
- **Closer**: cta → thanks

### Layout-to-Slide-Type Mapping

| Layout | Compatible Slide Type |
|--------|----------------------|
| cover | cover |
| toc, bullets, big-quote, table, code, diff, terminal, flow-diagram, arch-diagram, mindmap, timeline, comparison, pros-cons, todo-checklist, image-hero | content |
| three-column, kpi-grid, image-grid, roadmap | cards |
| process-steps | steps |
| stat-highlight, chart-bar, chart-line, chart-pie, chart-radar, gantt | chart |
| section-divider | content |
| cta | ending, content |
| thanks | ending |

## Chart Templates

33 chart types available in `templates/charts/`. Query `templates/charts/charts_index.json` for full metadata.

### Comparison Charts
| Chart | File | Best For |
|-------|------|----------|
| Bar Chart | bar_chart.svg | 3-8 category comparison |
| Horizontal Bar | horizontal_bar_chart.svg | 5-12 item ranking |
| Grouped Bar | grouped_bar_chart.svg | 2-4 series comparison |
| Stacked Bar | stacked_bar_chart.svg | Part-to-whole comparison |
| Butterfly | butterfly_chart.svg | Bidirectional comparison |
| Dumbbell | dumbbell_chart.svg | Before-after comparison |
| Waterfall | waterfall_chart.svg | Incremental change breakdown |
| Bullet | bullet_chart.svg | Target vs actual performance |

### Trend Charts
| Chart | File | Best For |
|-------|------|----------|
| Line Chart | line_chart.svg | Time trend, 1-3 series |
| Area Chart | area_chart.svg | Cumulative trend visualization |
| Stacked Area | stacked_area_chart.svg | Composition trends over time |
| Dual-Axis Line | dual_axis_line_chart.svg | Two metrics with different scales |

### Composition Charts
| Chart | File | Best For |
|-------|------|----------|
| Pie Chart | pie_chart.svg | 3-6 part proportions |
| Donut Chart | donut_chart.svg | Composition with center emphasis |
| Treemap | treemap_chart.svg | Hierarchical proportion display |

### Metrics Charts
| Chart | File | Best For |
|-------|------|----------|
| KPI Cards | kpi_cards.svg | 2x2 metrics overview |
| Gauge Chart | gauge_chart.svg | Single-metric achievement |
| Progress Bar | progress_bar_chart.svg | Multiple metric completion |

### Analysis Charts
| Chart | File | Best For |
|-------|------|----------|
| Radar Chart | radar_chart.svg | 4-8 dimension assessment |
| Scatter Plot | scatter_chart.svg | Correlation analysis |
| Bubble Chart | bubble_chart.svg | 3-dimension correlation |
| Heatmap | heatmap_chart.svg | 2D intensity patterns |
| Box Plot | box_plot_chart.svg | Statistical distribution |
| Pareto Chart | pareto_chart.svg | 80/20 rule analysis |
| Sankey Diagram | sankey_chart.svg | Flow and resource allocation |
| Funnel Chart | funnel_chart.svg | 3-5 stage conversion |
| 2x2 Matrix | matrix_2x2.svg | Dual-dimension positioning |

### Process & Strategy Charts
| Chart | File | Best For |
|-------|------|----------|
| Timeline | timeline.svg | 3-8 milestones |
| Process Flow | process_flow.svg | 3-8 step sequence |
| Gantt Chart | gantt_chart.svg | 6-12 task scheduling |
| Org Chart | org_chart.svg | Hierarchical structure |
| SWOT Analysis | swot_analysis.svg | Strategic 4-quadrant |
| Porter's Five Forces | porter_five_forces.svg | Industry competition analysis |

### ECharts Interactive Charts

For interactive charts with animations, tooltips, and zoom, use ECharts templates from `templates/charts/echarts_templates.json`. 20 chart types have ECharts option templates.

**Usage**:
1. Read `echarts_templates.json` and select the chart template
2. Resolve CSS variables to hex values from the style's config.json
3. Customize option with actual data
4. Include ECharts CDN: `https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js`
5. Add chart container and initialization script to the slide

**Note**: ECharts charts work with all styles, not just combo-9. They render correctly in PPTX export since Playwright executes JavaScript.

**Chart color adaptation**: Each style defines 10 chart CSS variables (`--chart-color-1` through `--chart-color-6`, `--chart-text`, `--chart-text-secondary`, `--chart-grid`, `--chart-bg`). When embedding chart SVG in HTML, replace default colors with these variables. For ECharts, resolve CSS variables to hex values at generation time. See `templates/charts/chart_color_map.json` for the complete mapping reference.

## Icon Library

3 icon libraries available in `templates/icons/`:

| Library | Count | Style | Best For |
|---------|-------|-------|----------|
| tabler-outline | 5039 | Stroke-based, clean | Professional, tech, general |
| tabler-filled | 1053 | Solid fill | Emphasis, status, badges |
| chunk | 640 | Simplified geometric | Creative, playful, modern |

**Usage**: Read SVG file content and embed inline in HTML. Apply `fill="currentColor"` or `fill="var(--text-primary)"` to adapt to the selected style.

**Common icons**: arrow-right, check, x, chevron-right, chevron-down, circle-check, alert-triangle, info-circle, chart-bar, chart-line, users, target, rocket, lightbulb, settings, star, heart, bookmark, download, share

## Content Mapping Rules

- Video script segments → 1.2-1.5 slides per segment
- Opening → Cover slide
- Problem/Context → Content or List slide
- Data/Comparison → Chart slide (select from 33 chart types based on data nature)
- Steps/Process → Steps slide with numbered items
- Key points → Cards slide (2-4 per row)
- Summary/Takeaway → Content slide with emphasis
- Closing → Ending slide with author

**Chart selection guide**:
- Category comparison → bar_chart, horizontal_bar_chart, grouped_bar_chart, stacked_bar_chart
- Bidirectional comparison → butterfly_chart, dumbbell_chart
- Proportion/composition → pie_chart, donut_chart, treemap_chart
- Time trend → line_chart, area_chart, stacked_area_chart, dual_axis_line_chart
- Multi-dimensional → radar_chart, scatter_chart, bubble_chart
- Key metrics → kpi_cards, gauge_chart, progress_bar_chart, bullet_chart
- Milestones → timeline
- Process → process_flow
- Strategy → swot_analysis, porter_five_forces, matrix_2x2
- Conversion → funnel_chart, waterfall_chart, sankey_chart
- Scheduling → gantt_chart
- Positioning → matrix_2x2, bubble_chart
- Distribution → box_plot_chart, scatter_chart, heatmap_chart
- Hierarchy → treemap_chart, org_chart, sankey_chart
- Performance → bullet_chart, gauge_chart, progress_bar_chart

## Template Management

### Style Templates (`templates/styles/`)

Each style is an independent folder:
```
templates/styles/combo-{n}-{name}/
├── config.json         # Metadata + CSS variables (required)
├── base.css            # Base styles, layout, fonts (required)
├── effects.css         # Background effects, animations (optional)
├── components.css      # Component styles (required)
└── preview.png         # Preview image (auto-generated)
```

**Add new style**: Copy existing folder → modify config.json + CSS files → run `python scripts/sync_styles_index.py` → run `node scripts/generate_previews.js`

**Update style**: Edit files in the style folder → if config.json changed, run sync script → delete preview.png and regenerate

**Delete style**: Remove folder → run sync script

**Index file**: `templates/styles/styles_index.json` is auto-generated by sync script. Do NOT edit manually.

**Preview images**: `preview.png` files are auto-generated by `scripts/generate_previews.js`. Do NOT edit manually.

### Chart Templates (`templates/charts/`)

SVG chart files with `charts_index.json` index, `chart_color_map.json` color mapping reference, and `echarts_templates.json` interactive chart templates. Add new charts by placing SVG files and updating the index.

### Icon Library (`templates/icons/`)

SVG icon files organized by style (tabler-outline, tabler-filled, chunk). Use icon name to find the SVG file (e.g., `arrow-right` → `templates/icons/tabler-outline/arrow-right.svg`).

## Resources

### scripts/
- `html-to-pptx.js` — Playwright + PptxGenJS converter. Takes HTML path, outputs PPTX with full-bleed slides.
- `generate_previews.js` — Generate preview.png for each style using Playwright screenshot.
- `sync_styles_index.py` — Scans style folders, validates config.json, generates styles_index.json.
- `source_to_md/pdf_to_md.py` — PDF to Markdown converter (PyMuPDF). Supports heading detection, table extraction, image extraction, header/footer removal.
- `source_to_md/doc_to_md.py` — DOCX/EPUB/HTML/LaTeX to Markdown converter (Pandoc-based). Supports 10+ input formats.
- `source_to_md/web_to_md.py` — Web page to Markdown converter (requests + BeautifulSoup). Supports image download, metadata extraction, Chinese CMS content detection.
- `source_to_md/web_to_md.cjs` — Web page to Markdown converter (Node.js). For WeChat/high-security sites that block Python requests.
- `source_to_md/ppt_to_md.py` — PowerPoint (PPTX) to Markdown converter (python-pptx). Supports text, tables, notes extraction.
- `image_gen.py` — Unified AI image generation tool. 11 backends (gemini, openai, qwen, zhipu, volcengine, stability, bfl, ideogram, siliconflow, fal, replicate).
- `image_backends/` — Backend modules for image_gen.py.

### templates/
- `styles/` — 18 visual style templates (folder-based, each with config.json + CSS + preview.png)
- `styles/styles_index.json` — Auto-generated style index (categories, quickLookup, metadata)
- `animations/` — Animation system (27 CSS animations + 20 Canvas FX)
- `animations/animations.css` — CSS animation classes (directional fades, dramatic entries, text effects, 3D perspective, ambient)
- `animations/animations_index.json` — Animation metadata + smart recommendations (slide_type_mapping, style_theme_mapping, content_type_mapping)
- `animations/fx-runtime.js` — Canvas FX runtime loader (auto-detects data-fx attributes, manages lifecycle)
- `animations/fx/_util.js` — FX utility library (canvas setup, color extraction, animation loop)
- `animations/fx/` — 20 Canvas FX modules (particle-burst, confetti-cannon, firework, starfield, galaxy-swirl, orbit-ring, matrix-rain, data-stream, knowledge-graph, neural-net, constellation, gradient-blob, magnetic-field, word-cascade, letter-explode, chain-react, shockwave, sparkle-trail, typewriter-multi, counter-explosion)
- `layouts/` — 31 layout templates
- `layouts/layouts_index.json` — Layout metadata index (8 categories, picking guide, slide-type mapping)
- `charts/` — 33 chart SVG templates
- `charts/charts_index.json` — Chart metadata index (7 categories, 17 quickLookup keys, usage guide)
- `charts/chart_color_map.json` — Chart color to CSS variable mapping reference
- `charts/echarts_templates.json` — ECharts interactive chart option templates (20 types)
- `icons/tabler-outline/` — 5039 outline-style icons
- `icons/tabler-filled/` — 1053 filled-style icons
- `icons/chunk/` — 640 chunk-style icons

### references/
- `style-registry.md` — Complete CSS variables, effects, and component specs for all 18 styles (reference document)
- `html-generation.md` — HTML structure, 7 slide types, navigation system, editing, SVG chart templates, ECharts, icons, animation integration
- `pptx-export.md` — Export guide, background colors, troubleshooting, known limitations