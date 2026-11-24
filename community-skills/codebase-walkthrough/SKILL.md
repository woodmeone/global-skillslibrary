---
name: codebase-walkthrough
description: Understand an unfamiliar project or process and hand back a written walkthrough — a layered interactive flow diagram plus scenario cases and four questions per node. Models the system as elements + orchestration + verification (元素抽象 + 链路编排 + 验证), explains every node with 是什么 / 为什么 / 有什么用 / 怎么用, and walks several named scenario cases through the flow — one per branch — with computed edge coverage so "we covered the branches" is checkable. Use when the user wants to get up to speed on a project (快速上手 / 摸清项目 / 看懂这个系统 / 项目解读 / 图文讲解), wants an explainer or onboarding doc, wants a diagram that also explains itself with scenario cases / 用户故事 / 场景案例 covering branches and exceptions, or asks to click a node and read its parameters and reasoning. **Only the diagram, no explanation? Use `codebase-blueprint` instead** — this skill is built on it and requires it installed alongside.
---

# A written walkthrough of a system

You read the project, model it, and hand back **two HTML files from one model**:

| File | What it is | When to open it |
|---|---|---|
| `图文讲解.html` | scenario cases → diagram → four-question cards | reading, learning, onboarding |
| `链路图.html` | the same diagram alone, full viewport | navigating, drilling, searching |

They share one `model.json` and link to each other. **Both come out of a single build command, so they cannot drift.**

The split is not decoration. Reading wants a scrolling document; navigating wants a fixed viewport with the whole screen for the graph. Cram both into one page and the diagram loses its canvas and the prose loses its scroll.

## This skill owns no drawing code

The picture is drawn by **`codebase-blueprint`**, a sibling skill:

```
community-skills/
├── codebase-blueprint/          renders the diagram; owns renderer.js + blueprint.css
│   └── scripts/core.mjs         ← imported here
└── codebase-walkthrough/
    └── scripts/build.mjs        imports core.mjs, wraps the diagram in a document
```

- **One copy of the engine**, in `codebase-blueprint/scripts/flow/`.
- Dependency runs one way: **walkthrough → blueprint**. Never the reverse.
- If `codebase-blueprint` is missing, `build.mjs` exits 1 with the command to
  link it, rather than an `ERR_MODULE_NOT_FOUND` stack. Keep them side by side
  (they are siblings in this repo, so one `SKILLS.md` junction step installs both).

Want only a diagram, with no story or cards? That is `codebase-blueprint`'s
job — do not use this skill for it.

## The order matters

Do these in sequence. Skipping to the drawing step is the usual failure — you get a picture nobody can learn from.

| # | Step | Output |
|---|---|---|
| **1** | **Model** — elements + orchestration + verification | `model.json` |
| **2** | **Draw** — the model becomes a layered diagram | `链路图.html` |
| **3** | **Explain** — a story on top, four questions per node | `图文讲解.html` |

Steps 2 and 3 are one build command. Step 1 is the work.

## Step 1 — Model

### 1a. Find the wires before reading files

Do not open source files first. Find what the system *says*:

| Wire | Where to look |
|---|---|
| **Protocol** | event/type enums, websocket schemas, openapi, proto |
| **Capabilities** | tool registries, route tables, command enums, permission lists |
| **State** | migrations, table definitions, anything with `version` / `revision` / `digest` |
| **Switches** | config files, especially anything defaulting to `false` |
| **Failures** | error codes, exception classes, `recoverable.error`-style envelopes |

These are small files that explain more than the large ones.

### 1b. Elements — what are the parts

Name the stages from **what changes for the user**, not from the folder layout. Typically 5–9.

| Bad stage name | Good stage name |
|---|---|
| "Services" | "Understand the user" |
| "Handlers" | "Offer candidates" |
| "Phase 2" | "Revise the plan" |

Every stage needs a `sub` line saying why the system cannot skip it. If you cannot state the reason, it is an implementation detail — fold it into another stage.

### 1c. Orchestration — how they connect

For each boundary, name **the payload that crosses it**. That name *is* your edge `label`.

An arrow without a payload name is an arrow nobody could justify. "A calls B" is unfalsifiable; `profile.完整` moves from A to B is checkable.

Branches to model explicitly:

| Kind | Shape |
|---|---|
| **Stage branch** | A node emits one name per mode; each mode gets its own downstream node |
| **Action branch** | One sentence, several operations — each gets its own emitted name |
| **Gate branch** | A check emits both allow and block; the block path is a terminal |
| **Loop** | An emit back into an earlier consume — state the bound in the node's `lines` |

