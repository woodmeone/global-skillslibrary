#!/usr/bin/env node
/**
 * build.mjs — one command, two readable files.
 *
 *   node build.mjs --in model.json --out walkthrough.html
 *
 * Everything below is one skill with three parts, applied in order:
 *
 *   1. MODEL     You understand the system and write it down as elements +
 *                orchestration + verification. That is `model.json`.
 *   2. DRAW      This script turns the model into a layered interactive diagram.
 *   3. EXPLAIN   The same script wraps that diagram in a document: a user story
 *                on top, a four-question card per node underneath.
 *
 * ── Output ─────────────────────────────────────────────────────────────
 *
 * Two self-contained HTML files, written from the same model in one run:
 *
 *   walkthrough.html           story → diagram → four-question cards.
 *                              This is the one to read.
 *   walkthrough-diagram.html   the diagram alone, full viewport, no prose.
 *                              This is the one to navigate.
 *
 * They link to each other. Neither needs a server or a build step. The split
 * exists because the two jobs want opposite page shells: reading wants a
 * scrolling document, navigating wants a fixed viewport. Forcing both onto
 * one page gives you the worst of each.
 *
 * ── Input ──────────────────────────────────────────────────────────────
 *
 *   {
 *     "title": "…", "sub": "…", "root": "overview",
 *
 *     "diagrams": {                       // 元素抽象 + 链路编排
 *       "overview": {
 *         "title": "…", "sub": "…", "crumb": "总图",
 *         "w": 1200, "h": 520,
 *         "bounds":   [{x,y,w,h,label}],  // 虚线边界区
 *         "groups":   [{x,y,w,h,label}],  // 浅色分组区
 *         "notes":    [{x,y,text}],
 *         "nodes": [{
 *           id, x, y, w, h,
 *           title, lines[], tag,
 *           drill,                       // 另一个 diagram 的 id：方框可点开进去
 *           ref,                         // "path@line@token"：方框可看代码
 *           code,                        // 或直接内联 { path, start, lines[], more }
 *           tip, style
 *         }],
 *         "edges": [{
 *           from, to,
 *           fs, ts, fa, ta, via,         // 走线控制
 *           label,                       // 跨过这条线的数据名 —— 必须写
 *           dashed, both, none,
 *           refs[], tip
 *         }]
 *       }
 *     },
 *
 *     "story": [{ beat, node, text }],    // 用户故事，每拍指向一个 node
 *
 *     "sections": {                        // 四问讲解，key 是 node id
 *       "<nodeId>": {
 *         what, why, for, how,            // 是什么 / 为什么 / 有什么用 / 怎么用
 *         name, meta, trap, refs[]
 *       }
 *     }
 *   }
 *
 * ── Validation ─────────────────────────────────────────────────────────
 *
 * The build FAILS (exit 1) when the model contradicts itself:
 *   - a `drill` naming a diagram that does not exist
 *   - an edge endpoint that is not a node
 *   - a `sections` key that is not a node
 *   - a `story` beat naming a missing node
 *   - `root` naming a diagram that does not exist
 *
 * That is the verification layer: a wrong claim about structure breaks the
 * build instead of shipping quietly.
 */
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'

const HERE = path.dirname(fileURLToPath(import.meta.url))

/** The drawing skill this one is built on.
 *
 *  Loaded with a dynamic import ON PURPOSE. A static `import ... from
 *  '../../blueprint/...'` is resolved by the ESM loader before any of
 *  this file runs, so a missing sibling would surface as
 *  ERR_MODULE_NOT_FOUND with a stack trace — an error about module resolution
 *  when the real problem is "you installed one of the two skills". Check
 *  first, then import. */
