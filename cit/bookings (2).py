"""Booking engine: ranks requests, places them, explains every decision.

Rules (same as the official validator):
  * effective category = lower of the requested category and the role's cap;
  * higher category wins; ties go to the earlier submitted_at;
  * approved = fully inside a requested window; alternative_offered = best valid slot outside it;
  * only an approved institute-level event may displace a regular class, and the class must be moved;
  * a cancelled request is never approved.
"""
from collections import defaultdict

MAX_PERIOD = 13
LAST_TEACHING = 9
SLOT_LABEL = {1: "08:00", 2: "09:00", 3: "10:00", 4: "11:00", 5: "12:00", 6: "14:00", 7: "15:00",
              8: "16:00", 9: "17:00", 10: "18:00", 11: "19:00", 12: "20:00", 13: "21:00"}
END_LABEL = {1: "09:00", 2: "10:00", 3: "11:00", 4: "12:00", 5: "13:00", 6: "15:00", 7: "16:00",
             8: "17:00", 9: "18:00", 10: "19:00", 11: "20:00", 12: "21:00", 13: "22:00"}


def effective_category(data, req):
    order = data["priority_order"]
    cap = data["role_category_cap"].get(req["role"], "club_event")
    a = order.index(req["requested_category"]) if req["requested_category"] in order else len(order) - 1
    return order[max(a, order.index(cap))]


def rank_key(data, req):
    return (data["priority_order"].index(effective_category(data, req)), req["submitted_at"])


def outranks(data, r1, r2):
    return rank_key(data, r1) < rank_key(data, r2)


def pretty(day, a, b):
    return f"{day.title()} P{a}" + (f"–P{b}" if b != a else "") + f" ({SLOT_LABEL[a]}–{END_LABEL[b]})"


class Occupancy:
    """Who is where in one week: classes (with overrides) plus bookings already placed."""

    def __init__(self, data, week_assign):
        self.data = data
        self.sessions = {s["id"]: s for s in data["sessions"]}
        self.rooms = {r["id"]: r for r in data["rooms"]}
        self.room_busy = defaultdict(list)     # (room, day, p) -> [ids]
        self.group_busy = defaultdict(set)     # (group, day, p) -> {ids}
        self.fac_busy = defaultdict(set)
        self.room_un = defaultdict(set)
        for u in data.get("room_unavailability", []):
            for p in u["periods"]:
                self.room_un[u["room_id"]].add((u["day"], p))
        for sid, (d, st, rid) in week_assign.items():
            self.add_class(sid, d, st, rid)

    def add_class(self, sid, d, st, rid):
        s = self.sessions[sid]
        for p in range(st, st + s["duration"]):
            self.room_busy[(rid, d, p)].append(sid)
            self.fac_busy[(s["faculty_id"], d, p)].add(sid)
            for g in s["groups"]:
                self.group_busy[(g, d, p)].add(s.get("basket_slot") or sid)

    def remove_class(self, sid, d, st, rid):
        s = self.sessions[sid]
        for p in range(st, st + s["duration"]):
            if sid in self.room_busy[(rid, d, p)]:
                self.room_busy[(rid, d, p)].remove(sid)
            self.fac_busy[(s["faculty_id"], d, p)].discard(sid)
            for g in s["groups"]:
                self.group_busy[(g, d, p)].discard(s.get("basket_slot") or sid)

    def add_booking(self, req_id, room, d, a, b):
        for p in range(a, b + 1):
            self.room_busy[(room, d, p)].append(req_id)

    def remove_booking(self, req_id, room, d, a, b):
        for p in range(a, b + 1):
            if req_id in self.room_busy[(room, d, p)]:
                self.room_busy[(room, d, p)].remove(req_id)


def room_ok_for(req, room):
    """Static suitability: type, size, features, events allowed."""
    if "event" not in room["allowed_uses"]:
        return False
    if room["type"] not in req["room_types"]:
        return False
    if room["capacity"] < req["attendance"]:
        return False
    feats = set(room["features"]) | ({"accessible"} if room["accessible"] else set())
    return not (set(req["needs"]) - feats)


def free_for(occ, req, room, d, a, b, ignore=()):
    rid = room["id"]
    for p in range(a, b + 1):
        if (d, p) in occ.room_un[rid]:
            return False
        if [x for x in occ.room_busy[(rid, d, p)] if x not in ignore]:
            return False
        for g in req["mandatory_for_groups"]:
            if occ.group_busy.get((g, d, p)):
                return False
    return True