### 1d. Verification — why should anyone believe it

Pick the two or three claims a reader should be able to check, and attach code:

```bash
grep -n "def derive_state_phase" path/to/journey.py
```

```json
{ "id": "stage", "ref": "path/to/journey.py@215@def derive_state_phase" }
```

Or extract a real snippet first and attach it as `code`:

```bash
python scripts/extract.py --root <repo> --refs refs.json --out code.json
```

`extract.py` searches ±3 lines around the declared line. **No whole-file fallback on purpose**: a short token can match unrelated code thousands of lines away, and silently quoting the wrong source is worse than reporting a broken reference.

### 1e. Write the model

See `assets/model.template.json`. Minimum shape:

```json
{
  "title": "…", "root": "overview",
  "diagrams": {
    "overview": {
      "title": "…", "w": 1200, "h": 520,
      "nodes": [{ "id": "a", "x": 40, "y": 150, "w": 220, "h": 110,
                  "title": "Cart", "lines": ["items chosen"], "drill": "cart-inside" }],
      "edges": [{ "from": "a", "to": "b", "fs": "r", "ts": "l", "label": "order.draft" }]
    },
    "cart-inside": { "title": "Cart, inside", "parent": "overview", "w": 900, "h": 320,
                     "nodes": [], "edges": [] }
  },
  "story": [{ "beat": "Day 1 …", "node": "a", "text": "…" }],
  "sections": { "a": { "what": "…", "why": "…", "for": "…", "how": "…", "trap": "…" } }
}
```

## Step 2 + 3 — Draw and explain

One command writes both files:

```bash
node scripts/build.mjs --in model.json \
  --out 图文讲解.html \
  --diagram 链路图.html
```

`--diagram` is optional; without it the second file is `<out>-diagram.html`. `--no-diagram` skips it.

The build **validates and exits 1** on: a `drill` naming a diagram that does not exist, an edge endpoint that is not a node, a `sections` key that is not a node, a `story`/`stories` beat naming a missing node **or a missing edge**, a scenario with no beats, or a `root` that does not exist.

Then check both files:

**`链路图.html`** — the diagram with the whole viewport.
- It fills the screen and does **not** scroll. That is correct here.
- Clicking `⧉` opens the sub-diagram; `Esc` goes back.
- `/` searches boxes; `0` re-fits; `T` toggles theme.

**`图文讲解.html`** — the scrolling document.
- The page **scrolls** to 16 cards. If it does not scroll, the vendored `html,body{height:100%;overflow:hidden}` won the cascade. The build emits `html,body{height:auto;min-height:100%;overflow:visible}` in `extraCss` to beat it — **keep that rule**.
- The diagram draws **inside** its box, 660px tall. (The vendored CSS pins `#bar`/`#stage` to the viewport; `.graphbox` overrides both.)
- Clicking a box **with a section** scrolls to its card. Clicking its `⧉` opens the sub-diagram in place. These must not both fire.

## Two traps in this shell, both silent

Both produce a page that looks fine at a glance. Neither breaks the build.

**1. The document does not scroll.** The vendored CSS is written for a full-viewport app and locks `html, body` to `height:100%; overflow:hidden`. Wrap that CSS in a document without overriding it and the page is pinned to one screen: the diagram and every card below it are unreachable. One rule in `extraCss` fixes it; deleting that rule silently re-breaks it.

**2. One click does two things.** The renderer navigates on `pointerup`, and it calls `svg.setPointerCapture()` on `pointerdown` — so by the time `pointerup` fires, the event target is the svg itself, not the box you pressed. Getting the bridge right needs all three of:

- listen on `document` in the **capture** phase, not on the svg (on the target element, capture and bubble listeners fire in *registration* order, and the renderer registered first, so your capture listener runs second);
- listen for `pointerup`, not `click` (a `click` arrives after the renderer has already drilled);
- record which node was under the pointer on `pointerdown`, because pointer capture has already replaced the target by `pointerup`.

Get any one of them wrong and clicking a box with a card both drills in *and* scrolls to the card, or drifts into the wrong sub-diagram. The `⧉` glyph must still fall through to the renderer, or the page loses its entire sub-diagram layer.