const CORE = path.resolve(HERE, '..', '..', 'blueprint', 'scripts', 'core.mjs')
if (!fs.existsSync(CORE)) {
  console.error('codebase-walkthrough 需要 blueprint 同时安装。')
  console.error(`  找不到：${CORE}`)
  console.error('')
  console.error('  两者在本仓是兄弟目录，按 SKILLS.md「新环境接入」一起软链：')
  console.error('    $LIB = "D:\\Project\\globalSkills-library"')
  console.error('    $SK  = "$env:USERPROFILE\\.dsh\\skills"')
  console.error('    New-Item -ItemType Junction -Path "$SK\\blueprint" `')
  console.error('      -Target "$LIB\\community-skills\\blueprint"')
  console.error('')
  console.error('  codebase-walkthrough 不持有画图引擎，它调用 blueprint 的 core.mjs。')
  process.exit(1)
}

const {
  validate: coreValidate,
  normalise: coreNormalise,
  renderDiagramPage,
  flowAssets,
  esc,
  LOCK_TITLE_JS,
} = await import(pathToFileURL(CORE).href)

function arg(name, fallback) {
  const i = process.argv.indexOf('--' + name)
  return i >= 0 && process.argv[i + 1] ? process.argv[i + 1] : fallback
}

const IN = arg('in', 'model.json')
const OUT = arg('out', 'walkthrough.html')

// Two artifacts, both from the same model:
//   <out>            the walkthrough — story, diagram, four-question cards
//   <diagram>        the diagram on its own, full viewport, nothing else
// `--diagram X.html` names the second one; default is `<out>-diagram.html`.
// `--no-diagram` skips it entirely.
const WANT_DIAGRAM = !process.argv.includes('--no-diagram')
const OUT_DIAGRAM = arg('diagram', OUT.replace(/\.html?$/i, '') + '-diagram.html')
const diagName = OUT_DIAGRAM.split(/[\\/]/).pop()
const walkName = OUT.split(/[\\/]/).pop()

if (!fs.existsSync(IN)) {
  console.error(`input not found: ${IN}`)
  process.exit(1)
}

const spec = JSON.parse(fs.readFileSync(IN, 'utf8'))
const diagrams = spec.diagrams || {}
const ROOT = spec.root || Object.keys(diagrams)[0]
const TITLE = spec.title || 'Walkthrough'
const SUB = spec.sub || ''
const SECTIONS = spec.sections || {}

// ── Scenarios ──────────────────────────────────────────────────────────
// `stories` is a list of named scenarios. A flow diagram is never one line:
// branches exist, and a branch that no scenario walks is a branch nobody has
// checked. The older single `story` array still works and becomes one scenario.
//
// A beat may name the edge it walks (`"edge": "a->b"`). Those declarations are
// what make coverage checkable — without them "did we cover the branches?" is
// an opinion.
const SCENARIOS = (Array.isArray(spec.stories) && spec.stories.length)
  ? spec.stories.map((s, i) => ({ ...s, id: s.id || `s${i + 1}` }))
  : (Array.isArray(spec.story) && spec.story.length)
    ? [{ id: 'main', name: '主路径', kind: '主路径', beats: spec.story }]
    : []
for (const s of SCENARIOS) {
  if (!Array.isArray(s.beats)) s.beats = []
  if (!s.name) s.name = s.id
}
const STORY = SCENARIOS.flatMap(s => s.beats)

// ── 1. validate the model ──────────────────────────────────────────────
// Structure is the drawing skill's job: it owns what a node and an edge are,
// so it owns whether they point at anything. This file adds only the checks
// that need to know about stories and sections.
const { problems, nodeIds: allNodeIds, edges: allEdges } = coreValidate(spec)

if (!diagrams[ROOT]) {
  console.error(`root diagram "${ROOT}" not found; have: ${Object.keys(diagrams).join(', ') || '(none)'}`)
  process.exit(1)
}

for (const key of Object.keys(SECTIONS)) {
  if (!allNodeIds.has(key)) problems.push(`sections: "${key}" is not a node in any diagram`)
}

// Every edge, addressable as "from->to".
const edgeKeys = new Set(allEdges.map((x) => x.key))

