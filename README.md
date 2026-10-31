# CIT Scheduler (Crunch Week)

A working campus scheduling and venue app for the Chilika Institute of Technology.
It builds the weekly timetable (189 sessions), the midsem exam schedule (41 exams) and the
Spectra week booking decisions, takes room requests in plain English or Hinglish, repairs the
timetable with the fewest moves when something changes, and exports `schedule.json` and
`schedule_after.json` that the official `validator.py` accepts.

## Run it

    ./run.sh                    # then open http://localhost:8000

Needs Python 3.9+ (`pip install -r requirements.txt` is done by `run.sh`).
Optional: `export ANTHROPIC_API_KEY=...` to let Claude read booking requests.
Without a key the built-in reader is used. Either way the result lands in an editable form.

First screen after signing in as the Dean's office: press **Generate everything** (about 40 s).

## Sign in (password for all: `demo`)

| Role | Accounts | Tabs |
|---|---|---|
| Admin | dean@cit.example, registrar@cit.example | Overview, Timetable, Rooms, Bookings, Changes, Exams |
| Department coordinator | coordinator.cse / ece / ee / me / ce @cit.example | Overview, Timetable, Rooms, Bookings, Changes |
| Faculty | faculty.f01 … f40 @cit.example | Overview, My timetable, Away & requests |
| Club representative | club.coding / robotics / dance / quiz / … @cit.example | Overview, Find a room, New request, My requests |

Every Overview starts with the priority order (Exams > Regular classes > Institute events > Guest
lectures > Department events > Club events) and highlights the highest level your role may ask for,
then shows the class information for that role.

There are two admin accounts on purpose: nobody can approve their own request, so a second admin is needed.

## Ask in plain words (the Ask button, every role)

One box understands three kinds of message. Nothing it does changes data by itself.

* **A room request** ("seminar hall kal shaam 6 baje, 2 ghante, 100 log, mic chahiye") fills the editable booking form.
* **A timetable request** ("I am away Thursday morning", "move my Digital Logic Design lecture to Wednesday afternoon",
  "Dr. Ananya Mishra is on leave Monday") becomes a draft change. The app shows whether that time is free, what would
  have to move, and the nearest times that work. If the time breaks a rule it says which rule. It is then sent to the
  Dean's office for approval and only applied after the checker passes.
* **A question** ("why is CS101 at 8 AM?", "why was BR-14 rejected?") is answered by code from the real timetable and rules.

In the Timetable, the left panel filters by subject (one subject across the week), by type (lecture, tutorial, lab, event), and has a Subject view that shows every section of one course.

Clicking any class in a timetable opens the same two things: why it is where it is, and a Move panel that lists every
time as free, possible if another class moves, or ruled out (with the reason).

Admins can also load a dataset file (same format as `cit_public.json`) from the Overview.

## Architecture

    Browser (web/, no build step)
        |  JSON over HTTPS, bearer token
    FastAPI (cit/api.py) -- roles, approvals, audit (cit/store.py, saved in var/state.json)
        |-- cit/assistant.py   words -> draft change / answer / form (rules; model only for room requests)
        |-- cit/parser.py      room request -> form (Claude if key set, rules otherwise) -> normalise
        |-- cit/bookings.py    ranking, placement, alternatives, reasons
        |-- cit/timetable.py   OR-Tools CP-SAT: timetable + minimal-move repair
        |-- cit/exams.py       OR-Tools CP-SAT: midsem
        |-- cit/explain.py     slot checks and "why is it here" written from real clashes
        '-- validator.py       official checker, run on every export and after every approved change

## Rules the app enforces

* Priority order and role caps from the dataset; same level goes to the earlier request.
* A request is approved (inside the asked window), offered an alternative (nearest valid slot), or
  rejected, always with a reason. Room swaps show as approved with a "Room changed" badge.
* Only an approved institute-level event may move a class, and the class is always moved to a free slot.
* Self-approval is blocked. Lab bookings can be approved by that lab's department coordinator; anything
  that moves a class, and every timetable change, goes to an admin.
