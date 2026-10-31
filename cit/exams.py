"""Midsem exam scheduler (CP-SAT). Rooms seat half their capacity; an exam may use several rooms."""
from collections import defaultdict
from ortools.sat.python import cp_model


def schedule_exams(data, blocked=None, time_limit=12):
    """Return (list of {exam_id, day, session, rooms}, info).

    blocked: optional {(room, day, session)} that cannot be used.
    """
    cal = data["calendar"]["exam_week"]
    slots = [(d, s["id"]) for d in cal["days"] for s in cal["sessions"]]
    rooms = [r for r in data["rooms"] if "exam" in r["allowed_uses"]]
    groups = {g["id"]: g for g in data["student_groups"]}
    exams = data["exams"]
    blocked = blocked or set()
    m = cp_model.CpModel()
    cap = {r["id"]: r["capacity"] // 2 for r in rooms}
    x = {}
    w = {}
    per_slot_rooms = defaultdict(list)       # (slot, room) -> vars
    for e in exams:
        needs_acc = any(groups[g]["needs_accessible"] for g in e["groups"] if g in groups)
        usable = [r for r in rooms if r["accessible"] or not needs_acc]
        for sl in slots:
            xv = m.NewBoolVar("")
            x[(e["id"], sl)] = xv
            seats = []
            for r in usable:
                if (r["id"],) + sl in blocked:
                    continue
                v = m.NewBoolVar("")
                w[(e["id"], sl, r["id"])] = v
                m.Add(v <= xv)
                seats.append(cap[r["id"]] * v)
                per_slot_rooms[(sl, r["id"])].append(v)
            if seats:
                m.Add(sum(seats) >= e["size"] * xv)
            else:
                m.Add(xv == 0)
        m.AddExactlyOne([x[(e["id"], sl)] for sl in slots])
    for vs in per_slot_rooms.values():
        if len(vs) > 1:
            m.AddAtMostOne(vs)
    for g in groups:
        for sl in slots:
            vs = [x[(e["id"], sl)] for e in exams if g in e["groups"]]
            if len(vs) > 1:
                m.AddAtMostOne(vs)
    pen = []
    days = cal["days"]
    for g in groups:
        for d in days:
            vs = [x[(e["id"], (d, s["id"]))] for e in exams if g in e["groups"] for s in cal["sessions"]]
            if len(vs) > 1:
                ex = m.NewIntVar(0, len(vs), "")
                m.Add(ex >= sum(vs) - 1)
                pen.append(5 * 10 * ex)           # weight ten times the room-count term
    pen += [v for v in w.values()]                 # fewer rooms = fewer invigilators
    m.Minimize(sum(pen))
    s = cp_model.CpSolver()
    s.parameters.max_time_in_seconds = time_limit
    s.parameters.num_workers = 2
    s.parameters.random_seed = 3
    st = s.Solve(m)
    info = {"status": s.StatusName(st)}
    if st not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return None, info
    out = []
    for e in exams:
        for sl in slots:
            if s.Value(x[(e["id"], sl)]):
                used = sorted([rid for (eid, s2, rid), v in w.items() if eid == e["id"] and s2 == sl and s.Value(v)])
                out.append({"exam_id": e["id"], "day": sl[0], "session": sl[1], "rooms": used})
    return out, info