def why_not(occ, req, room_id, data_rooms):
    """One short sentence on why the room the requester wished for was not used."""
    r = data_rooms.get(room_id)
    if r is None:
        return f"“{room_id}” is not a room at CIT"
    if "event" not in r["allowed_uses"]:
        return f"{room_id} cannot host events"
    if r["type"] not in req["room_types"]:
        return f"{room_id} is a {r['type'].replace('_', ' ')}, not one of the types asked for"
    if r["capacity"] < req["attendance"]:
        return f"{room_id} seats {r['capacity']}, fewer than {req['attendance']}"
    feats = set(r["features"]) | ({"accessible"} if r["accessible"] else set())
    miss = sorted(set(req["needs"]) - feats)
    if miss:
        return f"{room_id} lacks {', '.join(miss).replace('_', ' ')}"
    dur = req["duration_periods"]
    holders, closed = [], False
    for w in req["windows"]:
        for s0 in range(w["from_period"], min(w["to_period"], MAX_PERIOD) - dur + 2):
            for p in range(s0, s0 + dur):
                if (w["day"], p) in occ.room_un[room_id]:
                    closed = True
                for x in occ.room_busy[(room_id, w["day"], p)]:
                    if x not in holders:
                        holders.append(x)
    if holders:
        names = [h for h in holders if h.startswith("BR-")]
        if names:
            return f"{room_id} was already given to {', '.join(names)}, which came first or ranks higher"
        return f"{room_id} has a class at that time"
    if closed:
        return f"{room_id} is closed at that time"
    return f"{room_id} could not take the full slot"


def _candidates(data, occ, req, windows, rooms, ignore=()):
    dur = req["duration_periods"]
    out = []
    for wi, w in enumerate(windows):
        hi = min(w["to_period"], MAX_PERIOD)
        for a in range(w["from_period"], hi - dur + 2):
            b = a + dur - 1
            for room in rooms:
                if free_for(occ, req, room, w["day"], a, b, ignore):
                    out.append((wi, w["day"], a, b, room))
    return out


def _score(req, cand, days, wished):
    wi, d, a, b, room = cand
    return (0 if room["id"] == wished else 1,
            room["capacity"] - req["attendance"],
            wi, a, room["id"])


def _nearest_alternative(data, occ, req, rooms, days):
    """Closest valid slot to the requested windows, anywhere in the week."""
    dur = req["duration_periods"]
    best = None
    for d in days:
        for a in range(1, MAX_PERIOD - dur + 2):
            b = a + dur - 1
            if a <= LAST_TEACHING and b > LAST_TEACHING:
                continue                       # do not straddle the end of class hours
            if a <= 5 < b:
                continue                       # nor lunch
            dist = min(abs(days.index(d) - days.index(w["day"])) * 20 + min(abs(a - w["from_period"]), abs(b - w["to_period"]))
                       for w in req["windows"])
            for room in rooms:
                if free_for(occ, req, room, d, a, b):
                    key = (dist, room["capacity"] - req["attendance"], room["id"], a)
                    if best is None or key < best[0]:
                        best = (key, d, a, b, room)
    return best


def relocate_class(data, occ, week_assign, sid, avoid_room, avoid_days_periods):
    """Find another valid slot for a class so an institute event can use its room."""
    from .timetable import Problem
    P = Problem(data)
    s = P.sessions[sid]
    if s.get("basket_slot") or s.get("fixed_slot"):
        return None
    d0, st0, r0 = week_assign[sid]
    occ.remove_class(sid, d0, st0, r0)
    day_hours = defaultdict(int)
    for x, (d, st, _) in week_assign.items():
        if x != sid and P.sessions[x]["faculty_id"] == s["faculty_id"]:
            day_hours[d] += P.sessions[x]["duration"]
    mx = P.fac[s["faculty_id"]].get("max_hours_per_day", 4)
    found = None
    opts = sorted(P.time_options(s), key=lambda o: (0 if o[0] == d0 else 1, abs(o[1] - st0)))
    for (d, st) in opts:
        per = range(st, st + s["duration"])
        if (d, st) == (d0, st0):
            continue
        if day_hours[d] + s["duration"] > mx:
            continue
        if any(occ.fac_busy.get((s["faculty_id"], d, p)) for p in per):
            continue
        if any(occ.group_busy.get((g, d, p)) for g in s["groups"] for p in per):
            continue
        for rid in P.eligible_rooms(s):
            if any(occ.room_busy[(rid, d, p)] or (d, p) in occ.room_un[rid] for p in per):
                continue
            if any((rid, d, p) in avoid_days_periods for p in per):
                continue
            found = (d, st, rid)
            break
        if found:
            break
    if not found:
        occ.add_class(sid, d0, st0, r0)
    return found


