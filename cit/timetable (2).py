"""Weekly timetable solver (OR-Tools CP-SAT).

One boolean per (session, day+start, room). Hard rules H1-H14 are linear constraints; the soft
penalties S1-S6 of the official validator are the objective. The same model does minimal-move
repair: pass a baseline and a move penalty and unaffected sessions stay where they were.
"""
import time
from collections import defaultdict
from ortools.sat.python import cp_model

LAST_TEACHING = 9
USE = {"lecture": "lecture", "tutorial": "tutorial", "lab": "lab"}

MOVE_ROOM = 1000     # a session that changes room
MOVE_TIME = 1500     # a session that changes day or period (counts as moved plus extra)


class Problem:
    """Pre-computed lookups shared by the solver, the checker and the booking engine."""

    def __init__(self, data):
        self.data = data
        cal = data["calendar"]
        self.days = cal["days"]
        self.lunch = cal["lunch"]["after_period"]
        self.lab_starts = set(cal["lab_start_periods"])
        self.rooms = {r["id"]: r for r in data["rooms"]}
        self.fac = {f["id"]: f for f in data["faculty"]}
        self.groups = {g["id"]: g for g in data["student_groups"]}
        self.sessions = {s["id"]: s for s in data["sessions"]}
        self.fac_un = defaultdict(set)
        for f in data["faculty"]:
            for u in f.get("unavailable", []):
                for p in u["periods"]:
                    self.fac_un[f["id"]].add((u["day"], p))
        self.room_un = defaultdict(set)
        for u in data.get("room_unavailability", []):
            for p in u["periods"]:
                self.room_un[u["room_id"]].add((u["day"], p))

    # candidate (day, start) pairs for a session, ignoring rooms
    def time_options(self, s):
        dur = s["duration"]
        out = []
        for d in self.days:
            for st in range(1, LAST_TEACHING - dur + 2):
                per = range(st, st + dur)
                if st <= self.lunch < per[-1]:
                    continue
                if s["kind"] == "lab" and st not in self.lab_starts:
                    continue
                fx = s.get("fixed_slot")
                if fx and (fx["day"] != d or fx["start_period"] != st):
                    continue
                if any((d, p) in self.fac_un[s["faculty_id"]] for p in per):
                    continue
                if any(a["day"] == d and any(p in a["periods"] for p in per) for a in s.get("avoid_slots", [])):
                    continue
                out.append((d, st))
        return out

    def eligible_rooms(self, s):
        use = USE[s["kind"]]
        out = []
        for r in self.data["rooms"]:
            if r["type"] not in s["room_types"] or r["capacity"] < s["size"]:
                continue
            if s.get("needs_accessible") and not r["accessible"]:
                continue
            if use not in r["allowed_uses"]:
                continue
            if s.get("pinned_room") and r["id"] != s["pinned_room"]:
                continue
            out.append(r["id"])
        return out


def soft_cost_of_option(P, s, d, st):
    per = range(st, st + s["duration"])
    c = 0
    for pref in P.fac[s["faculty_id"]].get("preferences", []):
        if pref.get("type") == "avoid" and d in pref.get("days", P.days):
            c += 2 * sum(1 for p in per if p in pref["periods"])
    if LAST_TEACHING in per:
        c += 1
    return c


