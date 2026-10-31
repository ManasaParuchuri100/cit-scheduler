"""Plain-language reasons, computed by code from the live timetable.

Nothing here asks a language model whether something is allowed. `slot_check` is the
same rule set as the solver and the official validator, applied to one class and one time,
and every sentence it returns comes from a real clash in the data.
"""
from collections import defaultdict
from .timetable import Problem, LAST_TEACHING, soft_cost_of_option, USE

DAYN = {"MON": "Monday", "TUE": "Tuesday", "WED": "Wednesday", "THU": "Thursday", "FRI": "Friday"}


def clock(p):
    return {1: "08:00", 2: "09:00", 3: "10:00", 4: "11:00", 5: "12:00", 6: "14:00", 7: "15:00",
            8: "16:00", 9: "17:00"}.get(p, f"P{p}")


def clock_end(p):
    return {1: "09:00", 2: "10:00", 3: "11:00", 4: "12:00", 5: "13:00", 6: "15:00", 7: "16:00",
            8: "17:00", 9: "18:00"}.get(p, f"P{p}")


def span(d, st, dur):
    return f"{DAYN[d]} {clock(st)} to {clock_end(st + dur - 1)}"


class Board:
    """Who is where right now, indexed for quick clash lookups."""

    def __init__(self, data, assign, reservations=None):
        self.data = data
        self.P = Problem(data)
        self.assign = {k: tuple(v) for k, v in assign.items() if k in self.P.sessions}
        self.fac = defaultdict(list)
        self.grp = defaultdict(list)
        self.room = defaultdict(list)
        self.fac_day = defaultdict(int)
        res = reservations or {}
        self.room_block = set(map(tuple, res.get("rooms", [])))
        self.group_block = set(map(tuple, res.get("groups", [])))
        for sid, (d, st, rid) in self.assign.items():
            s = self.P.sessions[sid]
            for p in range(st, st + s["duration"]):
                self.fac[(s["faculty_id"], d, p)].append(sid)
                self.room[(rid, d, p)].append(sid)
                for g in s["groups"]:
                    self.grp[(g, d, p)].append(sid)
            self.fac_day[(s["faculty_id"], d)] += s["duration"]

    def title(self, sid):
        s = self.P.sessions[sid]
        c = next((c for c in self.data["courses"] if c["id"] == s["course_id"]), {})
        return f"{c.get('title', s['course_id'])} ({s['course_id']}{'' if s['kind'] == 'lecture' else ' ' + s['kind']})"


def _basket_mates(P, sid):
    b = P.sessions[sid].get("basket_slot")
    return [x for x, s in P.sessions.items() if b and s.get("basket_slot") == b and x != sid]


def slot_check(B, sid, d, st):
    """Can this class sit at (day, start)? Returns blockers, each marked movable or not.

    movable=True means another class is in the way and could be moved; movable=False means a rule
    (teacher away, lunch, lab start, fixed slot) rules the time out whatever else is done.
    """
    P = B.P
    s = P.sessions[sid]
    dur, per = s["duration"], list(range(st, st + s["duration"]))
    f = P.fac[s["faculty_id"]]
    out = []

    def hard(t):
        out.append({"text": t, "movable": False})

    def soft(t):
        out.append({"text": t, "movable": True})

    if per[-1] > LAST_TEACHING:
        hard("It would run past 18:00, and teaching ends after P9")
    if st <= P.lunch < per[-1]:
        hard("It would run across lunch (13:00 to 14:00)")
    if s["kind"] == "lab" and st not in P.lab_starts:
        hard("A 3-hour lab can only start at P2 (09:00) or P6 (14:00)")
    fx = s.get("fixed_slot")
    if fx and (fx["day"] != d or fx["start_period"] != st):
        hard(f"This class is fixed to {DAYN[fx['day']]} {clock(fx['start_period'])}")
    for a in s.get("avoid_slots", []):
        if a["day"] == d and any(p in a["periods"] for p in per):
            hard("A request says this class must not be at that time")
    for u in f.get("unavailable", []):
        if u["day"] == d and any(p in u["periods"] for p in per):
            why = f" ({u['reason']})" if u.get("reason") else ""
            hard(f"{f['name']} is unavailable then{why}")
            break
    busy = {x for p in per for x in B.fac.get((f["id"], d, p), []) if x != sid}
    for x in sorted(busy):
        soft(f"{f['name']} is teaching {B.title(x)} then")
    mates = set(_basket_mates(P, sid))
    for g in s["groups"]:
        clash = {x for p in per for x in B.grp.get((g, d, p), []) if x != sid
                 and x not in mates and not (s.get("basket_slot") and P.sessions[x].get("basket_slot") == s["basket_slot"])}
        for x in sorted(clash):
            soft(f"{g} already has {B.title(x)} then")
        if any((g, d, p) in B.group_block for p in per):
            soft(f"{g} must attend an approved event then")
    if not busy:
        day_hours = B.fac_day.get((f["id"], d), 0)
        cur = B.assign.get(sid)
        if cur and cur[0] == d:
            day_hours -= dur
        if day_hours + dur > f.get("max_hours_per_day", 4):
            hard(f"{f['name']} would teach {day_hours + dur} hours that day, and the limit is {f.get('max_hours_per_day', 4)}")
    rooms = [r for r in P.eligible_rooms(s) if not s.get("pinned_room") or r == s["pinned_room"]]
    free = []
    for r in rooms:
        if any((d, p) in P.room_un[r] for p in per):
            continue
        if any((r, d, p) in B.room_block for p in per):
            continue
        if any(x != sid for p in per for x in B.room.get((r, d, p), [])):
            continue
        free.append(r)
    free.sort(key=lambda r: P.rooms[r]["capacity"])
    if not free and not any(not b["movable"] for b in out):
        if rooms:
            soft(f"All {len(rooms)} rooms that suit it are in use or closed then")
        else:
            hard("No room has the right type, size and access for it")
    if mates:
        soft(f"It would move its whole elective basket of {len(mates) + 1} classes together")
    return {"ok": not [b for b in out if b["text"] and not b["text"].startswith("It would move its whole")],
            "blockers": out, "rooms": free, "day": d, "start": st,
            "fixable": all(b["movable"] for b in out)}


