# End-to-end trace — classifier output -> curriculum row -> routed message

Two full walkthroughs, tracing every file in this build against each other, to
verify the pipeline is internally consistent before any live coding.

---

## Trace 1 — Aida (academic)

**Classifier output** (per classifier_system_prompt.md rules):
```json
{
  "learner_id": "aida",
  "message_excerpt": "still confused about the same closures thing from last week",
  "risk_types": ["academic"],
  "confidence": "high",
  "reasoning": "asked about the same concept twice without resolution"
}
```

**Curriculum row** (from curriculum_mcp_schema.md):
`current_module: 2, expected_module: 4` -> behind.

**Gate check** (fusion_routing_logic.md Step 1): academic + confidence high + behind
schedule -> escalation fires, does not get filtered out.

**Routing** (Step 2, academic path): topic = "closures". Query mentor_strengths ->
sam has times_successfully_explained: 3 for closures, highest match. Route to sam,
not coordinator jane.

**Final message to mentor sam:**
> Aida has asked about closures more than once and is currently on module 2 vs an
> expected 4. You've helped others with this before — might be worth a quick
> check-in.

Consistent end to end. PASS.

---

## Trace 2 — Daniel (isolation)

**Classifier output:**
```json
{
  "learner_id": "daniel",
  "message_excerpt": "(no substantive message — pattern-based)",
  "risk_types": ["isolation"],
  "confidence": "medium",
  "reasoning": "on-time submissions but no engagement in module-help or reactions across 3 weeks"
}
```

**Curriculum row:** `current_module: 4, expected_module: 4` -> on track.

**Gate check:** isolation flags are never gated on curriculum position per Step 1 —
only the academic-low-confidence exception checks curriculum standing. Isolation
proceeds regardless of being on track, which is the entire point of this category.
Escalation fires.

**Routing** (Step 2, isolation path): routes to coordinator jane, NOT mentor priya
(Daniel's assigned mentor) — confirms the rule that academic flags go to mentors
but isolation/overload/confidence/withdrawal stay coordinator-only, since priya
doesn't need personal-context information to do her job.

**Final message to coordinator jane:**
> Daniel is keeping up with submissions but hasn't engaged socially in cohort
> channels for 3 weeks. Not urgent, but might be worth a casual check-in so they
> don't feel disconnected.

Consistent end to end. PASS. This trace is the one most worth re-running once you
have live API access, since Daniel is the case most likely to be silently dropped
by a less careful implementation (an engineer might reasonably ask "why alert on
someone who's on track and submitting on time?" — the answer lives entirely in the
isolation-category design, not in the curriculum data).

---

## What's left before this is actually buildable code

1. Decide where the "history/context" string fed to the classifier comes from in
   practice — for the hackathon, this can be a simple rolling window (e.g. last 10
   messages per learner per channel, pulled via RTS) rather than a full
   conversational memory system. Keep this simple; it doesn't need to be elegant,
   it needs to demo correctly.
2. The mentor_strengths increment logic (Step 4 of fusion_routing_logic.md and the
   table in curriculum_mcp_schema.md) is the one piece that needs a "did the
   learner re-engage afterward" check — for the demo, this can be entirely faked
   /hardcoded rather than actually computed live, since proving the concept matters
   more than proving the learning loop in a 3-minute video.
3. The cohort-level pattern check (Step 4 of routing) needs a simple counter keyed
   by topic + week — straightforward to implement, and worth including in the demo
   since it's one of the strongest "richer" differentiators from the brainstorm.
