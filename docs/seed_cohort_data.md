# Kusoma AI — Seed Cohort Data

Six learner personas across a 3-week window in a fictional 8-week training cohort.
Each persona is built to cleanly exercise ONE primary risk type, plus one control
persona with no risk signal, so the classifier's discrimination can be verified
persona-by-persona in the demo.

Channels: #general, #module-help, #standup
Curriculum source (the MCP-connected sheet) tracks: current_module, expected_module,
last_submission_date — this is the external "ground truth" the agent cross-checks
informal chat against.

---

## Persona 1 — Aida — ACADEMIC risk

Curriculum sheet: current_module = 2, expected_module = 4 (behind)

[Week 2, #module-help] Aida: hey does anyone know how closures actually work? like i
read the doc twice

[Week 2, #module-help] Mentor_Sam: closures let a function remember variables from
where it was created :)

[Week 3, #module-help] Aida: sorry me again — i still don't really get closures, is
it like the function just keeps a copy of the variable?

[Week 3, #module-help] Aida: also still confused about the same closures thing from
last week, did anyone else struggle with this

Expected classification: academic, medium-high confidence (repeated, unresolved,
confirmed behind on the sheet).

---

## Persona 2 — Brian — OVERLOAD risk

Curriculum sheet: current_module = 3, expected_module = 4 (slightly behind)

[Week 2, #standup] Brian: not gonna lie, work's been insane this week, barely
touched the material

[Week 3, #standup] Brian: sorry for going quiet, my kid's been sick, trying to catch
up this weekend

[Week 3, #general] Brian: is the deadline flexible at all? life's just a lot right
now

Expected classification: overload, medium-high confidence. Should NOT be classified
as academic — Brian never expresses confusion about content, only time/capacity.

---

## Persona 3 — Carmen — CONFIDENCE risk

Curriculum sheet: current_module = 4, expected_module = 4 (on track)

[Week 2, #general] Carmen: everyone in here seems to just get this so fast, kind of
intimidating lol

[Week 3, #module-help] Carmen: i finished the exercise but it took me forever
compared to everyone else, maybe i'm just not cut out for this

[Week 3, #general] Carmen: probably a dumb question but here goes... (proceeds to ask
a perfectly reasonable question)

Expected classification: confidence, medium-high confidence. Note: Carmen is ON
TRACK on the curriculum sheet — this demonstrates that confidence-risk is detectable
independent of actual academic standing, which is the whole point of having it as a
separate category from academic risk.

---

## Persona 4 — Daniel — ISOLATION risk

Curriculum sheet: current_module = 4, expected_module = 4 (on track)

[Week 1, #general] Daniel: (submits assignment on time, no message)
[Week 2, #general] Daniel: (submits assignment on time, no message)
[Week 3, #general] Daniel: (submits assignment on time, no message)

No messages in #module-help across 3 weeks. No reactions, no replies to others,
despite being active in the channel list (read receipts show Daniel viewing
messages).

Expected classification: isolation, low-medium confidence (this is the hardest to
detect with certainty — flagged for a gentle, non-alarming check-in, not an urgent
escalation). Should NOT be flagged academic or overload — nothing in his behavior
suggests either; the signal is purely social absence despite being on track.

---

## Persona 5 — Esther — WITHDRAWAL risk

Curriculum sheet: current_module = 2, expected_module = 4 (behind)

[Week 1, #module-help] Esther: hi all, excited to start! quick question about the
setup steps — (asks a clear, engaged question)
[Week 1, #general] Esther: (posts 4 more messages that week, engaged and active)
[Week 2, #general] Esther: (1 short message)
[Week 3] Esther: (no messages at all)

Expected classification: withdrawal, high confidence — requires comparing week 1
baseline (highly active) against week 3 (silent) for the SAME learner, not against
cohort average. This is the case that proves the "own baseline, not group average"
design decision actually matters.

---

## Persona 6 — Felix — CONTROL, no risk signal

Curriculum sheet: current_module = 4, expected_module = 4 (on track)

[Week 2, #general] Felix: lol this module wrecked me but got there in the end

[Week 2, #module-help] Felix: anyone else think the async section was way easier
than people made it sound

[Week 3, #standup] Felix: shipped the project, onto the next one 🚀

Expected classification: no signal. This persona exists specifically to prove the
classifier does NOT over-flag normal venting, banter, or casual tone as risk — Felix
jokes about difficulty exactly once, in an otherwise clearly engaged, on-track
pattern, which the system prompt explicitly calls out as not a flag.

---

## Demo sequencing recommendation

Run the personas in this order for the live demo, narrating as each fires:
1. Felix first — show the agent correctly stays silent on normal chatter (proves
   it's not trigger-happy)
2. Aida — academic flag, routed to a mentor with the specific topic named
3. Esther — withdrawal flag, routed to coordinator as a personal check-in, NOT a
   mentor ping, since a mentor can't fix silence
4. Carmen — confidence flag, on an otherwise on-track learner, to show the system
   catches what curriculum data alone would miss entirely
5. (Optional, if time allows) Brian and Daniel as a quick "and it also distinguishes
   these two from each other" close
