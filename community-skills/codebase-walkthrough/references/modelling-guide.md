# Modelling guide

How to turn a codebase into a graph that is worth checking.

## Contents

1. [Finding stages](#finding-stages)
2. [Naming data](#naming-data)
3. [Branches](#branches)
4. [Loops and cost](#loops-and-cost)
5. [Async and background work](#async-and-background-work)
6. [Where verification actually lives](#where-verification-actually-lives)
7. [Worked example: a five-stage system](#worked-example)

---

## Finding stages

A stage is **a change in what the user can expect from the system**, not a folder.

Ask: "what can the system do now that it could not do a moment ago?" Each distinct answer is a boundary.

| Symptom in the code | Likely stage boundary |
|---|---|
| A completeness check on user-supplied facts | Before / after "we know who this is" |
| A cache or candidate pool being populated | Before / after "we have options" |
| A first persistent write | Before / after "something is now saved" |
| A version counter that starts mattering | Before / after "others may now conflict with us" |

Four to six stages is typical. Fewer and the graph hides real branching. More and it becomes a call graph.

**Bad stage names** describe code: "Services", "Handlers", "Controllers", "Phase 2".
**Good stage names** describe the user's situation: "Understand the user", "Offer candidates", "Build the plan", "Revise the plan".

Every stage needs a `why`: the reason the system cannot skip it. If you cannot state the reason, the stage may be an implementation detail — fold it into a node.

## Naming data

Edge names are the whole verification mechanism, so they carry the design.

Rules that keep them checkable:

- **Name the payload, not the action.** `evidence.raw` beats `queryRan`. The action is visible in the arrow; the reader needs to know what moved.
- **One name per shape.** If two nodes produce the same thing, use the same name — that is how a fan-in edge gets computed. If they produce different things, use different names even if the wording is similar.
- **Namespace with a dot.** `profile.complete`, `card.confirmed`, `plan.version`. It keeps labels short enough to read on an arrow and makes mismatches obvious.
- **Include the qualifier that matters.** `evidence.raw` vs `evidence.verified` is a real distinction and belongs in the name, not in a note.
- **Terminal names are still names.** Something returned to the outside world, or reported as an error, gets a name and `"to": null`. It marks the end of a chain instead of leaving it dangling.

Failure to match is informative. When `emits` says `card.pending` and the downstream `consumes` says `card.confirmed`, you have found that a confirmation step exists between them — the mismatch is telling you a node is missing, not that a string is wrong.

## Branches

Four kinds, all worth showing.

### Stage branch

The system behaves differently depending on state. Model the decision as a node that emits one name per mode, and give each mode its own downstream node.

```
[decide stage] --discover.state--> [understand the user]
              --candidates.state--> [query facts]
              --build.state-----> [build the plan]
```

If the decision is a priority-ordered cascade of checks, say so in `decision` — the order is the design.

### Action branch

One sentence, several operations. Each operation gets its own emitted name.

```
[understand "change"] --intent.add----> [guard]
                     --intent.replace-> [guard]
                     --intent.remove---> [guard]
```

This is often where the real risk lives: `add` and `replace` differ in whether the total changes, and getting it wrong is a silent data error, not a visible failure.

### Gate branch

A check that can stop the flow. The gate emits **both** outcomes, and the blocking outcome is a terminal.

```
[pre-checks] --gate.pass--> [build the plan]
            --gate.block--> (terminal: tell the user what is missing)
```

Show the block path. A model with only pass paths hides the most important design question: what does the system refuse to do, and what does it say instead?

### Loop

See below.

## Loops and cost

A node that emits into an earlier node's `consumes` is a loop. Two things must be modelled, or the graph lies about cost:

- **The loop bound.** "At most N iterations" belongs in `decision`. Without a bound, a loop is an unbounded cost.
- **The re-check on each pass.** If each iteration re-reads state (a version, a timestamp), say so. That re-read is usually the reason the loop is safe.

Loops are common in "think, call a tool, think again" shapes and in retry-with-revalidation shapes. Neither is a defect; hiding them is.

## Async and background work

The synchronous request path is not the whole system. When work is queued, model the queue as data:

```
[accept request] --job.queued--> [worker]
[worker]         --job.done---> [report back]
```

Two things to capture explicitly:

- **What is frozen at enqueue time** (inputs, an expected version). That freezing is what makes the job replayable.
- **What the worker re-reads on pickup.** If nothing, say so — that is a staleness risk worth surfacing in `trap`.

Also model the **recovery** path: what happens when the worker is asked about a job it has no record of. "Unknown" and "not yet done" are different answers and are often conflated.

## Where verification actually lives

Separate the two kinds of claim, because they carry different weight.

**Structural verification** — is the model internally consistent? Free, automatic, and it is what `build.mjs` does. It catches:

- an emitted name nothing consumes
- a consumed name nothing emits
- a node that is unreachable from any entry
- a cycle with no stated bound

**Behavioural verification** — does the code do what the node claims? Not free. Your options, cheapest first:

| Method | What it proves | Cost |
|---|---|---|
| Cite the enum / constant / schema | The vocabulary exists | One `grep` |
| Cite the guard clause | The rule is enforced at this point | One `grep` |
| Cite the branch that handles the refusal | The refusal is real | One `grep` |
| Trace a run and cite its output | The path executed | Running the system |
| A test asserting the postcondition | The behaviour holds under test | Writing a test |

Cite the **refusal** whenever a node claims to prevent something. A `trap` field without a citation to the guard that implements it is speculation.

Be explicit about the gap in your report: a reference proves a line exists; it does not prove the surrounding logic is correct.

## Worked example

A five-stage system with one branch and one loop:

```json
{
  "stages": [
    { "id": "s1", "name": "Identify the caller", "why": "nothing can be answered without knowing who is asking", "color": "#1e40af" },
    { "id": "s2", "name": "Load context",      "why": "the answer depends on state the caller cannot supply", "color": "#6d28d9" },
    { "id": "s3", "name": "Decide the path",   "why": "the same words mean different operations", "color": "#a16207" },
    { "id": "s4", "name": "Do the work",       "why": "this is the only stage that writes", "color": "#c2410c" },
    { "id": "s5", "name": "Report",            "why": "callers cannot see internal state", "color": "#15803d" }
  ],
  "nodes": [
    {
      "id": "n1", "stage": "s1", "no": "1", "title": "Resolve the caller",
      "consumes": [{ "name": "request.raw", "what": "credentials plus payload", "from": "external" }],
      "emits":    [{ "name": "caller.identified", "what": "verified identity", "to": "n2" }],
      "decision": "reject before accepting the connection, not after",
      "trap": "accepting first would open an anonymous channel"
    },
    {
      "id": "n2", "stage": "s2", "no": "2", "title": "Load a bounded context",
      "consumes": [{ "name": "caller.identified", "what": "verified identity", "from": "n1" }],
      "emits":    [{ "name": "context.loaded", "what": "a trimmed snapshot of current state", "to": "n3" }],
      "decision": "the server decides what the worker may see",
      "trap": "letting the worker fetch freely moves the cost and the blame to the wrong side"
    },
    {
      "id": "n3", "stage": "s3", "no": "3", "title": "Classify the request",
      "consumes": [{ "name": "context.loaded", "what": "trimmed state", "from": "n2" }],
      "emits": [
        { "name": "intent.read",  "what": "read-only request",       "to": "n4" },
        { "name": "intent.write", "what": "request that changes state", "to": "n5" }
      ],
      "decision": "anything that reads real data or changes state needs explicit confirmation",
      "trap": "treating a write as a read is how unsolicited changes ship"
    },
    {
      "id": "n4", "stage": "s4", "no": "4", "title": "Answer from cited data",
      "consumes": [{ "name": "intent.read", "what": "read-only request", "from": "n3" }],
      "emits":    [{ "name": "answer.cited", "what": "answer plus the evidence it used", "to": "n6" }],
      "decision": "every referenced fact must resolve against the ledger",
      "trap": "an unresolvable reference invalidates the whole turn rather than the one sentence"
    },
    {
      "id": "n5", "stage": "s4", "no": "5", "title": "Execute behind a confirmation",
      "consumes": [{ "name": "intent.write", "what": "request that changes state", "from": "n3" }],
      "emits":    [{ "name": "change.receipt", "what": "structured result of the write", "to": "n6" }],
      "decision": "the worker may propose; only the server applies, and only after an explicit click",
      "trap": "a worker's prose saying 'done' is not a receipt"
    },
    {
      "id": "n6", "stage": "s5", "no": "6", "title": "Report terminal state",
      "consumes": [
        { "name": "answer.cited",   "what": "answer with evidence", "from": "n4" },
        { "name": "change.receipt", "what": "write receipt",        "from": "n5" }
      ],
      "emits": [{ "name": "response.final", "what": "the authoritative reply", "to": null }],
      "decision": "failures are reported through the same channel as successes",
      "trap": "a success-only channel lets a failed write look like a successful one"
    }
  ]
}
```

What this model demonstrates:

- **Fan-out** at `n3` (two intents) and **fan-in** at `n6` (two producers, both consumed).
- **A gate** expressed as two named outcomes rather than a note.
- **`n6` consumes two names**, so two edges are computed into it automatically — no line was drawn by hand.
- Every `trap` names a failure that the node exists to prevent. That is the field a reader learns the most from.

Add `refs.json` entries for the guard clauses in `n1`, `n3`, and `n5`, and the model becomes checkable rather than merely plausible.
