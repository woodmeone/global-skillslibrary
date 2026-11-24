#!/usr/bin/env node
/**
 * blueprint — draw a flow diagram, one file, nothing else.
 *
 *   node scripts/draw.mjs --in model.json --out 图.html
 *
 * No stories, no scenarios, no four-question cards. A model of boxes and
 * arrows in, one self-contained HTML out: pan, zoom, drill into any box,
 * search, light/dark. That is the whole skill.
 *
 * The model only needs `diagrams`. `title` and `root` are optional.
 *
 *   {
 *     "title": "报销审批",
 *     "root": "main",
 *     "diagrams": {
 *       "main": {
 *         "title": "主流程", "sub": "…", "w": 1200, "h": 520,
 *         "nodes": [{ "id","x","y","w","h","title","lines":[],"tag","drill","tip" }],
 *         "edges": [{ "from","to","label","dashed","both","via" }],
 *         "bounds": [{ "x","y","w","h","label" }],
 *         "groups": [{ "x","y","w","h","label" }]
 *       }
 *     }
 *   }
 *
 * Exits 1 when the model contradicts itself (a `drill` or edge endpoint that
 * names something that is not there). That check is the point: a diagram whose
 * arrows point at nothing is worse than no diagram.
 */
import fs from 'node:fs'
import path from 'node:path'
import { validate, normalise, renderDiagramPage } from './core.mjs'

function arg(name, fallback) {
  const i = process.argv.indexOf('--' + name)
  return i >= 0 && process.argv[i + 1] ? process.argv[i + 1] : fallback
}

const IN = arg('in', 'model.json')
const OUT = arg('out', 'diagram.html')

if (!fs.existsSync(IN)) {
  console.error(`input not found: ${IN}`)
  process.exit(1)
}

// Tolerate a UTF-8 BOM. Windows PowerShell's `Set-Content -Encoding utf8`
// writes one by default, and JSON.parse chokes on it with a message that does
// not mention the BOM at all.
const raw = fs.readFileSync(IN, 'utf8').replace(/^\uFEFF/, '')
let spec
try {
  spec = JSON.parse(raw)
} catch (e) {
  console.error(`${IN} is not valid JSON: ${e.message}`)
  process.exit(1)
}

const { problems } = validate(spec)
if (problems.length) {
  console.error('model problems:')
  for (const p of problems) console.error('  X ' + p)
  process.exit(1)
}

const data = normalise(spec)
const title = spec.title || Object.keys(data.diagrams)[0] || 'diagram'
const html = renderDiagramPage({ data, title })

fs.writeFileSync(OUT, html, 'utf8')

const counts = Object.values(data.diagrams).map((d) => `${d.id}:${d.nodes.length}`).join(' ')
console.log(`OK ${OUT}`)
console.log(`  ${Object.keys(data.diagrams).length} diagrams · ${counts}`)
console.log(`  ${(html.length / 1024).toFixed(0)} KB · 打开这一个文件就够`)