* Week 9 is exam week (no bookings). Bookings work for any week 1 to 16; published decisions are locked and
  new requests are placed around them.
* Changes (teacher away, room closed, add/remove a class, or an uploaded change file) are repaired with
  the smallest set of moves, shown as a before/after table, and applied only when another admin approves.

## For judges (command line, same code as the website)

    python -m cit.cli generate                       # resets, builds everything, writes exports/
    python -m cit.cli apply examples/sample_disruption.json   # files and approves a change file
    python -m cit.cli check                          # runs validator.py rules on both exports

In the website the same steps are: Generate everything, Changes > Upload a change file (Dean), approve as
Registrar, then Overview > Download schedule.json / schedule_after.json (or Run official check).
`exports/` is rewritten by the app after every generate and every approved change.

## Result on the public dataset

* schedule.json: 0 hard violations, soft penalty 3 to 5, booking score 67 of 70, 0 priority inversions, exam penalty 0.
* schedule_after.json (sample disruption): 0 hard violations, 8 sessions moved, all room-only.

## Class swaps and online guest lectures

**Swap classes (teachers).** A teacher opens *Swap classes*, picks one of their own classes, then picks a colleague's class they would like to take. The list shows who teaches each class now and marks the ones that cannot work, with the reason (a clash, an absence, the daily hour limit, a step-free room). The colleague is asked first. If they agree, the request goes to the department head (the coordinator of each department involved, or the Dean's office where a department has no coordinator). Only when every head has approved is the timetable changed, and the change is checked with the official validator and undone if it would add a hard violation. Swapped classes are drawn with a dashed outline in the timetable.

**Online guest lectures (Bookings, second tab).** Title, speaker, week, day, start and end time, meeting link and audience. No room is needed, but the audience must not have a class, an exam or another online lecture at that time. The Dean's office schedules directly; coordinators and teachers send it for approval. Only `http(s)` links are accepted.

Tests: `python tests/collab_flow.py` (resets the server state, then runs both workflows through the API).


## Swaps last for one day

A class swap is for one week by default: the teacher picks the week, and only that week's two classes change hands, each on its own day. Every other week keeps its usual teacher, and `schedule.json` is not touched. "Every week" is still there as a separate choice, and that one goes through the official validator before it is applied. Swaps for weeks that have passed are refused, and old one-day swaps are deleted once their days are over. Test: `python tests/oneday_flow.py`.

## Bookings: approving, cancelling and clean-up

- Whoever can approve a booking (the Dean's office, or the coordinator of the department whose lab it is) can also cancel it. The person who asked is told.
- "My bookings" is a tab inside Bookings. It lists every request the signed-in person has made, across all weeks. "All my requests" on the overview opens it.
- Bookings, online lectures and extra classes whose time has passed are deleted automatically. Weekends count as before Monday, as on the overview. Past fest-week bookings leave the app but are kept for `schedule.json`, so the export still matches the dataset. Test: `python tests/purge_flow.py`.

## First start

The app starts with a ready-made timetable, exam schedule and Spectra week decisions (`data/seed_state.json`), so there is nothing to wait for. On the Dean's office overview, "Use the ready-made timetable" loads it again after a reset, and "Generate a new one" runs the solver (about 40 seconds to a minute, depending on the computer).

## Extra classes in exam week

During exam week (week 9) a teacher can ask for an extra or revision class at any time from 07:00 to 22:00, including the evening periods that are normally event-only. It is available only in exam week.

- **Hard rules (exams only):** the students' own exams that day, and rooms an exam is using. These block the request.
- **Soft rules (a score, never a block):** teacher away or avoiding that time, daily hours limit, another extra class or online lecture for the same students, room too small, not step-free, closed or not meant for classes, lunch hour, ending after 19:00 or 21:00, longer than 3 hours, double-booked room.
- The form checks as you type, ranks rooms by points, and shows the exams the students have that day. If no room is picked, the room with the fewest points is used.
- The head of the course's department (or the Dean's office) approves or turns down, and sees the points and each warning. Approved classes appear on the exam-week timetable and are kept out of `schedule.json`, like online lectures.
- API: `GET /api/extras`, `POST /api/extras/check`, `POST /api/extras`, `POST /api/extras/{id}/decide`, `POST /api/extras/{id}/cancel`. Test: `python tests/extra_flow.py`.