for (const [si, s] of SCENARIOS.entries()) {
  const where = s.name || s.id || `scenario ${si + 1}`
  if (!s.beats.length) problems.push(`scenario "${where}": has no beats`)
  for (const b of s.beats) {
    if (b.node && !allNodeIds.has(b.node)) {
      problems.push(`scenario "${where}": beat references node "${b.node}", which does not exist`)
    }
    if (b.edge && !edgeKeys.has(b.edge)) {
      problems.push(`scenario "${where}": beat references edge "${b.edge}", which does not exist`)
    }
    if (!b.node && !b.edge) {
      problems.push(`scenario "${where}": beat "${b.beat || '?'}" names neither a node nor an edge`)
    }
  }
}

if (problems.length) {
  console.error('model problems:')
  for (const p of problems) console.error('  X ' + p)
  process.exit(1)
}

// ── 1b. coverage — which edges did any scenario walk ───────────────────
// Reported, not enforced: a branch can legitimately be unexercised. But it has
// to be visible, because an unreached edge is usually either a scenario you
// forgot to write or a box you drew and nobody uses.
const walkedEdges = new Set()
const walkedNodes = new Set()
for (const s of SCENARIOS) {
  for (const b of s.beats) {
    if (b.edge) walkedEdges.add(b.edge)
    if (b.node) walkedNodes.add(b.node)
  }
}
const missedEdges = allEdges.filter(x => !walkedEdges.has(x.key))

// ── 2. normalise for renderer.js ───────────────────────────────────────
// The renderer's input shape belongs to the drawing skill. Ask it.
const data = coreNormalise(spec)

// ── 3. build the explanation layer ─────────────────────────────────────
function renderRefs(refs) {
  if (!Array.isArray(refs) || !refs.length) return ''
  return refs.map(r => {
    if (!r || !Array.isArray(r.snippet)) {
      // A raw path@line@token with no extracted body: show the pointer only.
      return `<div class="refptr"><code>${esc(r)}</code></div>`
    }
    const rows = r.snippet.map(l =>
      `<div class="cl${l.hit ? ' hit' : ''}"><i>${l.n}</i><code>${esc(l.text) || ' '}</code></div>`
    ).join('')
    return `<details class="ref"><summary>${esc(r.label || 'code')}`
      + `<code class="loc">${esc(r.path)}:${r.line}</code></summary>`
      + `<div class="src">${rows}</div></details>`
  }).join('')
}

function renderCard(nodeId, s, diagramTitle) {
  if (!s) return ''
  const qa = (label, val, cls = '') => val
    ? `<div class="qa ${cls}"><dt>${esc(label)}</dt><dd>${esc(val)}</dd></div>` : ''
  return `
<section class="card" id="sec-${esc(nodeId)}">
  <header>
    <span class="badge">${esc(diagramTitle)}</span>
    <h3>${esc(s.name || nodeId)}</h3>
    ${s.meta ? `<code class="meta">${esc(s.meta)}</code>` : ''}
  </header>
  <dl>
    ${qa('是什么', s.what)}
    ${qa('为什么', s.why)}
    ${qa('有什么用', s.for)}
    ${qa('怎么用', s.how)}
    ${qa('坑', s.trap, 'trap')}
  </dl>
  ${renderRefs(s.refs)}
</section>`
}

const cards = []
for (const [id, d] of Object.entries(diagrams)) {
  for (const n of d.nodes || []) {
    const s = SECTIONS[n.id]
    if (!s) continue
    cards.push(renderCard(n.id, { ...s, name: s.name || n.title }, d.title || id))
  }
}

// A scenario is one concrete person walking one concrete path. Different
// people hit different branches; that is the whole point of listing several.
// `kind` drives the colour: 主路径 = the happy path, 拒绝/失败 = what the system
// refuses and says instead, 回退/并发 = what happens when the world moves.
const KIND_CLASS = {
  '主路径': 'k-main', '正常': 'k-main',
  '拒绝': 'k-deny', '失败': 'k-deny', '中断': 'k-deny',
  '回退': 'k-recoil', '并发': 'k-recoil', '边界': 'k-recoil', '降级': 'k-recoil',
}

