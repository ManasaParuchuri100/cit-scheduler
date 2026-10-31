"""Ties the solvers together: generate everything, export schedule.json."""
import time
from .timetable import solve
from .bookings import decide_batch, reservations_for, booking_score, rank_key
from .exams import schedule_exams

TEAM = "CIT Scheduler"


def plan_reservations(data, requests=None):
    """Decide the bookings on an empty timetable; the slots they use during class hours are
    kept free when the timetable is generated (booking-aware timetabling)."""
    decisions, _, _ = decide_batch(data, {}, requests=requests, allow_override=False)
    return decisions


def generate_timetable(data, time_limit=45, requests=None, log=print):
    """Return (assign, info, reservations, plan). Drops reservations of the lowest-ranked
    requests first if the timetable cannot be built with all of them."""
    plan = plan_reservations(data, requests)
    by = {r["id"]: r for r in data["booking_requests"]}
    # lowest priority first when we have to give up reservations
    order = sorted([d for d in plan if d["status"] in ("approved", "alternative_offered")],
                   key=lambda d: rank_key(data, by[d["request_id"]]), reverse=True)
    kept = list(plan)
    dropped = []
    while True:
        res = reservations_for(data, kept)
        assign, info = solve(data, reservations=res, time_limit=time_limit)
        if assign is not None:
            info["dropped_reservations"] = dropped
            return assign, info, res, plan
        if not order:
            return None, info, res, plan
        drop = order.pop(0)
        dropped.append(drop["request_id"])
        kept = [d for d in kept if d["request_id"] != drop["request_id"]]
        log(f"timetable infeasible with all event slots reserved; releasing {drop['request_id']}")


def to_schedule(data, assign, decisions, overrides, exams, team=TEAM):
    return {
        "team": team,
        "dataset_id": data["dataset_id"],
        "sessions": [{"session_id": sid, "day": d, "start_period": st, "room_id": r}
                     for sid, (d, st, r) in sorted(assign.items())],
        "fest_week": {
            "bookings": [{k: v for k, v in d.items() if k != "room_changed"} for d in decisions],
            "session_overrides": overrides,
        },
        "exams": exams,
    }


def generate_all(data, tt_time=45, log=print):
    t0 = time.time()
    assign, info, res, plan = generate_timetable(data, time_limit=tt_time, log=log)
    if assign is None:
        return None
    decisions, overrides, trace = decide_batch(data, assign)
    exams, einfo = schedule_exams(data)
    return {"assign": assign, "decisions": decisions, "overrides": overrides, "trace": trace,
            "exams": exams, "info": {"timetable": info, "exams": einfo, "seconds": round(time.time() - t0, 1),
                                     "reservations": len(res["rooms"])},
            "reservations": res}
