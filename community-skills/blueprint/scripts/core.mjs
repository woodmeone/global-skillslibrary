/**
 * core.mjs — the drawing half of a flow diagram, on its own.
 *
 * This module knows nothing about stories, scenarios, or explanations. It takes
 * a model of boxes and arrows and returns one self-contained HTML page you can
 * pan, zoom, drill and search. That is the whole contract.
 *
 *   import { validate, normalise, renderDiagramPage } from './core.mjs'
 *
 *   const problems = validate(spec)          // [] means the model is consistent
 *   const data     = normalise(spec)         // the shape renderer.js expects
 *   const html     = renderDiagramPage({ spec, data, ... })
 *
 * `codebase-walkthrough` imports this file and wraps the result in its document.
 * There is exactly one copy of renderer.js / blueprint.css in the whole skills
 * tree, and it lives next to this file, in `flow/`.
 */
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const HERE = path.dirname(fileURLToPath(import.meta.url))
export const FLOW_DIR = path.join(HERE, 'flow')

/** The vendored Interfold assets. Read once, reused by every page. */
export function flowAssets() {
  return {
    css: fs.readFileSync(path.join(FLOW_DIR, 'blueprint.css'), 'utf8'),
    js: fs.readFileSync(path.join(FLOW_DIR, 'renderer.js'), 'utf8'),
  }
}

export function esc(s) {
  return String(s ?? '')
    .replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;')
}

/**
 * Structural problems with the model. An empty array means every claim in it
 * points at something that exists — no dangling `drill`, no edge endpoint that
 * is not a node, no `root` naming a diagram that is not there.
 *
 * Stories and sections are the walkthrough's business, so they are checked
 * there, not here. This only guarantees the *picture* is coherent.
 */
export function validate(spec) {
  const problems = []
  const diagrams = spec.diagrams || {}
  const root = spec.root || Object.keys(diagrams)[0]

  if (!diagrams[root]) {
    problems.push(`root diagram "${root}" not found; have: ${Object.keys(diagrams).join(', ') || '(none)'}`)
    return { problems, nodeIds: new Set(), edges: [] }
  }

  const nodeIds = new Set()
  const edges = []

  for (const [id, d] of Object.entries(diagrams)) {
    const ids = new Set((d.nodes || []).map((n) => n.id))
    for (const nid of ids) nodeIds.add(nid)
    for (const n of d.nodes || []) {
      if (n.drill && !diagrams[n.drill]) {
        problems.push(`${id}: node "${n.id}" drills into "${n.drill}", which does not exist`)
      }
    }
    for (const e of d.edges || []) {
      if (!ids.has(e.from)) problems.push(`${id}: edge from "${e.from}" — no such node`)
      if (!ids.has(e.to)) problems.push(`${id}: edge to "${e.to}" — no such node`)
      edges.push({ diagram: id, key: `${e.from}->${e.to}`, e })
    }
  }

  return { problems, nodeIds, edges }
}

/**
 * Reshape the model into exactly what renderer.js reads. Unknown fields are
 * dropped on purpose: the renderer's own schema is the narrower one, and
 * passing authoring-only fields through has bitten this before.
 *
 * `code` blocks are hoisted into a side table and referenced by key, because
 * the renderer looks them up by id rather than reading inline.
 */