function renderBeat(b, i) {
  const jump = b.node
    ? `<a class="jump" href="#sec-${esc(b.node)}">→ ${esc(b.node)}</a>`
    : ''
  const edge = b.edge
    ? `<code class="edgeref" title="跨过这条边">${esc(b.edge)}</code>`
    : ''
  return `    <li class="beat${b.edge && !walkedEdges.has(b.edge) ? ' unmatched' : ''}">
      <div class="beat-h"><span class="bn">${i + 1}</span>${esc(b.beat)}${jump}${edge}</div>
      <div class="beat-b">${esc(b.text)}</div>
    </li>`
}

const scenarioHtml = SCENARIOS.map((s, si) => {
  const cls = KIND_CLASS[s.kind] || 'k-main'
  const nodeLinks = [...new Set(s.beats.map(b => b.node).filter(Boolean))]
  return `
<section class="scenario ${cls}" id="sc-${esc(s.id)}">
  <header>
    <span class="skind">${esc(s.kind || '场景')}</span>
    <h3>${esc(s.name)}</h3>
    ${s.sub ? `<p class="ssub">${esc(s.sub)}</p>` : ''}
  </header>
  ${s.setup ? `<div class="setup">${esc(s.setup)}</div>` : ''}
  <ol class="beats">
${s.beats.map(renderBeat).join('\n')}
  </ol>
  ${s.ends ? `<div class="ends"><b>走完得到</b>${esc(s.ends)}</div>` : ''}
</section>`
}).join('\n')

// Legend + coverage: the honest part. It says which edges no scenario touches,
// so "we covered the branches" is checkable rather than asserted.
const kindsPresent = [...new Set(SCENARIOS.map(s => s.kind).filter(Boolean))]
const coverageHtml = allEdges.length ? `
<div class="coverage">
  <div class="cov-h">
    <b>${walkedEdges.size}</b> / ${allEdges.length} 条链路被场景走到
    <span class="cov-bar"><i style="width:${(walkedEdges.size / allEdges.length * 100).toFixed(1)}%"></i></span>
  </div>
  ${missedEdges.length ? `<details class="cov-miss">
    <summary>未走到的 ${missedEdges.length} 条（可能是漏写的场景，也可能是没人用的画法）</summary>
    <ul>${missedEdges.map(x => `<li><code>${esc(x.key)}</code><span>${esc(x.diagram)}</span>${x.e.label ? `<em>${esc(String(x.e.label).replace(/\n/g, ' '))}</em>` : ''}</li>`).join('')}</ul>
  </details>` : '<div class="cov-ok">每条链路都有场景走到。</div>'}
</div>` : ''

let storyHtml = ''
if (SCENARIOS.length) {
  storyHtml = `
<div class="panel" id="story">
  <h2>场景案例</h2>
  <p class="lede">一个链路图里的分支不会自己发生。<b>${SCENARIOS.length}</b> 个具体的人，各走一条，走出来的每一拍都标了跨过哪条边。没走到的边列在最后。</p>
  <div class="kindlegend">
    ${kindsPresent.map(k => `<span class="kl ${KIND_CLASS[k] || 'k-main'}">${esc(k)}</span>`).join('')}
  </div>
  ${coverageHtml}
${scenarioHtml}
</div>`
}

// ── 4. page shell ──────────────────────────────────────────────────────
const { css, js } = flowAssets()

