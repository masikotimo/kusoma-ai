# Kusoma AI — Fusion & Routing Logic

This sits between the classifier output (classifier_system_prompt.md) and the final
Slack message. Input: one classification result + the matching curriculum_tracker
row. Output: one routed action, or no action.

## Step 1 — Gate: does this even warrant escalation?

Do not escalate on:
- `risk_types: []` (no signal)
- a single `academic` flag with `confidence: low` and the learner is AT or AHEAD of
  expected_module (asking a hard question while on track is just learning, not risk)

This gate exists specifically so the system doesn't nag a coordinator every time
someone asks a normal question. Silence is a feature, not a gap — see Felix.

## Step 2 — Route by risk type

Each risk type has exactly one routing path. This is the core design rule: never
let two different problems collapse into the same generic "this person needs help"
message, because the coordinator can't act on a vague flag the same way they can act
on a specific one.

### academic → mentor nudge
Condition to fire: `academic` in risk_types AND (repeated within the window OR
current_module < expected_module).
Action: query `mentor_strengths` for the topic mentioned, pick the top mentor by
times_successfully_explained (fallback: assigned_mentor from cohort_tracker if no
topic match exists yet). Send to that mentor, not the coordinator.
Message shape: "[Learner] has asked about [topic] more than once and is currently
on module [current] vs an expected [expected]. You've helped others with this
before — might be worth a quick check-in."

### overload → coordinator, flexibility-oriented
Condition to fire: `overload` in risk_types.
Action: route to coordinator, not mentor — a mentor explaining the material again
doesn't address a time/capacity problem.
Message shape: "[Learner] has mentioned time pressure outside the course twice
recently. Worth checking whether they need a deadline adjustment rather than more
material support."

### confidence → coordinator, reassurance-oriented
Condition to fire: `confidence` in risk_types.
Action: route to coordinator. Explicitly note in the message if curriculum data
shows they're ON TRACK — that's the most useful and counterintuitive part of the
flag.
Message shape: "[Learner] has expressed self-doubt comparing themselves to peers.
Worth noting: they're actually on track ([current]/[expected]) — this looks like a
confidence gap, not a skills gap."

### isolation → coordinator, light-touch
Condition to fire: `isolation` in risk_types, confidence >= medium OR sustained
over 2+ weeks at low confidence.
Action: route to coordinator with explicitly lower urgency framing, since this is
the least certain signal type.
Message shape: "[Learner] is keeping up with submissions but hasn't engaged
socially in cohort channels for [N] weeks. Not urgent, but might be worth a casual
check-in so they don't feel disconnected."

### withdrawal → coordinator, personal check-in
Condition to fire: `withdrawal` in risk_types.
Action: route to coordinator, marked higher urgency than isolation since this
combines silence with an actual activity drop-off against the learner's own
baseline.
Message shape: "[Learner] was highly active in week 1 and has gone quiet since
week [N]. This is a bigger change than their usual pattern — probably worth a
direct, personal message rather than another resource link."

## Step 3 — Multiple simultaneous flags

If a learner trips more than one risk type in the same window (e.g. academic +
overload), do not send two separate messages. Combine into one coordinator message
that names both, and let the coordinator decide priority — this avoids alert
fatigue, which is the fastest way a tool like this gets muted or uninstalled.

## Step 4 — Cohort-level pattern check (the "richer" upgrade from earlier)

Before routing an individual academic flag, check: have 2+ other learners also
been flagged academic on the SAME topic in the same window? If yes, change the
action entirely — instead of (or in addition to) pinging a mentor for one learner,
send the coordinator a separate, distinct message: "[Topic] has come up as a
point of confusion for [N] learners this week — might be worth revisiting in a
group session rather than one-on-one." This is what turns the tool from a
per-student alert system into a curriculum-quality signal as well.

## What this logic deliberately does NOT do

- It never sends anything to the learner directly. All output goes to a mentor or
  coordinator — a human decides the actual outreach.
- It never accumulates a persistent "risk score" attached to a learner's permanent
  record. Each window's classification is evaluated fresh; a learner who was
  flagged once and then re-engaged should not carry that flag forward as a
  reputation.
- It never escalates two different risk types to two different audiences in a way
  that could let one team see information another shouldn't (e.g. a mentor never
  receives an overload or confidence flag — those are coordinator-only, since they
  involve sensitive personal context a mentor doesn't need to do their job).
