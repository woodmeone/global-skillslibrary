const { chromium } = require('playwright');
const PptxGenJS = require('pptxgenjs');
const path = require('path');
const fs = require('fs');

const SLIDE_W = 10;
const SLIDE_H = 5.625;
const VIEWPORT_W = 1280;
const VIEWPORT_H = 720;
const DPR = 2;
const JPEG_QUALITY = 95;

async function htmlToPptx(htmlPath, outputPath, options = {}) {
  const bgColor = options.bgColor || '0d0221';
  const title = options.title || 'Presentation';
  const subject = options.subject || '';

  console.log('[1/5] 启动浏览器...');
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({
    viewport: { width: VIEWPORT_W, height: VIEWPORT_H },
    deviceScaleFactor: DPR,
  });

  const fileUrl = 'file:///' + htmlPath.replace(/\\/g, '/');
  console.log('[2/5] 加载 HTML:', fileUrl);
  await page.goto(fileUrl, { waitUntil: 'networkidle' });

  const slideCount = await page.evaluate(() => document.querySelectorAll('.slide').length);
  console.log('[2/5] 检测到', slideCount, '页幻灯片');

  await page.evaluate(() => {
    const nav = document.querySelector('.nav-container');
    if (nav) nav.style.display = 'none';
    const hotzone = document.querySelector('.edit-hotzone');
    if (hotzone) hotzone.style.display = 'none';
    const editBtn = document.querySelector('.edit-toggle');
    if (editBtn) editBtn.style.display = 'none';
    const scanLine = document.querySelector('.scan-line');
    if (scanLine) scanLine.style.display = 'none';
    document.querySelectorAll('.slide').forEach((s) => {
      s.style.transition = 'none';
    });
  });

  const pptx = new PptxGenJS();
  pptx.defineLayout({ name: 'WIDESCREEN_16x9', width: SLIDE_W, height: SLIDE_H });
  pptx.layout = 'WIDESCREEN_16x9';
  pptx.author = 'PowerfulPPT';
  pptx.subject = subject;
  pptx.title = title;

  console.log('[3/5] 逐页截图并提取文本...');
  for (let i = 0; i < slideCount; i++) {
    await page.evaluate((idx) => {
      const slides = document.querySelectorAll('.slide');
      slides.forEach((s, j) => {
        s.classList.remove('active', 'exiting');
        s.style.transition = 'none';
        s.style.opacity = j === idx ? '1' : '0';
        s.style.transform = j === idx ? 'none' : 'translateY(20px)';
        s.style.pointerEvents = j === idx ? 'auto' : 'none';
        s.style.visibility = j === idx ? 'visible' : 'hidden';
      });
      const activeSlide = slides[idx];
      activeSlide.querySelectorAll('.fade-in-up').forEach((el) => {
        el.style.animation = 'none';
        el.style.opacity = '1';
        el.style.transform = 'none';
      });
    }, i);

    await page.waitForTimeout(800);

    const textContent = await page.evaluate((idx) => {
      const slide = document.querySelectorAll('.slide')[idx];
      const texts = [];
      const walk = (el) => {
        if (el.children.length === 0 || el.tagName === 'SPAN' || el.tagName === 'LI') {
          const t = el.textContent.trim();
          if (t && t.length > 1) texts.push(t);
        } else {
          for (const child of el.children) walk(child);
        }
      };
      walk(slide);
      return texts.join('\n');
    }, i);

    const screenshot = await page.screenshot({ type: 'jpeg', quality: JPEG_QUALITY });
    const base64 = screenshot.toString('base64');

    const slide = pptx.addSlide();
    slide.background = { color: bgColor };
    slide.addImage({
      data: `image/jpeg;base64,${base64}`,
      x: 0,
      y: 0,
      w: SLIDE_W,
      h: SLIDE_H,
    });

    if (textContent) {
      slide.addNotes(textContent);
    }

    console.log(`  [${i + 1}/${slideCount}] 第 ${i + 1} 页完成`);
  }

  console.log('[4/5] 生成 PPTX 文件...');
  await pptx.writeFile({ fileName: outputPath });

  console.log('[5/5] 关闭浏览器...');
  await browser.close();

  const stats = fs.statSync(outputPath);
  const sizeMB = (stats.size / 1024 / 1024).toFixed(2);
  console.log(`\n✅ 转换完成!`);
  console.log(`   文件: ${outputPath}`);
  console.log(`   页数: ${slideCount}`);
  console.log(`   大小: ${sizeMB} MB`);
  console.log(`   画布: ${SLIDE_W}" × ${SLIDE_H}" (16:9)`);
}

const args = process.argv.slice(2);
const htmlArg = args[0];
const bgArg = args.find((a) => a.startsWith('--bg='));
const titleArg = args.find((a) => a.startsWith('--title='));

if (!htmlArg || htmlArg.startsWith('--')) {
  console.error('用法: node html-to-pptx.js <html文件路径> [--bg=颜色] [--title=标题]');
  process.exit(1);
}

const htmlPath = path.resolve(htmlArg);
const dir = path.dirname(htmlPath);
const baseName = path.basename(htmlPath, '.html');
const outputPath = path.join(dir, baseName + '.pptx');

const options = {};
if (bgArg) options.bgColor = bgArg.replace('--bg=', '');
if (titleArg) options.title = titleArg.replace('--title=', '');

htmlToPptx(htmlPath, outputPath, options).catch((err) => {
  console.error('❌ 转换失败:', err);
  process.exit(1);
});