def decide_batch(data, week_assign, requests=None, locked=None, allow_override=True):
    """Decide every request (default: all in the dataset) for one week.

    locked: {request_id: decision} already published; they stay as they are and block their rooms.
    Returns (decisions, overrides, trace).
    """
    days = data["calendar"]["days"]
    rooms_by = {r["id"]: r for r in data["rooms"]}
    rooms = sorted(data["rooms"], key=lambda r: (r["capacity"], r["id"]))
    cancelled = {c["request_id"] for c in data.get("cancellations", [])}
    reqs = requests if requests is not None else data["booking_requests"]
    week = dict(week_assign)
    occ = Occupancy(data, week)
    locked = locked or {}
    decisions, overrides, trace = {}, [], {}
    for rid_, d in locked.items():
        decisions[rid_] = d
        if d["status"] in ("approved", "alternative_offered"):
            occ.add_booking(rid_, d["room_id"], d["day"], d["start_period"], d["end_period"])

    for req in sorted(reqs, key=lambda r: rank_key(data, r)):
        rid_ = req["id"]
        if rid_ in locked:
            continue
        cat = effective_category(data, req)
        capped = cat != req["requested_category"]
        tr = {"category": cat, "capped": capped, "requested_category": req["requested_category"]}
        trace[rid_] = tr
        if rid_ in cancelled:
            decisions[rid_] = {"request_id": rid_, "status": "rejected",
                               "reason": "Cancelled by the requester, so no room is held"}
            continue
        wished = req.get("requested_room")
        suitable = [r for r in rooms if room_ok_for(req, r)]
        biggest = max((r["capacity"] for r in data["rooms"] if "event" in r["allowed_uses"]
                       and r["type"] in req["room_types"]), default=0)
        if not suitable:
            if biggest < req["attendance"]:
                reason = (f"No venue of the right type seats {req['attendance']:,} (the largest is {biggest:,})")
            else:
                reason = "No room has everything asked for (" + ", ".join(req["needs"]).replace("_", " ") + ")"
            decisions[rid_] = {"request_id": rid_, "status": "rejected", "reason": reason}
            continue
        valid_windows = [w for w in req["windows"] if w["from_period"] >= 1 and
                         min(w["to_period"], MAX_PERIOD) - w["from_period"] + 1 >= req["duration_periods"]]
        cands = _candidates(data, occ, req, valid_windows, suitable)
        note = []
        if wished and wished not in rooms_by:
            note.append(f"“{wished}” is not a room at CIT")
        if cands:
            best = min(cands, key=lambda c: _score(req, c, days, wished))
            _, d, a, b, room = best
            reason_bits = []
            if capped:
                reason_bits.append(f"Ranked as {cat.replace('_', ' ')} (the most your role can ask for)")
            if wished and room["id"] != wished:
                reason_bits.append(why_not(occ, req, wished, rooms_by) + f", so {room['id']} was assigned")
            elif not wished:
                reason_bits.append(f"{room['id']} fits {req['attendance']} and has what you asked for")
            dec = {"request_id": rid_, "status": "approved", "day": d, "start_period": a, "end_period": b,
                   "room_id": room["id"], "reason": ". ".join(reason_bits) or f"{room['id']} is free"}
            dec["room_changed"] = bool(wished and room["id"] != wished)
            decisions[rid_] = dec
            occ.add_booking(rid_, room["id"], d, a, b)
            continue
        # institute-level events may move a class
        if allow_override and data["priority_order"].index(cat) <= data["priority_order"].index("institute_event"):
            done = _try_override(data, occ, week, req, suitable, valid_windows, decisions, overrides, rooms_by)
            if done:
                continue
        alt = _nearest_alternative(data, occ, req, suitable, days)
        if alt:
            _, d, a, b, room = alt
            why = _why_windows_failed(occ, req, valid_windows, suitable, rooms_by, data)
            reason = why + f". Offered {room['id']} on {pretty(d, a, b)} instead"
            if note:
                reason = note[0] + ". " + reason
            decisions[rid_] = {"request_id": rid_, "status": "alternative_offered", "day": d, "start_period": a,
                               "end_period": b, "room_id": room["id"], "reason": reason,
                               "room_changed": bool(wished and room["id"] != wished)}
            occ.add_booking(rid_, room["id"], d, a, b)
            continue
        why = _why_windows_failed(occ, req, valid_windows, suitable, rooms_by, data)
        decisions[rid_] = {"request_id": rid_, "status": "rejected", "reason": why + "; nothing else free this week"}
    ordered = [decisions[r["id"]] for r in (requests if requests is not None else data["booking_requests"]) if r["id"] in decisions]
    return ordered, overrides, trace