export function normalise(spec) {
  const diagrams = spec.diagrams || {}
  const root = spec.root || Object.keys(diagrams)[0]
  const title = spec.title || 'diagram'

  const data = {
    tag: title,
    root,
    root_dir: '',
    code: {},
    diagrams: {},
  }

  for (const [id, d] of Object.entries(diagrams)) {
    const nodes = (d.nodes || []).map((n) => {
      const out = {
        id: n.id, x: n.x, y: n.y, w: n.w, h: n.h,
        title: n.title, lines: n.lines || [],
      }
      if (n.tag) out.tag = n.tag
      if (n.mono) out.mono = true
      if (n.monoLines) out.monoLines = true
      if (n.tip) out.tip = n.tip
      if (n.style) out.style = n.style
      if (n.drill) out.drill = n.drill
      if (n.ref) out.ref = n.ref
      if (n.code && typeof n.code === 'object') {
        const key = `code:${id}:${n.id}`
        data.code[key] = n.code
        out.code = key
        if (n.focus) out.focus = n.focus
      }
      return out
    })

    const edges = (d.edges || []).map((e) => {
      const out = { from: e.from, to: e.to }
      for (const k of ['fs', 'ts', 'fa', 'ta', 'via', 'label', 'lx', 'ly', 'lt', 'lp', 'lanchor', 'tip', 'key']) {
        if (e[k] !== undefined) out[k] = e[k]
      }
      if (e.dashed) out.dashed = true
      if (e.both) out.both = true
      if (e.none) out.none = true
      if (Array.isArray(e.refs) && e.refs.length) out.refs = e.refs
      return out
    })

    data.diagrams[id] = {
      id, kind: 'diagram',
      title: d.title || id,
      crumb: d.crumb || d.title || id,
      sub: d.sub || '',
      w: d.w || 1400,
      h: d.h || 800,
      groups: d.groups || [],
      bounds: d.bounds || [],
      notes: d.notes || [],
      documentation: d.documentation || [],
      nodes, edges,
      parent: d.parent,
    }
  }

  return data
}

/**
 * The vendored renderer rewrites document.title to "<diagram> · Interfold
 * blueprint" on every navigation, which leaks the library's name into the
 * browser tab. This observer pins the title back to what the page declared.
 * It must be injected BEFORE renderer.js runs, or it captures the rewritten
 * title as the one to keep.
 */
export const LOCK_TITLE_JS = `
(function () {
  var want = document.title;
  var el = document.querySelector('title');
  if (!el) return;
  new MutationObserver(function () {
    if (document.title !== want) document.title = want;
  }).observe(el, { childList: true, characterData: true, subtree: true });
})();
`

/**
 * One page, the diagram and nothing else, filling the viewport.
 *
 * The vendored stylesheet is a full-viewport app shell — fixed #bar, fixed
 * #stage, html/body locked to 100% — so here it is used unmodified. That is
 * why this page does not scroll, and why it looks wrong the moment you wrap
 * it in a document (a document must override the lock; see the walkthrough).
 *
 * @param {object}   o
 * @param {object}   o.data       result of normalise()
 * @param {string}   o.title      the browser tab title
 * @param {string}   [o.brand]    the bar label; defaults to `title`
 * @param {string[]} [o.nav]      extra <a>/<button> HTML in the bar
 * @param {string}   [o.help]     bottom-left hint line
 * @param {object}   [o.assets]   pass flowAssets() to skip re-reading the disk
 */
export function renderDiagramPage({ data, title, brand, nav = '', help = '', assets }) {
  const { css, js } = assets || flowAssets()
  const t = esc(title)
  const b = esc(brand ?? title)
  return `<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${t}</title>
<style>${css}</style>
</head>
<body data-theme="light">
<header id="bar">
  <div class="brand">${b}</div>
  <div id="crumbs"></div>
  <div class="search"><input id="q" type="search" placeholder="找方框…  ( / )" autocomplete="off" spellcheck="false"><div id="results" hidden></div></div>
  <nav>
    ${nav}
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
  <div id="help">${help || '⧉ 打开内部图 · &lt;/&gt; 看代码 · Esc 返回 · 滚轮缩放，拖动平移'}</div>
</main>
<script>window.BLUEPRINT = ${JSON.stringify(data).replace(/</g, '\\u003c')};</script>
<script>${LOCK_TITLE_JS}</script>
<script>${js}</script>
</body>
</html>
`
}

export default { validate, normalise, renderDiagramPage, flowAssets, esc, LOCK_TITLE_JS, FLOW_DIR }