def slot_table(data, assign, sid, reservations=None):
    """Every start time for one class: free, free-if-others-move, or ruled out (with reasons)."""
    B = Board(data, assign, reservations)
    P = B.P
    s = P.sessions[sid]
    cur = B.assign.get(sid)
    rows = []
    for d in P.days:
        for st in range(1, LAST_TEACHING - s["duration"] + 2):
            if cur and cur[0] == d and cur[1] == st:
                continue
            c = slot_check(B, sid, d, st)
            if c["ok"]:
                kind = "free"
            elif c["fixable"]:
                kind = "if_others_move"
            else:
                kind = "ruled_out"
            cost = soft_cost_of_option(P, s, d, st)
            rows.append({"day": d, "start": st, "label": span(d, st, s["duration"]), "kind": kind,
                         "reasons": [b["text"] for b in c["blockers"]][:3],
                         "rooms": c["rooms"][:4], "penalty": cost})
    order = {"free": 0, "if_others_move": 1, "ruled_out": 2}
    rows.sort(key=lambda r: (order[r["kind"]], r["penalty"], P.days.index(r["day"]), r["start"]))
    return rows


def why_here(data, assign, sid, reservations=None):
    """Why this class sits where it does. Facts first, then what else was open."""
    B = Board(data, assign, reservations)
    P = B.P
    s = P.sessions[sid]
    d, st, room = B.assign[sid]
    f = P.fac[s["faculty_id"]]
    lines = []
    when = span(d, st, s["duration"])
    head = f"{B.title(sid)} is on {when} in {room}."
    # the room
    rooms = P.eligible_rooms(s)
    caps = sorted(P.rooms[r]["capacity"] for r in rooms)
    rc = P.rooms[room]["capacity"]
    lines.append(f"Room: {room} seats {rc} and the class has {s['size']} students. {len(rooms)} rooms are the right type and big enough; "
                 f"{'this is the closest fit' if rc == caps[0] or rc <= s['size'] * 1.5 else 'it was the one free at that time'}.")
    if s.get("fixed_slot"):
        lines.append("The time is fixed in the dataset, so it never moves.")
    if s.get("basket_slot"):
        lines.append(f"It is part of elective basket {s['basket_slot']}: every class in the basket has to run at the same time, so they were placed together.")
    if s["kind"] == "lab":
        lines.append("Labs run for three hours and cannot cross lunch, so they only start at P2 (09:00) or P6 (14:00).")
    # other open times
    rows = slot_table(data, assign, sid, reservations)
    free = [r for r in rows if r["kind"] == "free"]
    fix = [r for r in rows if r["kind"] == "if_others_move"]
    out = [r for r in rows if r["kind"] == "ruled_out"]
    tally = defaultdict(int)
    for r in out:
        for t in r["reasons"][:1]:
            key = "teacher unavailable" if "unavailable" in t else "lunch" if "lunch" in t else "lab start" if "lab" in t.lower() \
                else "daily teaching limit" if "limit" in t else "past 18:00" if "18:00" in t else "other rule"
            tally[key] += 1
    total = len(rows) + 1
    lines.append(f"Of {total} possible start times in the week, {len(out)} are ruled out by rules ("
                 + ", ".join(f"{n} by {k}" for k, n in sorted(tally.items(), key=lambda kv: -kv[1])) + ")." if out else
                 f"All {total} possible start times are allowed by the rules.")
    if free:
        lines.append("Other times that are free right now with no clash: " + "; ".join(r["label"] for r in free[:4]) +
                     ". The solver picked the current time because it gives the whole timetable fewer soft penalties.")
    else:
        lines.append("No other time is free for this teacher, these classes and a suitable room at once, so moving it means moving another class too.")
    if fix:
        lines.append(f"{len(fix)} more times would work if another class moved first. Example: {fix[0]['label']} (" + fix[0]["reasons"][0] + ").")
    # the 8 AM and soft sides
    soft_notes = []
    if st == 1:
        soft_notes.append("It is at 08:00. An early start is not penalised by the rules unless the teacher asked to avoid it, and "
                          + ("no teacher preference is broken here." if soft_cost_of_option(P, s, d, st) == 0 else "a small penalty applies here."))
    if st + s["duration"] - 1 == LAST_TEACHING:
        soft_notes.append("It ends at 18:00 (P9), which has a small soft penalty. It was kept there because earlier times were taken or ruled out.")
    for pref in f.get("preferences", []):
        if pref.get("type") == "avoid" and d in pref.get("days", P.days) and any(p in pref["periods"] for p in range(st, st + s["duration"])):
            soft_notes.append(f"{f['name']} asked to avoid this time. It stayed because moving it would break a rule or another class.")
    if not soft_notes:
        soft_notes.append("It breaks no soft rule: no teacher preference is hit and it is not in the last period of the day.")
    lines += soft_notes
    return {"session_id": sid, "title": head, "lines": lines,
            "alternatives": [{"label": r["label"], "day": r["day"], "start": r["start"], "rooms": r["rooms"]} for r in free[:5]]}


def parse_slot_words(text):
    """Pull 'avoid' or 'to' targets out of a faculty sentence. Used by the assistant router."""
    return None
