---
name: codebase-blueprint
description: Draw a layered, clickable flow diagram as one self-contained HTML file — boxes that open into other diagrams, arrows that carry labels, zoom, search, light/dark. Takes a model of nodes and edges and renders it; knows nothing about code, so it draws business processes (报销审批 / 下单履约 / 客服工单), data pipelines (ETL), decision trees, state machines, org and system architecture, and code structure equally well. Use when the user wants to 画图 / 画流程图 / 画链路图 / 画架构图 / 画业务流程图 / 画状态机 / 画决策树 / draw a flow diagram / architecture diagram / process map, wants a diagram they can click into, or wants a diagram that explains itself without a wall of prose. For a diagram wrapped in a written walkthrough with scenario cases, use codebase-walkthrough instead — this skill is only the picture.
---

# Draw a flow diagram

**You build a model. This skill turns it into one HTML file.**

A model is boxes and arrows, nothing more:

```json
{
  "title": "报销审批",
  "root": "main",
  "diagrams": {
    "main": {
      "title": "主流程", "w": 1180, "h": 520,
      "nodes": [{ "id": "a", "x": 40, "y": 200, "w": 200, "h": 110,
                  "title": "员工", "lines": ["提交单据"] }],
      "edges": [{ "from": "a", "to": "b", "label": "单据.原始" }]
    }
  }
}
```

```bash
node scripts/draw.mjs --in model.json --out 图.html
```

Open the file. That is the whole workflow.

---

## What this draws well

| Kind | Top level | Boxes open into |
|---|---|---|
| **Business process** | Actors and handoffs | That actor's internal steps |
| **Data pipeline** | Stages | That stage's transforms |
| **Decision tree / state machine** | States or gates | A gate's sub-checks |
| **System architecture** | Services and stores | A service's modules |
| **Code structure** | Packages and entry points | A package's files |

The same model shape covers all of them. There is no "code mode".

---

## Things that decide whether the diagram reads well

### 1. Every arrow carries a payload

An arrow labelled `A 调用 B` is unfalsifiable — nobody can say it is wrong.
An arrow labelled `单据.已校验` says what crosses it, and can be checked.

If you cannot name what crosses an arrow, ask whether the arrow is real.

### 2. Dashes mean "not the main line"

Dashed edges are refusals, failures, retries, and other branches. Use them:

```
gate → refuse   "命中任一条"        ← what happens when the check fails
verify → block  "unknown"          ← what happens when the data lies
verify → query  "stale → 重查一次"  ← a back-edge: this can happen twice
```

**A dashed back-edge returning to an earlier box is the most informative
thing on the diagram.** It says "this happens twice, and the second time is
not the first time." If your model has zero back-edges, you probably drew a
happy path and stopped.

### 3. One altitude per diagram

Never put a stage next to an implementation detail. If a box is a different
size of thing from its neighbours, it belongs one level down — use `drill`.

Top level: **5–9 boxes**. More means you are one level too deep.

### 4. Coordinates are yours to choose

There is no auto-layout. `x`, `y`, `w`, `h` are in diagram units and the
viewer fits them to the screen. Size the canvas to the content (`w`, `h`), not
to a monitor.

Leave room for labels: an edge label is drawn along its longest segment, so a
horizontal run between two boxes needs ~60px of gap to hold text.

### 5. Loading

By default O(n), but it is also O(n) in the number of times you move a box by
20px. Two passes are usually enough: lay out the skeleton, then nudge the two
or three boxes whose labels collide.

---

## Node and edge fields

### Node
| Field | Meaning |
|---|---|
| `id` | Unique across the whole model — edges and `drill` refer to it |
| `x`, `y`, `w`, `h` | Position and size in diagram units |
| `title` | The bold line |
| `lines` | Small lines under the title |
| `tag` | A small tab in the top-left corner (`失败`, `拒绝`, `人工`) |
| `drill` | Another diagram's id — this box opens into it |
| `tip` | Hover text |
| `style` | `box` (default) or `tagged` (thicker border, for rejections) |

### Edge
| Field | Meaning |
|---|---|
| `from`, `to` | Node ids in the same diagram |
| `label` | **What crosses it.** Always write one. |
| `fs`, `ts` | Side to leave/enter: `l` `r` `t` `b` (default `r` → `l`) |
| `fa`, `ta` | Position along that side, 0–1 (default 0.5) |
| `via` | Waypoints `[[x,y], …]` when the auto-router would cut through a box |
| `dashed` | Refusal / failure / retry / branch |
| `both` | Arrowheads on both ends |
| `none` | No arrowhead (pure association) |

### Diagram
| Field | Meaning |
|---|---|
| `title`, `sub`, `crumb` | Heading, one-line description, breadcrumb label |
| `w`, `h` | Canvas size — size to content |
| `parent` | Parent diagram id (drives Esc and the breadcrumb) |
| `bounds` | Dashed regions `{x,y,w,h,label}` |
| `groups` | Light grouping rectangles |
| `notes` | Free text `{x,y,text,anchor}` |

---

## Controls the reader gets

| | |
|---|---|
| `⧉` on a box | Open the diagram inside it |
| `Esc` | Back one level |
| `/` | Search boxes |
| `0` | Fit to screen |
| `T` | Light / dark |
| wheel, drag | Zoom, pan |

---

## The build fails on purpose

`draw.mjs` exits 1 when the model contradicts itself:

```
model problems:
  X main: node "a" drills into "nope", which does not exist
  X main: edge from "ghost" — no such node
```

A diagram whose arrows point at nothing is worse than no diagram. Fix the
model, not the renderer.

It also tolerates a UTF-8 BOM — Windows PowerShell's `Set-Content -Encoding
utf8` writes one, and a bare `JSON.parse` would fail with a message that never
mentions the BOM.

---

## Honest limits

- **The page is your model, not an inventory.** It shows what you chose to draw.
- **No auto-layout.** You place the boxes. This is deliberate: hand-placed
  boxes read better than a layout engine's output for anything under ~30 nodes.
- **One file, no server.** If it needs to update live, it is the wrong tool.
- **`drill` is a link, not a proof** — it shows the sub-diagram you wrote.

---

## Files

- `scripts/draw.mjs` — the CLI: read model, validate, render, write.
- `scripts/core.mjs` — `validate`, `normalise`, `renderDiagramPage`. Import
  these if you are building a document *around* a diagram.
- `scripts/flow/` — vendored Interfold renderer and CSS (LGPL-3.0, see
  `scripts/flow/LICENSE.md`). **This is the only copy in the skills tree.**
- `assets/model.template.json` — copy this to start.

`codebase-walkthrough` imports `core.mjs` from here. Keep the two installed
side by side; the engine lives in exactly one place.
