# Manual classifier trace — verifying the system prompt's logic by hand

Walking each test case against the rules in classifier_system_prompt.md exactly as
written, to verify discrimination before any live API wiring.

## Felix (control)
Message: "lol this module wrecked me but got there in the end"
History: active, on track.
Rule check: "Normal venting or jokes about difficulty that fit the typical tone...
is not a flag." Single joke, otherwise engaged. -> risk_types: [] -- PASS, no
false positive.

## Aida (academic)
Message: "also still confused about the same closures thing from last week"
History: behind on sheet (module 2 vs expected 4), second time asking.
Rule check: "repeated + unresolved + behind on curriculum position" is explicitly
the academic trigger condition. -> risk_types: ["academic"], confidence: high.
PASS.

## Esther (withdrawal)
Message: none this week.
History: week 1 highly active -> week 3 silent, own baseline comparison available.
Rule check: "withdrawal requires message history context... never infer from a
single message alone" -- satisfied, we have 3 weeks of contrast. -> risk_types:
["withdrawal"], confidence: high. PASS.

## Carmen (confidence)
Message: "maybe i'm just not cut out for this" + comparison language ("everyone
else", "compared to everyone else").
History: ON TRACK on the sheet.
Rule check: comparison language is the distinguishing signal for confidence,
explicitly independent of curriculum standing. -> risk_types: ["confidence"],
confidence: medium-high. Critically should NOT also fire "academic" since there's
no expressed confusion about a concept, only self-doubt. PASS if classifier
keeps these separate -- this is the trickiest discrimination to verify once live.

## Brian (overload)
Message: "my kid's been sick, trying to catch up" -- time/life pressure, zero
content-confusion language.
Rule check: "overload is not academic... never relabel one as the other."
-> risk_types: ["overload"]. Must NOT fire academic. PASS if kept distinct.

## Daniel (isolation)
Message: none of substance, just silent submissions.
History: ON TRACK, but zero #module-help activity, no reactions, no replies.
Rule check: "isolation can apply with ZERO academic or overload signals... do not
require another risk type to be present." -> risk_types: ["isolation"],
confidence: low-medium (explicitly the hardest to call with certainty).
PASS if classifier resists pulling this toward "no signal" just because he's on
track academically -- this is the case most likely to be missed by a naive
classifier that only looks at curriculum position.

## Summary of what this trace is actually testing
The five categories are designed to be mutually exclusive on these six cases by
construction. The real risk once this runs live against an LLM is:
1. Carmen and Aida both involve "struggle" language -- does the model correctly
   route Carmen to confidence and not academic? This is the single most important
   case to manually verify once you have live API access.
2. Daniel is the easiest case to silently fail on, since most naive approaches
   would treat "on track + submits on time" as no signal. Isolation only fires if
   the classifier is actually checking the secondary engagement metric (replies,
   reactions), not just submission status -- worth a deliberate test before the
   demo.
3. Felix passing (staying silent) is just as important to demo as any flag firing
   -- it's the proof the system doesn't cry wolf.
