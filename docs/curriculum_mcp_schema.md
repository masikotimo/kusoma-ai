# Kusoma AI — Curriculum Tracking Source (MCP connection)

This is the external "ground truth" the agent checks informal Slack signal against.
Build this as a Google Sheet (connect via the Google Drive MCP server) or an Airtable
base — either works, Google Sheets is faster to stand up in a weekend.

## Sheet: `cohort_tracker`

| column              | type   | example          | purpose                                                  |
|---------------------|--------|------------------|-----------------------------------------------------------|
| learner_id          | text   | aida             | matches the Slack user/handle the classifier reports      |
| display_name        | text   | Aida K.          | for the coordinator-facing message                         |
| cohort_start_date   | date   | 2026-05-01       | used to compute "week N of program"                        |
| expected_module     | number | 4                | where the program plan says they should be by today        |
| current_module      | number | 2                | where they actually are, from their last submission        |
| last_submission_date| date   | 2026-06-10       | staleness check independent of module number                |
| prior_experience     | text   | none / some / experienced | sets the baseline-sensitivity per the "pre-cohort baseline" enrichment idea |
| assigned_mentor      | text   | sam              | who Kusoma AI pings for an academic-type flag               |
| coordinator          | text   | jane             | who Kusoma AI pings for overload / confidence / isolation / withdrawal flags |

## Sample rows (matching the six seed personas)

```
learner_id, display_name, cohort_start_date, expected_module, current_module, last_submission_date, prior_experience, assigned_mentor, coordinator
aida,    Aida K.,    2026-05-01, 4, 2, 2026-06-09, none,        sam,  jane
brian,   Brian O.,   2026-05-01, 4, 3, 2026-06-11, some,        sam,  jane
carmen,  Carmen R.,  2026-05-01, 4, 4, 2026-06-12, none,        priya, jane
daniel,  Daniel M.,  2026-05-01, 4, 4, 2026-06-12, experienced, priya, jane
esther,  Esther N.,  2026-05-01, 4, 2, 2026-05-20, none,        sam,  jane
felix,   Felix T.,   2026-05-01, 4, 4, 2026-06-12, some,        priya, jane
```

## Mentor topic-strength table (for the "specific mentor, not just any mentor" upgrade)

A second small sheet, `mentor_strengths`, used only when routing an academic flag —
this is what turns "ping a mentor" into "ping the mentor who's actually good at this
exact topic."

```
mentor, topic,      times_successfully_explained
sam,    closures,   3
sam,    recursion,  1
priya,  recursion,  4
priya,  async,      2
```

`times_successfully_explained` is incremented whenever a flagged learner re-engages
(posts again, moves to the next module) within some window after that mentor replied
to them on that topic — this is the self-correcting trust loop from the earlier
brainstorm, simplified to something codeable in a weekend: a counter, not a model.

## MCP read pattern

The agent's only read operations against this source:
1. Given a learner_id, fetch their row (current_module, expected_module, prior_experience).
2. Given a topic, fetch the mentor_strengths rows sorted by times_successfully_explained descending.

No write access is required for the hackathon MVP — keeping this read-only
simplifies both the build and the permissions story you'd tell judges (the agent
observes and recommends, it does not alter program records).
