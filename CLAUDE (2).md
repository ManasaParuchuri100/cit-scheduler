# CIT Scheduler

Campus scheduling and venue app for the fictional Chilika Institute of Technology (hackathon project).
FastAPI backend, OR-Tools CP-SAT solver, a vanilla JS single page app. No build step.

## Run it

    bash run.sh            # installs requirements, serves http://localhost:8000
    bash restart.sh        # kills anything on :8000 and starts a fresh server (log in /tmp/cit-server.log)

Demo password for every account is `demo`. Accounts: `dean@cit.example` (Admin), `coordinator.<dept>@cit.example`
(cse, ece, ee, me, ce), `faculty.<id>@cit.example` (for example `faculty.f01@cit.example`), `club.<slug>@cit.example`.
The login screen lists them all.

Restart the server after any change in `cit/`. Changes in `web/` only need a browser refresh.

## The one rule that matters

`validator.py` is the official checker and it wins any argument. Exports (`exports/schedule.json`,
`exports/schedule_after.json`) must give 0 hard violations. Check with `python -m cit.cli check`
(also `generate` and `apply examples/sample_disruption.json`). Current result: 0 hard, booking score 67/70.

Things that are deliberately kept OUT of `schedule.json`: online guest lectures, exam-week extra classes,
one-day swaps. They are not part of the weekly pattern.

## Layout

- `cit/api.py` HTTP endpoints, role checks, timetable and overview views
- `cit/store.py` all state (`Store`), JSON persistence in `var/state.json`, exports, past-event clean-up (`purge_past`)
- `cit/collab.py` class swaps (`CollabMixin`), online lectures, exam-week extra classes (`ExtraMixin`)
- `cit/timetable.py` CP-SAT timetable model. `cit/exams.py` exam scheduler. `cit/bookings.py` booking priority and room decisions
- `cit/repair.py` disruption repair with a diff. `cit/parser.py` plain-English and Hinglish request reader
- `cit/assistant.py` optional Claude call, used only if `ANTHROPIC_API_KEY` is set (see `.env.example`). Rules-based reader works without it
- `web/app.js`, `web/app.css`, `web/index.html` the whole front end. Views are `VIEWS.<tab>`, clicks go through one
  `data-act` switch near the end of `app.js`
- `data/cit_public.json` the dataset, `data/seed_state.json` the ready-made timetable loaded on first start
- `tests/` see below. `README.md`, `AI_USAGE.md`, `THIRD_PARTY.md` are part of the judged deliverable, keep them current

## Behaviour to keep

- Priority: Exams > Regular classes > Institute events > Guest lectures > Department events > Club events. Nobody approves their own request.
- Roles: Admin (Dean's office), Department coordinator, Faculty, Club representative. Each sees only its own tabs.
- Swaps are for ONE week by default (week picker, with real dates). "Every week" is a separate choice and goes through the validator.
- Exam-week extra classes: only exams are hard blocks. Every other rule is a soft warning with points.
- Events whose time has passed are deleted automatically. Past fest-week bookings go to `Store.archive` so the export stays complete.
- Undo (Admin, `Store.undo_change` / `undo_swap`): only the newest approved change can be undone. A snapshot (`self.undo`) is taken just before a change is applied. Undo restores it, re-runs `validator.py` and refuses (changing nothing) if hard problems rise.
- Repeating bookings: `repeat_until` on `POST /api/bookings` makes one request per week (ids `BR-nn` plus a letter, shared `series_id`). Exam week and past weeks are skipped, max 26. One approval for the series is `POST /api/bookings/series/{id}/publish`.
- First start loads `data/seed_state.json`. "Use the ready-made timetable" on the Admin overview reloads it (`POST /api/seed`).
  Generating from scratch takes 40 s to a minute. Do not shorten the solver time limit, the timetable gets much worse.

## Tests

Start the server first (`bash restart.sh`). These reset the server state, so run `POST /api/seed` as admin afterwards
(or press the button) to get the demo state back.

    python tests/api_flow.py    python tests/collab_flow.py   python tests/oneday_flow.py
    python tests/extra_flow.py  python tests/purge_flow.py    python tests/logic_flow.py   python tests/test_parser.py
    python tests/undo_flow.py   python tests/recurring_flow.py
    python tests/ui_flow.py OUT_DIR   python tests/ui_logic.py OUT_DIR   python tests/shots.py OUT_DIR   # Playwright
    python tests/ui_undo.py OUT_DIR   python tests/ui_recurring.py OUT_DIR   # Playwright. Run suites one at a time, they share the server state

## Style

Plain and professional, not "AI-looking". No emojis. Palette: cream background, slate primary `#3B4D5F`, rose accent.
Fonts are bundled in `web/fonts` (DM Sans body, Source Serif 4 headings), so nothing loads from the internet.
Every subject has its own colour in timetable views (`setSubjects` / `subjCol`). Keep copy short and in plain words.