def _why_windows_failed(occ, req, valid_windows, suitable, rooms_by, data):
    if not valid_windows:
        bad = [w for w in req["windows"] if w["to_period"] > MAX_PERIOD]
        if bad:
            return (f"Period {bad[0]['to_period']} does not exist; events end at P{MAX_PERIOD} (22:00)")
        return "The requested window is shorter than the event"
    holders = []
    classes = False
    dur = req["duration_periods"]
    for w in valid_windows:
        for r in suitable:
            for a in range(w["from_period"], min(w["to_period"], MAX_PERIOD) - dur + 2):
                for p in range(a, a + dur):
                    for x in occ.room_busy[(r["id"], w["day"], p)]:
                        if x.startswith("BR-"):
                            if x not in holders:
                                holders.append(x)
                        else:
                            classes = True
    if req["mandatory_for_groups"]:
        return "Every suitable room is taken, or the compulsory groups have class"
    if holders:
        return "Every suitable room in the window is held by " + ", ".join(holders[:4]) + (" and others" if len(holders) > 4 else "")
    if classes:
        return "Every suitable room has a class in the window"
    return "No suitable room is free in the window"


def _try_override(data, occ, week, req, suitable, windows, decisions, overrides, rooms_by):
    """Take a room from classes by moving them elsewhere (institute events only)."""
    dur = req["duration_periods"]
    for w in windows:
        hi = min(w["to_period"], MAX_PERIOD)
        for a in range(w["from_period"], hi - dur + 2):
            b = a + dur - 1
            if b > LAST_TEACHING:
                continue
            for room in suitable:
                rid = room["id"]
                blockers = set()
                ok = True
                for p in range(a, b + 1):
                    if (w["day"], p) in occ.room_un[rid]:
                        ok = False
                    for x in occ.room_busy[(rid, w["day"], p)]:
                        if x.startswith("BR-"):
                            ok = False
                        else:
                            blockers.add(x)
                if not ok or not blockers:
                    continue
                snapshot = {s: week[s] for s in blockers}
                moved = []
                good = True
                avoid = {(rid, w["day"], p) for p in range(a, b + 1)}
                for sid in sorted(blockers):
                    new = relocate_class(data, occ, week, sid, rid, avoid)
                    if not new:
                        good = False
                        break
                    moved.append((sid, new))
                    d0, st0, r0 = week[sid]
                    week[sid] = new
                    occ.add_class(sid, *new)
                if good and free_for(occ, req, room, w["day"], a, b):
                    for sid, new in moved:
                        overrides.append({"session_id": sid, "day": new[0], "start_period": new[1],
                                          "room_id": new[2], "displaced_by": req["id"]})
                    decisions[req["id"]] = {
                        "request_id": req["id"], "status": "approved", "day": w["day"], "start_period": a,
                        "end_period": b, "room_id": rid,
                        "reason": "Institute event; the classes in the room were moved: " + ", ".join(s for s, _ in moved),
                        "room_changed": False}
                    occ.add_booking(req["id"], rid, w["day"], a, b)
                    return True
                # undo
                for sid, new in moved:
                    occ.remove_class(sid, *new)
                for sid, old in snapshot.items():
                    week[sid] = old
                    occ.add_class(sid, *old)
    return False


def reservations_for(data, decisions):
    """Rooms and groups that the timetable must keep free so approved bookings stay valid."""
    rooms, groups = [], []
    by = {r["id"]: r for r in data["booking_requests"]}
    for d in decisions:
        if d["status"] not in ("approved", "alternative_offered"):
            continue
        for p in range(d["start_period"], min(d["end_period"], LAST_TEACHING) + 1):
            rooms.append((d["room_id"], d["day"], p))
            for g in by[d["request_id"]]["mandatory_for_groups"]:
                groups.append((g, d["day"], p))
    return {"rooms": rooms, "groups": groups}


def booking_score(data, decisions):
    from .bookings import effective_category
    W = {"institute_event": 5, "guest_lecture": 4, "department_event": 3, "club_event": 2}
    by = {r["id"]: r for r in data["booking_requests"]}
    score = 0.0
    for d in decisions:
        if d["status"] in ("approved", "alternative_offered"):
            score += W[effective_category(data, by[d["request_id"]])] * (1 if d["status"] == "approved" else 0.5)
    return score