A third, smaller one: the renderer rewrites `document.title` to `<diagram> · Interfold blueprint` on every navigation. The build injects a `MutationObserver` **before** the renderer to pin the title back.

A headless check catches the failures that a build cannot — the build proves the model is consistent, not that the page works:

```python
# pip install playwright && playwright install chromium
# open both files, then assert these six things:
#   图文讲解: scrollHeight > innerHeight        (page scrolls)
#   图文讲解: click ⧉ -> location.hash changes  (drill works)
#   图文讲解: click a box with a card -> scrollY > 500 AND hash unchanged
#   链路图:   #stage height > innerHeight       (fills the viewport)
#   链路图:   node count > 0 and path count > 0 (something was drawn)
#   both:     no pageerror
```

Both of the traps below were found by exactly that check, after builds that exited 0.

## Altitude — the one judgement call that decides whether it works

| Goal | Top level shows | Each box opens into |
|---|---|---|
| **Getting up to speed on a project** | Business stages | That stage's steps and parameters |
| **A business flow** | Actors and handoffs | That actor's internal pipeline |
| **A codebase** | Services and stores | That service's modules, then functions |
| **A single process** | Steps and decision gates | A step's sub-steps |

Rules:

- **Top level: 5–9 boxes.** More means you are one level too deep.
- **One altitude per diagram.** Never put an implementation detail beside a stage.
- A box with nothing worth opening stays terminal — not every box needs a sub-diagram.
- When a reader asks "what's inside this?", the answer is a **drill target**, not a bigger box.

## The four questions

Every node with a section must answer:

| Question | Answers | Does not answer |
|---|---|---|
| **是什么** | "The only node that can answer 'what can I reach with this score'." | "Handles score queries." |
| **为什么** | "Without it the system is just a chatbot." | "To improve user experience." |
| **有什么用** | "Produces a candidate range with sources, for the verifier to check." | "Returns results." |
| **怎么用** | "In: province + year + subject + score. Out: rank and reachable schools, each with a version stamp." | "Takes input, returns output." |

**为什么 is the filter.** If you cannot state the failure this node prevents, the node is implementation detail — demote it into a sub-diagram or into another node's `坑`.

The optional **坑** row names the specific trap the node guards against. It is usually the most valuable line on the card.

## Scenarios — the part that proves you understood the branches

A flow diagram is never one line. If your model has eight nodes and only one path through them, either the system is a straight line (rare) or **you have not modelled the branches**.

**Draw the branches first.** Every real pipeline has at least three kinds of edge that a naive walkthrough omits:

| Branch | Ask yourself | Typical edge |
|---|---|---|
| **Refusal** | What does the gate do when the check fails? | `gate -> refuse`, dashed, labelled with the rule that fired |
| **Failure / void turn** | What happens when the data cannot be trusted? | `verify -> block`, dashed |
| **Retry** | Where does a stale input send you back to? | `verify -> query`, dashed, back-edge |
| **Concurrency** | What if two writers race? | `cas -> intent`, dashed, back-edge |
| **Read-only** | What if the user never enters the pipeline at all? | `user -> askonly` |

A dashed back-edge that returns to an earlier node is the single most informative thing on the diagram: it says "this can happen twice, and the second time is not the first time".

### Then write one scenario per branch

`stories` is a list of named scenarios. Not one story with a branch mentioned in passing — **one concrete person per branch**, each with a name, a situation, and a reason the situation is hard.

```json
"stories": [{
  "id": "deny", "name": "小李要「山东的全删了」——第三层拦下", "kind": "拒绝",
  "sub": "系统不直接改，先出一张提案，说清代价。",
  "setup": "小李已经有一版 30 条的方案，目标数量也是 30。",
  "beats": [{ "beat": "第三层拦下：改完只剩 23 条", "node": "guard",
              "edge": "guard->decline", "text": "原因是 target_count_mismatch……" }],
  "ends": "他看到的是「影响 7 条」，不是一个被默默执行的删除。"
}]
```

| Field | Why it earns its place |
|---|---|
| `name` | A person and a specific situation, not "the rejection case" |
| `kind` | `主路径` / `拒绝` / `回退` / `并发` / `边界` / `只读` — drives colour, and forces you to notice which kinds you have none of |
| `setup` | The starting state that makes this branch reachable. A branch nobody can get into is not a branch. |
| `setup` must include the number | "目标数量也是 30" is why the rule fires. Without it the story is a claim. |
| `edge` | **The verification hook** — see below |
| `ends` | What the person actually receives. Not "it fails": what they see. |