## Undo an approved change

The Dean's office can roll back the most recent approved timetable change (a Changes request, or an "every week" swap) from its card on the Changes or Swap classes tab.

- Before a change is applied, the app keeps a snapshot of the timetable, the list of applied changes and the booking decisions it was about to touch.
- Undo puts all three back, then runs the official `validator.py` again on the result. If the checker reports more hard problems than before, nothing is changed and the reason is shown. Otherwise the change is marked "Undone" with the checker result, who did it and why, and `schedule_after.json` is rewritten.
- Only the latest change can be undone, because later ones build on it. Older cards say so; undo the newer one first. It also refuses if a booking the change touched has been decided again since, so that no one's approval is silently reversed.
- The person who asked and the teachers whose classes moved back are notified. A one-week swap has nothing in the weekly timetable to put back, so undoing it only marks it undone.
- API: `POST /api/changes/{id}/undo`, `POST /api/swaps/{id}/undo` (Admin only). Test: `python tests/undo_flow.py` (checks that `schedule_after.json` is identical to before the change, and that the checker still gives 0 hard violations).

## Repeating bookings

A club that rehearses every Tuesday asks once. On the request form, "Repeat every week until week N" books the same slot in every week from the chosen week to week N.

- Exam week is skipped, and so are weeks that have already passed. The form shows the weeks it will book before it is sent. One repeat holds at most 26 bookings (for example 13 weeks of two days).
- Each week is decided on its own against that week's timetable, so a week can get a different room or be turned down without affecting the others. The ids share one number with a letter each (BR-21a, BR-21b), and `series_id` ties them together. The Spectra-week one goes into `schedule.json` like any other booking.
- The Dean's office (or the lab's coordinator) sees "Approve all N weeks" and approves the series with one click. Approving a single week is still possible. The person who asked cannot approve it.
- "Cancel this week" and "Cancel this and later weeks" are on every row; the owner, the approver and the Dean's office can use them.
- The plain-English reader understands "every Tuesday for 6 weeks", "weekly until week 8" and "every Tuesday" (which runs to the last week before exams, and says so).
- API: `POST /api/bookings` with `repeat_until`, `POST /api/bookings/series/{series_id}/publish`, `POST /api/bookings/series/{series_id}/cancel` (optional `from_week`). Test: `python tests/recurring_flow.py`.

## Known limitations

* State is one JSON file (`var/state.json`), fine for a demo and one server, not for many writers.
* The week is the same every week except for approved bookings; there is no per-week timetable editing.
* Moving a class asks the solver for the fewest moves; it is not guaranteed to be the global minimum.
* The built-in reader handles common English and Hinglish phrasing; unusual wording falls back to follow-up questions.
* Exam week (Week 9), the 16-week semester and "current week" (3) are assumptions, see below.

## Assumptions to confirm

* The semester has 16 weeks, Spectra week is Week 7 (from the dataset) and exam week is Week 9 (assumed; `cit/store.py` SEM).
* "Today" for tomorrow ("kal") comes from the server clock; weekend days are not teaching days, so the form asks for a day.
* Demo accounts and the shared password are for the hackathon only.

## Layout

    cit/timetable.py   CP-SAT timetable and repair model
    cit/bookings.py    ranking, placement, overrides, reasons
    cit/exams.py       exam scheduler
    cit/repair.py      minimal-move repair and diff
    cit/parser.py      plain-language reader (Claude or rules) -> form
    cit/store.py       users, weeks, bookings, changes, audit (state in var/state.json)
    cit/api.py         FastAPI endpoints + static site
    web/               the website (no build step)
    tests/             API flow, UI click-through, parser and solver checks

## Running on Windows (PowerShell)

```
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python -m uvicorn cit.api:app --port 8000
```
Open http://localhost:8000, sign in as `dean@cit.example` / `demo`, and press "Generate everything".
Use a venv: OR-Tools needs NumPy 2, which breaks pandas in a conda base environment.
