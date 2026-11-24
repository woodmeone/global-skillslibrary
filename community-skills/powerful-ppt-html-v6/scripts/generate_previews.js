const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

const VIEWPORT_W = 1280;
const VIEWPORT_H = 720;
const DPR = 2;

const STYLES_DIR = path.resolve(__dirname, '..', 'templates', 'styles');

const STYLE_FOLDERS = fs.readdirSync(STYLES_DIR).filter(f => {
  const p = path.join(STYLES_DIR, f);
  return fs.statSync(p).isDirectory() && fs.existsSync(path.join(p, 'config.json'));
});

function generatePreviewHTML(config, baseCSS, effectsCSS, componentsCSS) {
  const vars = Object.entries(config.css_variables)
    .map(([k, v]) => `  ${k}: ${v};`)
    .join('\n');

  return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=1280">
<style>
:root {
${vars}
}
${baseCSS}
${effectsCSS}
${componentsCSS}
.slide { opacity: 1 !important; transform: none !important; visibility: visible !important; pointer-events: auto !important; }
.fade-in-up { animation: none !important; opacity: 1 !important; transform: none !important; }
.preview-container { width: ${VIEWPORT_W}px; height: ${VIEWPORT_H}px; overflow: hidden; }
</style>
</head>
<body>
<div class="presentation">
<div class="slide active preview-container">
  <div class="section-label">PREVIEW</div>
  <div class="hero-title">${config.name}</div>
  <div class="hero-subtitle">${config.name_cn} — ${config.best_for.join(' / ')}</div>
  <div style="margin-top: 32px; display: flex; gap: 12px; flex-wrap: wrap;">
    <span class="hero-tag tag-red">Style ${config.id}</span>
    <span class="hero-tag tag-blue">${config.theme}</span>
    <span class="hero-tag tag-yellow">${config.chart_support}</span>
  </div>
  <div class="card-grid" style="margin-top: 32px;">
    <div class="brutal-card card-red">
      <div style="font-weight: 900; font-size: 1.2rem;">Card A</div>
      <div style="color: var(--text-secondary); margin-top: 8px;">Sample card component</div>
    </div>
    <div class="brutal-card card-blue">
      <div style="font-weight: 900; font-size: 1.2rem;">Card B</div>
      <div style="color: var(--text-secondary); margin-top: 8px;">Sample card component</div>
    </div>
    <div class="brutal-card card-green">
      <div style="font-weight: 900; font-size: 1.2rem;">Card C</div>
      <div style="color: var(--text-secondary); margin-top: 8px;">Sample card component</div>
    </div>
  </div>
</div>
</div>
</body>
</html>`;
}

async function generatePreviews() {
  console.log(`Found ${STYLE_FOLDERS.length} styles to preview\n`);

  const browser = await chromium.launch({ headless: true });

  for (const folder of STYLE_FOLDERS) {
    const styleDir = path.join(STYLES_DIR, folder);
    const configPath = path.join(styleDir, 'config.json');
    const outputPath = path.join(styleDir, 'preview.png');

    if (fs.existsSync(outputPath)) {
      console.log(`  [skip] ${folder} — preview.png already exists`);
      continue;
    }

    console.log(`[Generating] ${folder}...`);

    const config = JSON.parse(fs.readFileSync(configPath, 'utf-8'));
    const baseCSS = fs.existsSync(path.join(styleDir, 'base.css'))
      ? fs.readFileSync(path.join(styleDir, 'base.css'), 'utf-8') : '';
    const effectsCSS = fs.existsSync(path.join(styleDir, 'effects.css'))
      ? fs.readFileSync(path.join(styleDir, 'effects.css'), 'utf-8') : '';
    const componentsCSS = fs.existsSync(path.join(styleDir, 'components.css'))
      ? fs.readFileSync(path.join(styleDir, 'components.css'), 'utf-8') : '';

    const html = generatePreviewHTML(config, baseCSS, effectsCSS, componentsCSS);
    const tmpHtml = path.join(styleDir, '_preview_tmp.html');
    fs.writeFileSync(tmpHtml, html, 'utf-8');

    const page = await browser.newPage({
      viewport: { width: VIEWPORT_W, height: VIEWPORT_H },
      deviceScaleFactor: DPR,
    });

    try {
      const fileUrl = 'file:///' + tmpHtml.replace(/\\/g, '/');
      await page.goto(fileUrl, { waitUntil: 'networkidle' });
      await page.waitForTimeout(500);
      await page.screenshot({ path: outputPath, type: 'png' });
      console.log(`  [done] ${outputPath}`);
    } catch (err) {
      console.error(`  [error] ${folder}:`, err.message);
    } finally {
      await page.close();
      fs.unlinkSync(tmpHtml);
    }
  }

  await browser.close();
  console.log('\nAll previews generated!');
}

generatePreviews().catch(err => {
  console.error('Failed:', err);
  process.exit(1);
});
