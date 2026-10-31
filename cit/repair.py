"""Minimal-move repair after a disruption, with a plain diff."""
import copy
from collections import defaultdict
from .timetable import solve, Problem

import validator as official


CUSTOM = ("move_session", "swap_faculty")


def apply_disruption(data, dis):
    """Official change types go through the official code. `move_session` is ours: it pins a class
    to a chosen time (and room) or forbids some times, and the same rules then have to hold."""
    plain = {**dis, "changes": [c for c in dis.get("changes", []) if c["type"] not in CUSTOM]}
    d = official.apply_disruption(data, plain)
    for c in dis.get("changes", []):
        if c["type"] not in CUSTOM:
            continue
        if c["type"] == "swap_faculty":
            by = {x["id"]: x for x in d["sessions"]}
            if c["session_a"] not in by or c["session_b"] not in by:
                raise ValueError("One of the swapped classes does not exist")
            by[c["session_a"]]["faculty_id"] = c["faculty_b"]
            by[c["session_b"]]["faculty_id"] = c["faculty_a"]
            continue
        s = next((x for x in d["sessions"] if x["id"] == c["session_id"]), None)
        if s is None:
            raise ValueError(f"No class {c['session_id']}")
        if c.get("to"):
            s["fixed_slot"] = {"day": c["to"]["day"], "start_period": int(c["to"]["start_period"])}
            if c["to"].get("room_id"):
                s["pinned_room"] = c["to"]["room_id"]
        for a in c.get("avoid", []):
            s.setdefault("avoid_slots", []).append({"day": a["day"], "periods": list(a["periods"])})
    return d


def affected_sessions(old_data, new_data, baseline):
    """Sessions whose current placement is no longer valid, or that are new."""
    P = Problem(new_data)
    out, why = [], {}
    for s in new_data["sessions"]:
        sid = s["id"]
        if sid not in baseline:
            out.append(sid)
            why[sid] = "New session"
            continue
        d, st, rid = baseline[sid]
        per = range(st, st + s["duration"])
        reasons = []
        if s.get("fixed_slot") and (s["fixed_slot"]["day"], s["fixed_slot"]["start_period"]) != (d, st):
            reasons.append("Moved as requested")
        for a in s.get("avoid_slots", []):
            if a["day"] == d and any(p in a["periods"] for p in per):
                reasons.append("Asked to move away from this time")
        if s.get("pinned_room") and s["pinned_room"] != rid:
            reasons.append(f"Moved to {s['pinned_room']} as requested")
        for p in per:
            if (d, p) in P.fac_un[s["faculty_id"]]:
                f = P.fac[s["faculty_id"]]
                reasons.append(f"{f['name']} is away on {d.title()}")
                break
        for p in per:
            if (d, p) in P.room_un[rid]:
                reasons.append(f"{rid} is closed on {d.title()}")
                break
        if reasons:
            out.append(sid)
            why[sid] = "; ".join(reasons)
    return out, why


def neighbours(data, seeds):
    """Sessions that share a faculty member or a group with the seeds."""
    S = {s["id"]: s for s in data["sessions"]}
    fac = {S[x]["faculty_id"] for x in seeds if x in S}
    grp = {g for x in seeds if x in S for g in S[x]["groups"]}
    return {s["id"] for s in data["sessions"] if s["faculty_id"] in fac or set(s["groups"]) & grp}


def repair(data, dis, baseline, reservations=None, time_limit=60):
    """Return (new_data, new_assign, diff, info). Tries the smallest neighbourhood first."""
    new_data = apply_disruption(data, dis)
    removed = {sid for sid in baseline if sid not in {s["id"] for s in new_data["sessions"]}}
    base = {k: v for k, v in baseline.items() if k not in removed}
    aff, why = affected_sessions(data, new_data, base)
    stages = [("affected sessions only", set(aff)),
              ("their teachers and classes", neighbours(new_data, aff) | set(aff)),
              ("whole timetable", None)]
    new_assign, info = None, {}
    for name, free in stages:
        new_assign, info = solve(new_data, baseline=base, reservations=reservations,
                                 time_limit=time_limit, free_sessions=free if free is not None else None)
        if new_assign is not None:
            info["stage"] = name
            break
    if new_assign is None and reservations:
        new_assign, info = solve(new_data, baseline=base, time_limit=time_limit)
        info["stage"] = "whole timetable, without keeping event slots free"
        info["dropped_reservations"] = True
    diff = []
    if new_assign is not None:
        S = {s["id"]: s for s in new_data["sessions"]}
        for sid, new in new_assign.items():
            old = base.get(sid)
            if old is None:
                diff.append({"session_id": sid, "type": "added", "before": None, "after": list(new),
                             "why": why.get(sid, "New session")})
            elif tuple(old) != tuple(new):
                kind = "moved" if tuple(old[:2]) != tuple(new[:2]) else "room"
                diff.append({"session_id": sid, "type": kind, "before": list(old), "after": list(new),
                             "why": why.get(sid) or "Made room for another change"})
        for sid in removed:
            diff.append({"session_id": sid, "type": "removed", "before": list(baseline[sid]), "after": None,
                         "why": "Session removed"})
    return new_data, new_assign, diff, info
