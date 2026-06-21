# HackathonSlackTim — Sandbox member IDs

Workspace: **HackathonSlackTim**

Use these IDs in the Google Sheet (`slack_user_id` column), routing config, and `/kusoma scan` wiring.

---

## Cohort roles (demo)

| Display name | learner_id | Slack member ID | Role | Demo risk type |
|---|---|---|---|---|
| Jane K. (Coordinator) | `jane` | `U0BBZHB3CV7` | Coordinator — receives overload / confidence / withdrawal DMs | — |
| Sam M. (Mentor) | `sam` | `U0BBRBDHKDH` | Mentor — receives academic nudges; posts in `#module-help` | — |
| Aida K. | `aida` | `U0BBUA2QFC5` | Learner | Academic → routes to Sam |
| Brian O. | `brian` | `U0BBVKNLF0E` | Learner | Overload → routes to Jane |
| Carmen R. | `carmen` | `U0BBXMWT2RY` | Learner | Confidence (on track) → routes to Jane |
| Esther N. | `esther` | `U0BCS0Q1S56` | Learner | Withdrawal (history vs silence) → routes to Jane |

---

## Judges (do not use in demo personas)

| Display name | Slack member ID | Email |
|---|---|---|
| slackhack | `U0BBZSALJLR` | slackhack@salesforce.com |
| testing | `U0BBGH2C9UP` | testing@devpost.com |

---

## Curriculum sheet rows (`cohort_tracker`)

Copy into Google Sheet. `assigned_mentor` / `coordinator` are logical IDs — map to Slack IDs above when sending DMs.

| learner_id | slack_user_id | display_name | expected_module | current_module | last_submission_date | assigned_mentor | coordinator |
|---|---|---|---|---|---|---|---|
| aida | U0BBUA2QFC5 | Aida K. | 4 | 2 | 2026-06-09 | sam | jane |
| brian | U0BBVKNLF0E | Brian O. | 4 | 3 | 2026-06-11 | sam | jane |
| carmen | U0BBXMWT2RY | Carmen R. | 4 | 4 | 2026-06-12 | sam | jane |
| esther | U0BCS0Q1S56 | Esther N. | 4 | 2 | 2026-05-20 | sam | jane |

Staff DM targets:

| logical id | slack_user_id | display_name |
|---|---|---|
| jane | U0BBZHB3CV7 | Jane K. (Coordinator) |
| sam | U0BBRBDHKDH | Sam M. (Mentor) |

---

## Mentor strengths (`mentor_strengths` sheet)

| mentor | topic | times_successfully_explained |
|---|---|---|
| sam | closures | 3 |
| sam | recursion | 1 |

---

## Channels to create

| Channel | Purpose |
|---|---|
| `#module-help` | Aida, Carmen, Esther (week 1), Sam replies |
| `#standup` | Brian check-ins |
| `#general` | Brian, Carmen, Esther (week 1) |
| `#kusoma-log` | Optional — Kusoma posts scan summaries for demo |

Invite `@kusoma` to each cohort channel after creation.

---

## Setup checklist

- [x] Rename sandbox users (Jane, Sam, Aida, Brian, Carmen, Esther)
- [x] Copy member IDs into this doc
- [x] Invite judges (slackhack, testing)
- [ ] Create `#module-help`, `#standup`, `#kusoma-log` (reuse `#general`)
- [ ] `/invite @kusoma` in each cohort channel
- [x] Seed messages (see `seed_cohort_data.md` — Aida, Brian, Carmen, Esther only)
- [ ] Create Google Sheet + paste rows from `config/*.csv` (see `docs/google_sheet_setup.md`)
- [x] Wire RTS + classify + route + DM (`/kusoma scan`)
