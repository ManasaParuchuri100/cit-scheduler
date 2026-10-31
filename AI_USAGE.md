# AI usage

## What the model is not allowed to decide

The model only turns words into a form that a person then checks and edits. It never decides anything:

* whether a booking is valid, approved, rejected or moved: `cit/bookings.py` does, with fixed rules;
* whether a timetable or a change is valid: OR-Tools and the checks in `cit/timetable.py` and the official `validator.py` do;
* who may approve: `cit/store.py` blocks self-approval and checks roles in code;
* the priority level: it comes from the person's role (`role_category_cap`), whatever the message says.
  “Mark it institute level”, “top priority” or “ignore the rules” are noted on the form and have no effect;
* explanations: every reason shown (“why is this class here”, “why was this rejected”) is written by code from the
  real clashes in the data, not by a model.

Every model output goes through `normalise()` in `cit/parser.py` (real days, periods, room types, groups) and then
through the same live check and booking engine as a hand-filled form, before any data changes.

## Where prompts are kept

The only prompt is `SYSTEM` in `cit/parser.py`. It is plain text in the repo.

## AI tools used to build the project

* Claude (Anthropic) through Claude Code: wrote and revised most of the code in `cit/`, `web/` and `tests/`, the
  README and these declarations, under the team's direction. The team reviewed and tested the results.
* Claude was also used to read the problem statement and plan the features and role screens before any code was written.


## Swaps and online lectures
No model is used here. Swap feasibility, approvals and the online-lecture clash check are plain rules in `cit/collab.py`, using the same constraints as the official validator.

Extra classes in exam week use no model. Exam clashes are hard checks and every other rule is a fixed point score, so the result is the same each time and can be explained to the approver.

Undo and repeating bookings use no model either. Undo is decided by the official validator, run again on the rolled-back timetable, and a roll-back that makes it worse is refused. Only the weekly-repeat wording in the plain-English reader ("every Tuesday for 6 weeks") goes through the same reader as every other booking request, and its answer is shown in an editable form that the person confirms.