Beat rules: each beat names the node it hits *and* the edge it crosses (both become clickable / bold). One beat per real decision. End with what the person never had to know.

### Coverage is computed, never asserted

Every beat may declare `"edge": "a->b"`. The build then counts which of the diagram's edges any scenario walks, prints `N/M 条链路被场景走到` at the top of the page, and lists the unreached ones in a red disclosure.

That number is the point. A build that says **28/28** has demonstrably exercised every arrow you drew. A build that says **1/22** means you wrote a story and then drew a diagram, and the two are barely related.

Coverage is **reported, not enforced** — an unreached edge can be legitimate. But it must be visible, because an unreached edge is usually either a scenario you forgot or a box nobody uses.

The build **exits 1** on a beat naming an edge that does not exist, so `edge` cannot drift away from the diagram.

A single `"story"` array still works and becomes one scenario named 主路径. Use `stories` as soon as there is more than one path.

## Data reference

### Diagram
| Field | Meaning |
|---|---|
| `title`, `sub`, `crumb` | Heading, one-line description, breadcrumb label |
| `w`, `h` | Canvas size in diagram units — size to content, not to a screen |
| `parent` | Parent diagram id (drives Esc and the breadcrumb) |
| `nodes`, `edges` | Below |
| `bounds` | Dashed boundary regions `{x,y,w,h,label}` |
| `groups` | Light grouping rectangles |
| `notes` | Free text `{x,y,text,anchor}` |

### Node
| Field | Meaning |
|---|---|
| `id`, `x`, `y`, `w`, `h` | Identity and geometry |
| `title`, `lines` | Bold line, then small lines |
| `tag` | Uppercase tab above the box |
| `drill` | Another diagram's id — the box gets `⧉` |
| `ref` | `path@line@token` — the box gets `</>` |
| `code` | Inline `{path, start, lines[], more}` excerpt |
| `tip` | Hover text |
| `mono`, `style` | Monospace / `chip` / `tagged` |

### Edge
| Field | Meaning |
|---|---|
| `from`, `to` | Node ids |
| `fs`, `ts` | Exit / entry side: `l` `r` `t` `b` (default `r` / `l`) |
| `fa`, `ta` | 0–1 position along that side |
| `via` | Explicit waypoints `[[x,y], …]` |
| `label` | **The payload name** — drawn at the longest segment |
| `dashed`, `both`, `none` | Style |
| `refs`, `tip` | Code references, hover text |

### Section
| Field | Meaning |
|---|---|
| `what`, `why`, `for`, `how` | The four questions |
| `trap` | The specific failure this node prevents |
| `name`, `meta` | Card title, `file:line` badge |
| `refs` | `[{label, path, line, snippet:[{n,text,hit}]}]` |

## Anti-patterns

| Do not | Why |
|---|---|
| Start by reading source files | You will model the file tree instead of the flow |
| Draw an arrow without a payload name | Unfalsifiable; nothing learned |
| Answer 为什么 with "for user experience" | Not a failure mode; filters nothing |
| Put 15 boxes on the top level | You are one level too deep |
| Hand-type code into a ref | A paraphrase looks authoritative and is wrong |
| Ship the diagram without the four questions | Structure without causality |
| Give every node a section | Terminal boxes need none; 16 cards is already a lot |
| Mix altitudes in one diagram | The reader cannot tell a stage from an implementation detail |

## Reporting limits honestly

State these when you deliver, because they are true:

- The pages reflect **your model**, not a complete inventory of the system.
- A `drill` target shows **what you chose to model**, not everything inside.
- A code ref proves **the cited line exists and matches the token** — not that the surrounding logic does what your prose says.
- A green build means **no broken structure and no missing files**, not that the system is correct.
- Line numbers drift as code changes; re-extract before trusting an old page.
- Two files from one model means **they agree**, not that either is complete. Fix the model, rebuild — never patch one HTML by hand.

## Reference

- `assets/model.template.json` — starting point.
- `assets/refs.template.json` — code reference format.
- `references/modelling-guide.md` — finding stages, naming payloads, branches, loops, async work, and which claims are worth verifying.
- `scripts/build.mjs` — validates the model, draws it, writes **both** pages.
- `scripts/extract.py` — pulls real source lines and checks references.
- `scripts/flow/` — vendored Blueprint renderer and CSS (LGPL-3.0, see `scripts/flow/LICENSE.md`).