const extraCss = `
/* ══ walkthrough layout ══════════════════════════════════════════════ */

/* The vendored stylesheet is written for a full-viewport app: html/body are
   height:100%, overflow:hidden, and #bar / #stage are position:fixed. This
   page is a scrolling document instead, so the lock has to come off first.
   Without this one rule the document is pinned to a single viewport height
   and everything below the fold — the diagram, every card — is unreachable
   by scrolling. That is a broken page, not a cosmetic issue. */
html,body{height:auto;min-height:100%;overflow:visible}

#stage{display:none}
body{background:#fff}
.wrap{max-width:1180px;margin:0 auto;padding:0 24px 100px}

.top{padding:44px 0 26px;border-bottom:2.5px solid var(--line)}
.top .k{font-size:12px;letter-spacing:.2em;color:#c2410c;font-weight:800}
.top h1{font-size:36px;font-weight:800;line-height:1.22;margin:12px 0 12px;letter-spacing:-.02em}
.top p{font-size:16.5px;color:var(--sub);max-width:760px;line-height:1.75}
.top .stats{margin-top:18px;display:flex;gap:22px;flex-wrap:wrap;font-size:13px;color:var(--muted)}
.top .stats b{color:var(--ink);font-weight:700}

.panel{background:#fff;border:1px solid var(--line);border-radius:14px;padding:24px 26px;margin:26px 0;
  box-shadow:0 2px 10px rgba(0,0,0,.04)}
.panel h2{font-size:22px;font-weight:800;margin-bottom:6px}
.panel .lede{color:var(--sub);font-size:14.5px;margin-bottom:16px}

/* The vendored CSS pins #bar and #stage to the viewport. Inside this page
   every one of them must be anchored to the container instead, or the SVG
   renders outside the page. Keep these overrides if you touch the CSS. */
.graphbox{border:1px solid var(--line);border-radius:14px;overflow:hidden;background:#fff;margin:26px 0}
.graphbox .viewer{position:relative;height:660px;display:flex;flex-direction:column}
.graphbox #bar{position:relative;top:auto;left:auto;right:auto;flex:0 0 auto;width:100%}
.graphbox #stage{position:relative;top:auto;left:auto;right:auto;bottom:auto;
  flex:1 1 auto;min-height:0;width:100%;height:auto;display:block;overflow:hidden}
.graphbox #head{position:absolute;top:8px;left:16px;right:16px;z-index:3;pointer-events:none}
.graphbox #canvas{position:absolute;top:0;left:0;width:100%;height:100%;display:block}
.graphbox #help{position:absolute;bottom:4px;left:16px;right:16px;z-index:3}

/* story */
.beats{list-style:none;counter-reset:b}
.beats li{counter-increment:b;position:relative;padding:0 0 22px 46px;border-left:2px solid var(--line)}
.beats li:last-child{border-left-color:transparent;padding-bottom:0}
.beats li::before{content:counter(b);position:absolute;left:-17px;top:-2px;width:32px;height:32px;
  border-radius:50%;background:#2a2622;color:#fff;font-weight:800;font-size:14px;
  display:flex;align-items:center;justify-content:center}
.beat-h{font-weight:750;font-size:15.5px;margin-bottom:4px}
.beat-h .jump{margin-left:10px;font-size:12px;font-weight:700;color:#c2410c;text-decoration:none;
  background:#fff4ed;padding:2px 7px;border-radius:5px}
.beat-h .jump:hover{background:#c2410c;color:#fff}
.beat-b{font-size:14.5px;color:var(--sub);line-height:1.75}

/* ── scenarios ─────────────────────────────────────────────────────── */
.kindlegend{display:flex;gap:8px;flex-wrap:wrap;margin:0 0 14px}
.kl{font-size:11.5px;font-weight:800;padding:3px 9px;border-radius:5px;letter-spacing:.04em}
.kl.k-main{background:#eef6ee;color:#166534}
.kl.k-deny{background:#fdeaea;color:#9f1239}
.kl.k-recoil{background:#eef2fd;color:#1e40af}

.scenario{border:1px solid var(--line);border-radius:12px;margin:16px 0;overflow:hidden;background:#fff}
.scenario header{padding:13px 20px 11px;border-bottom:1px solid var(--line);background:#fafaf9}
.scenario header h3{display:inline;font-size:17px;font-weight:750}
.scenario header .skind{font-size:11px;font-weight:800;letter-spacing:.06em;padding:2px 8px;
  border-radius:5px;margin-right:10px;vertical-align:2px}
.scenario.k-main header .skind{background:#166534;color:#fff}
.scenario.k-deny header .skind{background:#9f1239;color:#fff}
.scenario.k-recoil header .skind{background:#1e40af;color:#fff}
.scenario header .ssub{margin:6px 0 0;font-size:13.5px;color:var(--sub)}
.scenario .setup{margin:0;padding:12px 20px;background:#fffdf7;border-bottom:1px solid #f3f0ea;
  font-size:14px;line-height:1.75;color:#57534e}
.scenario .setup::before{content:"设定 · ";font-weight:800;color:#c2410c}
.scenario.k-deny .setup::before{color:#9f1239}
.scenario.k-recoil .setup::before{color:#1e40af}
.scenario .beats{padding:18px 20px 4px}
.scenario .ends{margin:0;padding:11px 20px;background:#f8f7f5;border-top:1px solid var(--line);
  font-size:14px;color:var(--sub);line-height:1.7}
.scenario .ends b{color:var(--ink);margin-right:10px}
.scenario.k-deny .beats li::before{background:#9f1239}
.scenario.k-recoil .beats li::before{background:#1e40af}

/* per-beat: the ordinal sits inside the text so scenario numbering is
   independent of the li counter */
.beat-h .bn{display:none}
.beat-h .edgeref{font-family:ui-monospace,Consolas,monospace;font-size:11px;
  background:#f0ebe3;color:#57534e;padding:2px 7px;border-radius:4px;margin-left:8px}
.beat.unmatched{opacity:.75}

/* coverage */
.coverage{border:1px solid var(--line);border-radius:10px;padding:13px 16px;margin:0 0 18px;background:#fcfbfa}
.cov-h{display:flex;align-items:center;gap:12px;font-size:13.5px;color:var(--sub)}
.cov-h b{color:var(--ink);font-size:15px}
.cov-bar{flex:1 1 auto;height:7px;background:#e7e3dc;border-radius:4px;overflow:hidden;min-width:80px}
.cov-bar i{display:block;height:100%;background:#166534}
.cov-miss{margin-top:10px;font-size:13px}
.cov-miss summary{cursor:pointer;color:#9f1239;font-weight:700;list-style:none}
.cov-miss summary::-webkit-details-marker{display:none}
.cov-miss summary::before{content:"\\25B8 ";font-weight:900}
.cov-miss[open] summary::before{content:"\\25BE "}
.cov-miss ul{margin:9px 0 0;padding:0;list-style:none}
.cov-miss li{display:flex;gap:10px;align-items:baseline;padding:3px 0;color:var(--sub)}
.cov-miss li code{font-family:ui-monospace,Consolas,monospace;font-size:11.5px;
  background:#f0ebe3;padding:1px 6px;border-radius:4px;color:#57534e}
.cov-miss li span{font-size:11.5px;color:var(--muted)}
.cov-miss li em{font-style:normal;font-size:12px;color:#c2410c}
.cov-ok{margin-top:8px;font-size:13px;color:#166534;font-weight:700}

/* four-question cards */
.card{background:#fff;border:1px solid var(--line);border-radius:12px;margin:14px 0;overflow:hidden;
  scroll-margin-top:20px}
.card header{padding:13px 20px;background:#fafaf9;border-bottom:1px solid var(--line);
  display:flex;align-items:center;gap:12px;flex-wrap:wrap}
.card .badge{font-size:11px;font-weight:800;letter-spacing:.06em;padding:2px 8px;border-radius:5px;
  background:#2a2622;color:#fff}
.card h3{font-size:17px;font-weight:750}
.card .meta{margin-left:auto;font-family:ui-monospace,Consolas,monospace;font-size:11.5px;color:var(--muted)}
.card dl{padding:8px 20px 14px}
.qa{display:grid;grid-template-columns:76px 1fr;gap:14px;padding:9px 0;border-bottom:1px solid #f3f0ea}
.qa:last-child{border-bottom:none}
.qa dt{font-weight:800;font-size:12px;color:var(--muted);padding-top:3px;letter-spacing:.04em}
.qa dd{font-size:14.5px;line-height:1.78;color:var(--ink)}
.qa.trap dd{color:#7c2d12;background:#fff7ed;padding:8px 12px;border-radius:7px}

/* code refs inside a card */
details.ref{border:1px solid var(--line);border-radius:8px;margin:8px 20px;background:#fbfaf8;overflow:hidden}
details.ref summary{padding:9px 13px;cursor:pointer;font-size:13px;list-style:none;
  display:flex;align-items:center;gap:10px;flex-wrap:wrap;user-select:none}
details.ref summary::-webkit-details-marker{display:none}
details.ref summary::before{content:"\\25B8";color:#c2410c;font-weight:900;font-size:11px}
details.ref[open] summary::before{content:"\\25BE"}
details.ref .loc{font-family:ui-monospace,Consolas,monospace;font-size:11.5px;color:var(--muted);
  background:#f0ebe3;padding:2px 7px;border-radius:4px}
details.ref[open] summary{border-bottom:1px solid var(--line);background:#fff}
.src{overflow-x:auto;font-family:ui-monospace,Consolas,monospace;font-size:12px;line-height:1.7;
  background:#1c1917;color:#e7e5e4;padding:10px 0}
.src .cl{display:flex;white-space:pre}
.src .cl.hit{background:rgba(194,65,12,.18)}
.src i{flex:0 0 48px;text-align:right;padding-right:12px;color:#57534e;font-style:normal;user-select:none}
.src code{flex:1;padding-right:14px}
.src .cl.hit i{color:#fdba74;font-weight:700}
.refptr{margin:8px 20px;font-size:12px;color:var(--muted)}
.refptr code{font-family:ui-monospace,Consolas,monospace;background:#f0ebe3;padding:2px 7px;border-radius:4px}

@media (max-width:760px){
  .top h1{font-size:27px}
  .qa{grid-template-columns:1fr;gap:2px}
  .graphbox .viewer{height:460px}
}
`