def solve(data, baseline=None, reservations=None, time_limit=120, workers=2, log=False,
          free_sessions=None, move_weights=True, hint=None):
    """Return (assign, info). assign: sid -> (day, start, room).

    baseline:       previous assignment; moving away from it is penalised (repair mode).
    reservations:   {"rooms": [(room, day, period)], "groups": [(group, day, period)]} kept free.
    free_sessions:  if given, every other session is pinned to its baseline value.
    """
    P = Problem(data)
    t0 = time.time()
    reservations = reservations or {}
    room_block = set(map(tuple, reservations.get("rooms", [])))
    group_block = set(map(tuple, reservations.get("groups", [])))
    m = cp_model.CpModel()

    sids = [s["id"] for s in data["sessions"]]
    sess = P.sessions
    baskets = defaultdict(list)
    for sid in sids:
        b = sess[sid].get("basket_slot")
        if b:
            baskets[b].append(sid)
    rep = {}   # session -> representative session of its basket (or itself)
    for b, lst in baskets.items():
        for sid in lst:
            rep[sid] = lst[0]

    # ---- domains
    topts = {}
    for sid in sids:
        s = sess[sid]
        opts = P.time_options(s)
        gb = [(g, d, p) for (g, d, p) in group_block if g in s["groups"]]
        if gb:
            opts = [(d, st) for (d, st) in opts
                    if not any((g, d, p) in group_block for g in s["groups"] for p in range(st, st + s["duration"]))]
        topts[sid] = opts
    for b, lst in baskets.items():     # a basket needs a time every member can take
        common = set(topts[lst[0]])
        for sid in lst[1:]:
            common &= set(topts[sid])
        for sid in lst:
            topts[sid] = [o for o in topts[sid] if o in common]

    if baseline is not None and free_sessions is not None:
        free = set(free_sessions)
        for b, lst in baskets.items():
            if any(x in free for x in lst):
                free |= set(lst)
        # pinned sessions keep their baseline slot
    else:
        free = set(sids)

    z = {}                       # (sid, d, st, room) -> BoolVar
    by_session = defaultdict(list)
    cost_terms = []
    for sid in sids:
        s = sess[sid]
        rooms = P.eligible_rooms(s)
        fixed = baseline.get(sid) if (baseline is not None and sid not in free) else None
        for (d, st) in topts[sid]:
            per = range(st, st + s["duration"])
            for rid in rooms:
                if fixed and (d, st, rid) != tuple(fixed):
                    continue
                if any((d, p) in P.room_un[rid] or (rid, d, p) in room_block for p in per):
                    continue
                v = m.NewBoolVar("")
                z[(sid, d, st, rid)] = v
                by_session[sid].append((d, st, rid, v))
                c = soft_cost_of_option(P, s, d, st)
                r = P.rooms[rid]
                if r["capacity"] and s["size"] / r["capacity"] < 0.4:
                    c += 1
                if baseline is not None and move_weights and sid in baseline:
                    bd, bst, brid = baseline[sid]
                    if (d, st) != (bd, bst):
                        c += MOVE_TIME
                    elif rid != brid:
                        c += MOVE_ROOM
                if c:
                    cost_terms.append(c * v)
    for sid in sids:
        if not by_session[sid]:
            return None, {"status": "INFEASIBLE", "reason": f"No valid slot for {sid}", "session": sid}
        m.AddExactlyOne([v for (_, _, _, v) in by_session[sid]])

    # time indicator t[sid, d, st]
    t = {}
    for sid in sids:
        agg = defaultdict(list)
        for (d, st, rid, v) in by_session[sid]:
            agg[(d, st)].append(v)
        for k, lst in agg.items():
            if len(lst) == 1:
                t[(sid,) + k] = lst[0]
            else:
                tv = m.NewBoolVar("")
                m.Add(sum(lst) == tv)
                t[(sid,) + k] = tv
    # baskets: identical times
    for b, lst in baskets.items():
        first = lst[0]
        keys = {(d, st) for (sid_, d, st) in t if sid_ == first}
        for other in lst[1:]:
            for (d, st) in keys:
                m.Add(t[(first, d, st)] == t[(other, d, st)])

    # ---- occupancy constraints
    room_occ = defaultdict(list)
    fac_occ = defaultdict(list)
    grp_occ = defaultdict(list)
    fac_day = defaultdict(list)
    for (sid, d, st, rid), v in z.items():
        s = sess[sid]
        for p in range(st, st + s["duration"]):
            room_occ[(rid, d, p)].append(v)
    for (sid, d, st), v in t.items():
        s = sess[sid]
        f = s["faculty_id"]
        for p in range(st, st + s["duration"]):
            fac_occ[(f, d, p)].append(v)
            if rep.get(sid, sid) == sid:
                for g in s["groups"]:
                    grp_occ[(g, d, p)].append(v)
        fac_day[(f, d)].append((s["duration"], v))
    for lst in room_occ.values():
        if len(lst) > 1:
            m.AddAtMostOne(lst)
    for lst in fac_occ.values():
        if len(lst) > 1:
            m.AddAtMostOne(lst)
    for lst in grp_occ.values():
        if len(lst) > 1:
            m.AddAtMostOne(lst)
    for (f, d), lst in fac_day.items():
        mx = P.fac[f].get("max_hours_per_day", 4)
        if sum(w for w, _ in lst) > mx:
            m.Add(sum(w * v for w, v in lst) <= mx)

    # ---- S2 gaps and S3 long days per group
    occ = {}
    for g in P.groups:
        for d in P.days:
            for p in range(1, LAST_TEACHING + 1):
                lst = grp_occ.get((g, d, p), [])
                if lst:
                    ov = m.NewBoolVar("")
                    m.Add(sum(lst) == ov)
                    occ[(g, d, p)] = ov
    for g in P.groups:
        for d in P.days:
            before = {}
            after = {}
            prev = None
            for p in range(1, LAST_TEACHING + 1):
                b = m.NewBoolVar("")
                if prev is not None:
                    m.Add(b >= prev)
                    if (g, d, p - 1) in occ:
                        m.Add(b >= occ[(g, d, p - 1)])
                else:
                    m.Add(b == 0)
                before[p] = b
                prev = b
            prev = None
            for p in range(LAST_TEACHING, 0, -1):
                a = m.NewBoolVar("")
                if prev is not None:
                    m.Add(a >= prev)
                    if (g, d, p + 1) in occ:
                        m.Add(a >= occ[(g, d, p + 1)])
                else:
                    m.Add(a == 0)
                after[p] = a
                prev = a
            for p in range(2, LAST_TEACHING):
                gap = m.NewBoolVar("")
                o = occ.get((g, d, p))
                expr = before[p] + after[p] - 1 - (o if o is not None else 0)
                m.Add(gap >= expr)
                cost_terms.append(gap)
            hrs = [v for p in range(1, LAST_TEACHING + 1) for v in ([occ[(g, d, p)]] if (g, d, p) in occ else [])]
            if len(hrs) > 6:
                over = m.NewIntVar(0, LAST_TEACHING - 6, "")
                m.Add(over >= sum(hrs) - 6)
                cost_terms.append(3 * over)

    # ---- S4 same course twice a day
    keyed = {}
    for sid in sids:
        s = sess[sid]
        if s["kind"] != "lecture":
            continue
        if s.get("basket_slot"):
            keyed.setdefault(("basket", s["course_id"]), []).append(sid)
        else:
            for g in s["groups"]:
                keyed.setdefault(("g", g, s["course_id"]), []).append(sid)
    seen_sets = defaultdict(int)
    for k, lst in keyed.items():
        seen_sets[tuple(sorted(lst))] += 1
    for lst, mult in seen_sets.items():
        if len(lst) < 2:
            continue
        for d in P.days:
            terms = [v for (sid, dd, st), v in t.items() if dd == d and sid in lst]
            if len(terms) < 2:
                continue
            ex = m.NewIntVar(0, len(lst), "")
            m.Add(ex >= sum(terms) - 1)
            cost_terms.append(3 * mult * ex)

    # ---- S6 (P9) is already in the option costs; S1 as well.
    m.Minimize(sum(cost_terms))

    if hint:
        for (sid, d, st, rid), v in z.items():
            m.AddHint(v, 1 if hint.get(sid) and tuple(hint[sid]) == (d, st, rid) else 0)

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit
    solver.parameters.num_workers = workers
    solver.parameters.log_search_progress = log
    solver.parameters.random_seed = 7
    solver.parameters.absolute_gap_limit = 5
    status = solver.Solve(m)
    name = solver.StatusName(status)
    info = {"status": name, "seconds": round(time.time() - t0, 1), "variables": len(z),
            "objective": solver.ObjectiveValue() if status in (cp_model.OPTIMAL, cp_model.FEASIBLE) else None,
            "bound": solver.BestObjectiveBound() if status in (cp_model.OPTIMAL, cp_model.FEASIBLE) else None}
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return None, info
    assign = {}
    for (sid, d, st, rid), v in z.items():
        if solver.Value(v):
            assign[sid] = (d, st, rid)
    return assign, info