// The title-lock script and the "which diagram" wording both belong to the
// drawing skill now — it renders the standalone page. Nothing to duplicate here.

const html = `<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${esc(TITLE)}</title>
<style>${css}${extraCss}</style>
</head>
<body data-theme="light">

<div class="wrap">

  <div class="top">
    <div class="k">WALKTHROUGH</div>
    <h1>${esc(TITLE)}</h1>
    ${SUB ? `<p>${esc(SUB)}</p>` : ''}
    <div class="stats">
      <span><b>${Object.keys(diagrams).length}</b> 层图</span>
      <span><b>${allNodeIds.size}</b> 个节点</span>
      <span><b>${cards.length}</b> 个讲解</span>
      ${SCENARIOS.length ? `<span><b>${SCENARIOS.length}</b> 个场景案例</span>` : ''}
      ${allEdges.length ? `<span><b>${walkedEdges.size}/${allEdges.length}</b> 条链路被走到</span>` : ''}
    </div>
  </div>

  ${storyHtml}

  <div class="panel">
    <h2>链路图</h2>
    <p class="lede">点方框上的 ⧉ 进入它的内部；点方框本身跳到下面的讲解。Esc 返回上一层，/ 搜索方框。
      ${WANT_DIAGRAM ? `<a href="${esc(diagName)}" style="color:#c2410c;font-weight:700;text-decoration:none">只看这张图 →</a>` : ''}</p>
    <div class="graphbox">
      <div class="viewer">
        <header id="bar">
          <div class="brand">${esc(TITLE)}</div>
          <div id="crumbs"></div>
          <div class="search"><input id="q" type="search" placeholder="找方框…  ( / )" autocomplete="off" spellcheck="false"><div id="results" hidden></div></div>
          <nav>
            <button id="up" title="上一层 (Esc)">上一层</button>
            <button id="fit" title="适应 (0)">适应</button>
            <button id="theme" title="明暗 (T)">主题</button>
          </nav>
        </header>
        <main id="stage">
          <div id="head"><div id="dtitle"></div><div id="dsub"></div><div id="documentation"></div></div>
          <svg id="canvas" preserveAspectRatio="xMidYMid meet" role="img" aria-label="diagram"></svg>
          <div id="tip" hidden></div>
          <aside id="code" hidden></aside>
          <div id="help">⧉ 打开内部图 · 点方框本体会跳到讲解 · Esc 返回 · 滚轮缩放，拖动平移</div>
        </main>
      </div>
    </div>
  </div>

  <div class="panel" style="padding:24px 26px 8px">
    <h2>节点讲解</h2>
    <p class="lede">每个节点四件事：是什么、为什么存在、有什么用、怎么用。</p>
  </div>

  ${cards.join('\n')}

</div>

<script>window.BLUEPRINT = ${JSON.stringify(data).replace(/</g, '\\u003c')};</script>
<script>${LOCK_TITLE_JS}</script>
<script>${js}</script>
<script>
// Bridge the diagram into the document.
//
// The renderer navigates on pointerup (it captures the pointer on the svg,
// so pointerup lands on the svg, not on the box). Two traps here:
//
//   1. A capture-phase "click" listener runs AFTER the renderer has already
//      drilled — you get the sub-diagram AND the card scroll.
//   2. Listening on the svg does not help either: on the target element,
//      capture and bubble listeners fire in registration order, and the
//      renderer registered first.
//
// So this listens on document in the capture phase, which fires before any
// listener on the svg, and stops the event there when the click means "read
// the card". One gesture, one outcome.
//
// Three cases fall through to the renderer untouched:
//   - the ⧉ glyph: drilling must still work, or the page loses its whole
//     sub-diagram layer.
//   - a drag: the pointer moved, this is panning, not a click.
//   - a box with no section: there is no card to scroll to.
(function () {
  const sections = new Set(${JSON.stringify(Object.keys(SECTIONS))});
  let down = null;

  document.addEventListener('pointerdown', function (ev) {
    const t = ev.target;
    if (!t.closest || !t.closest('#canvas')) return;
    // Record what is under the pointer NOW. The renderer calls
    // svg.setPointerCapture() on pointerdown, so by pointerup the event target
    // is the svg itself — the node you pressed is no longer the target.
    const node = t.closest('.node');
    down = {
      x: ev.clientX,
      y: ev.clientY,
      id: node ? node.dataset.id : null,
      glyph: !!(t.closest('.glyph')),
    };
  }, true);

  document.addEventListener('pointerup', function (ev) {
    const from = down;
    down = null;
    if (!from) return;
    if (Math.abs(ev.clientX - from.x) + Math.abs(ev.clientY - from.y) > 4) return; // pan
    if (from.glyph) return;                        // ⧉ — let the renderer drill
    if (!from.id || !sections.has(from.id)) return; // no card to scroll to
    const card = document.getElementById('sec-' + from.id);
    if (!card) return;
    // Claim the gesture: the renderer must not also navigate.
    ev.stopPropagation();
    ev.preventDefault();
    card.scrollIntoView({ behavior: 'smooth', block: 'start' });
    card.style.transition = 'background .35s';
    card.style.background = '#fff4ed';
    setTimeout(function () { card.style.background = '#fff'; }, 1200);
  }, true);
})();
</script>
</body>
</html>
`

// ── 5. the diagram on its own ──────────────────────────────────────────
// Delegated: the standalone page belongs to the drawing skill. Only the link
// back to this document is new, so it is passed in as the extra nav item.
const diagramHtml = renderDiagramPage({
  data,
  title: `${TITLE} · 链路图`,
  brand: TITLE,
  nav: `<a href="${esc(walkName)}" title="图 + 用户故事 + 节点讲解">图文讲解</a>`,
  assets: { css, js },
})

fs.writeFileSync(OUT, html, 'utf8')
if (WANT_DIAGRAM) fs.writeFileSync(OUT_DIAGRAM, diagramHtml, 'utf8')

console.log(`OK ${OUT}`)
console.log(`  ${Object.keys(diagrams).length} diagrams · ${allNodeIds.size} nodes · ${cards.length} sections · ${STORY.length} story beats`)
console.log(`  root: ${ROOT} · ${(html.length / 1024).toFixed(0)} KB`)
if (WANT_DIAGRAM) {
  console.log(`OK ${OUT_DIAGRAM}`)
  console.log(`  链路图单独一份 · ${(diagramHtml.length / 1024).toFixed(0)} KB`)
}
