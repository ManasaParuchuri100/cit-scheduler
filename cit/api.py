"""HTTP API and static site. Run: uvicorn cit.api:app"""
import datetime as dt
import json
import os
import re
import threading
from collections import defaultdict

from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import JSONResponse, FileResponse, Response
from fastapi.staticfiles import StaticFiles

import validator as official
from .store import Store, TABS, ROLE_LABEL, PRIORITY_LABEL, LAB_DEPT, PERIOD_START
from .parser import parse_request
from .bookings import effective_category, MAX_PERIOD, room_ok_for, END_LABEL, SLOT_LABEL, why_not


def pStart(p):
    return SLOT_LABEL.get(p, "")


def pEnd(p):
    return END_LABEL.get(p, "")


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
app = FastAPI(title="CIT Scheduler")
S = Store()


# ---------------------------------------------------------------- auth
def current(request: Request):
    h = request.headers.get("authorization", "")
    tok = h[7:] if h.lower().startswith("bearer ") else request.query_params.get("token", "")
    u = S.user_for(tok)
    if not u:
        raise HTTPException(401, "Please sign in")
    S.purge_past()                      # events whose time has passed are removed
    return u


def need(user, *roles):
    if user["role"] not in roles:
        raise HTTPException(403, "Your role cannot do this")


@app.exception_handler(ValueError)
async def _ve(_, e):
    return JSONResponse({"error": str(e)}, status_code=400)


@app.exception_handler(PermissionError)
async def _pe(_, e):
    return JSONResponse({"error": str(e)}, status_code=403)


@app.exception_handler(KeyError)
async def _ke(_, e):
    return JSONResponse({"error": f"Not found: {e}"}, status_code=404)


# ---------------------------------------------------------------- login and meta
@app.post("/api/login")
async def login(request: Request):
    b = await request.json()
    r = S.login(b.get("email", ""), b.get("password", ""))
    if not r:
        raise HTTPException(401, "Wrong email or password")
    tok, u = r
    return {"token": tok, "user": public_user(u)}


def public_user(u):
    return {"email": u["email"], "name": u["name"], "role": u["role"], "role_label": ROLE_LABEL[u["role"]],
            "department": u.get("department"), "faculty_id": u.get("faculty_id"), "tabs": TABS[u["role"]]}


@app.get("/api/demo-accounts")
def demo_accounts():
    d = S.base_data
    pick = {"admin": [], "department_coordinator": [], "faculty": [], "club": []}
    for u in S.users.values():
        pick[u["role"]].append({"email": u["email"], "name": u["name"], "department": u.get("department")})
    return {"password": "demo", "accounts": pick}


@app.get("/api/me")
def me(user=Depends(current)):
    unread = sum(1 for n in S.notes.get(user["email"], []) if not n["read"])
    return {"user": public_user(user), "unread": unread, "generated": S.generated, "job": S.job,
            "sem": S.sem, "current_week": S.current_week, "week_monday": S.week_monday().isoformat()}


@app.get("/api/meta")
def meta(user=Depends(current)):
    d = S.data
    return {"rooms": d["rooms"], "groups": d["student_groups"], "days": d["calendar"]["days"],
            "periods": d["calendar"]["periods"], "priority": [{"id": c, "label": PRIORITY_LABEL.get(c, c)} for c in d["priority_order"]],
            "role_cap": d["role_category_cap"], "sem": S.sem, "current_week": S.current_week,
            "faculty": [{"id": f["id"], "name": f["name"], "department": f["department"]} for f in d["faculty"]],
            "courses": {c["id"]: {"title": c["title"], "department": c["department"], "year": c["year"]} for c in d["courses"]},
            "sessions": [{"id": x["id"], "course_id": x["course_id"], "kind": x["kind"], "faculty_id": x["faculty_id"], "groups": x["groups"],
                          "duration": x["duration"], "size": x["size"], "room_types": x["room_types"]} for x in d["sessions"]], "lunch": d["calendar"]["lunch"],
            "exam_calendar": d["calendar"]["exam_week"]}


# ---------------------------------------------------------------- generate
@app.post("/api/dataset")
async def dataset_load(request: Request, user=Depends(current)):
    """Admin loads a dataset file (same format as cit_public.json). Clears everything built so far."""
    need(user, "admin")
    blob = await request.json()
    out = S.load_uploaded_dataset(user, blob)
    refresh_lookups()
    return {"ok": True, **out}


@app.post("/api/generate")
def generate(user=Depends(current)):
    need(user, "admin")
    if S.job.get("state") == "running":
        return S.job
    threading.Thread(target=S.generate, args=(user,), daemon=True).start()
    S.job = {"state": "running", "message": "Starting"}
    return S.job


@app.get("/api/job")
def job(user=Depends(current)):
    return S.job


@app.post("/api/seed")
def seed_load(user=Depends(current)):
    need(user, "admin")
    with S.lock:
        if not S.load_seed():
            raise HTTPException(404, "No ready-made timetable in this copy")
    refresh_lookups()
    return {"ok": True}


@app.post("/api/reset")
def reset(user=Depends(current)):
    need(user, "admin")
    S.reset()
    return {"ok": True}


# ---------------------------------------------------------------- timetable
def cell_view(sid, a, wa_base, week_ov, one=None):
    """`one` holds teacher changes that last for this week only (one-day swaps)."""
    s = SESS[sid]
    d, st, room = a
    fid = (one or {}).get(sid, s["faculty_id"])
    sf = FAC[s["faculty_id"]]["name"] if fid != s["faculty_id"] else (FAC[SWAPPED[sid]]["name"] if sid in SWAPPED and SWAPPED[sid] in FAC else None)
    return {"id": sid, "course_id": s["course_id"], "title": COURSE[s["course_id"]]["title"], "kind": s["kind"],
            "day": d, "start": st, "dur": s["duration"], "room": room, "faculty_id": fid,
            "faculty": FAC[fid]["name"], "groups": s["groups"], "basket": bool(s.get("basket_slot")),
            "moved_this_week": sid in week_ov, "one_day_swap": fid != s["faculty_id"],
            "swapped_from": sf,
            "changed": sid in wa_base and tuple(wa_base[sid]) != tuple(a),
            "status": ("Moved for an event" if sid in week_ov else
                       "Time changed" if sid in wa_base and tuple(wa_base[sid][:2]) != tuple(a[:2]) else
                       "Room changed" if sid in wa_base and wa_base[sid][2] != a[2] else "On time")}


SESS, COURSE, FAC, SWAPPED = {}, {}, {}, {}


def refresh_lookups():
    SESS.clear(); COURSE.clear(); FAC.clear(); SWAPPED.clear()
    SWAPPED.update(S.swapped_from())
    SESS.update({s["id"]: s for s in S.data["sessions"]})
    COURSE.update({c["id"]: c for c in S.data["courses"]})
    FAC.update({f["id"]: f for f in S.data["faculty"]})


def event_view(rec, req):
    return {"id": req["id"], "title": req["title"], "by": req["requester"], "day": rec.get("day"), "start": rec.get("start_period"),
            "end": rec.get("end_period"), "room": rec.get("room_id"), "status": rec["status"], "state": rec.get("state"),
            "category": rec.get("category"), "reason": rec.get("reason"), "owner": req["owner"],
            "groups": req["mandatory_for_groups"], "room_changed": rec.get("room_changed", False)}


@app.get("/api/timetable")
def timetable(view: str = "group", id: str = "", week: int = 0, user=Depends(current)):
    refresh_lookups()
    week = week or S.current_week
    if user["role"] == "faculty":
        view, id = "faculty", user["faculty_id"]
    if user["role"] == "department_coordinator" and view == "faculty":
        if FAC.get(id, {}).get("department") != user["department"] and False:
            pass
    wa = S.week_assign(week)
    ov = {o["session_id"] for o in S.week_overrides(week)}
    one = S.oneoff(week)
    cells = []
    for sid, a in wa.items():
        s = SESS.get(sid)
        if not s:
            continue
        if view == "group" and id not in s["groups"]:
            continue
        if view == "faculty" and one.get(sid, s["faculty_id"]) != id:
            continue
        if view == "room" and a[2] != id:
            continue
        if view == "course" and s["course_id"] != id:
            continue
        cells.append(cell_view(sid, a, S.baseline, ov, one))
    events = []
    for rec in S.week_decisions(week):
        if rec["status"] == "rejected":
            continue
        req = next(r for r in S.requests if r["id"] == rec["request_id"])
        if view == "room" and rec.get("room_id") == id:
            events.append(event_view(rec, req))
        elif view == "group" and id in req["mandatory_for_groups"]:
            events.append(event_view(rec, req))
    closed = []
    if view == "room":
        for u in S.data.get("room_unavailability", []):
            if u["room_id"] == id:
                closed.append(u)
    away = []
    if view == "faculty":
        away = FAC[id].get("unavailable", [])
    for c in cells:
        dd = S.week_date(week, c["day"]); c["date"], c["date_label"] = dd.isoformat(), f"{dd.day} {dd.strftime('%b')}"
    xs = []
    for x in S.approved_extras(week):
        if (view == "group" and id in x["groups"]) or (view == "faculty" and x["faculty_id"] == id) or (view == "room" and x["room"] == id) or (view == "course" and x["course_id"] == id):
            xs.append({k: x[k] for k in ("id", "course_id", "title", "day", "start", "end", "room", "groups", "topic", "by_name", "level")})
    return {"view": view, "id": id, "week": week, "cells": cells, "events": events, "closed": closed, "away": away, "extras": xs,
            "exam_week": week == S.sem["exam_week"], "fest_week": week == S.sem["fest_week"]}


@app.get("/api/timetable/choices")
def choices(user=Depends(current)):
    refresh_lookups()
    d = S.data
    depts = defaultdict(list)
    for g in d["student_groups"]:
        depts[g["department"]].append({"id": g["id"], "name": g["name"]})
    return {"groups": [{"id": g["id"], "name": g["name"], "department": g["department"]} for g in d["student_groups"]],
            "faculty": [{"id": f["id"], "name": f["name"], "department": f["department"]} for f in d["faculty"]
                        if f["department"] != "ADMIN"],
            "courses": sorted([{"id": c["id"], "title": c["title"], "department": c["department"], "year": c["year"]} for c in d["courses"]], key=lambda c: c["title"]),
            "rooms": [{"id": r["id"], "name": r["name"], "type": r["type"], "capacity": r["capacity"]} for r in d["rooms"]]}


# ---------------------------------------------------------------- rooms
@app.get("/api/rooms/find")
def rooms_find(day: str, frm: int, to: int, week: int = 0, min_cap: int = 0, rtype: str = "", need: str = "",
               user=Depends(current)):
    refresh_lookups()
    week = week or S.current_week
    wa = S.week_assign(week)
    needs = [n for n in need.split(",") if n]
    busy = {}
    for sid, (d, st, rid) in wa.items():
        if d != day:
            continue
        for p in range(st, st + SESS[sid]["duration"]):
            busy[(rid, p)] = ("class", f"{COURSE[SESS[sid]['course_id']]['title']} ({SESS[sid]['course_id']})")
    for rec in S.week_decisions(week):
        if rec["status"] in ("approved", "alternative_offered") and rec.get("day") == day:
            req = next(r for r in S.requests if r["id"] == rec["request_id"])
            for p in range(rec["start_period"], rec["end_period"] + 1):
                busy[(rec["room_id"], p)] = ("event", req["title"])
    closed = {(u["room_id"], p) for u in S.data.get("room_unavailability", []) if u["day"] == day for p in u["periods"]}
    out = []
    for r in S.data["rooms"]:
        if "event" not in r["allowed_uses"]:
            continue
        feats = set(r["features"]) | ({"accessible"} if r["accessible"] else set())
        fits = r["capacity"] >= min_cap and (not rtype or r["type"] == rtype) and not (set(needs) - feats)
        status, what = "free", ""
        for p in range(frm, to + 1):
            if (r["id"], p) in closed:
                status, what = "closed", "Closed for maintenance"
                break
            if (r["id"], p) in busy:
                status, what = busy[(r["id"], p)]
                break
        out.append({"id": r["id"], "name": r["name"], "type": r["type"], "capacity": r["capacity"], "features": r["features"],
                    "accessible": r["accessible"], "building": r["building"], "fits": fits, "status": status, "what": what})
    out.sort(key=lambda x: (x["status"] != "free", not x["fits"], x["capacity"]))
    return {"rooms": out, "week": week}


def apply_repeat(form):
    """Turn what the reader found ("every Tuesday", "for 6 weeks", "until week 10") into a last week for the form."""
    n, open_ = form.pop("repeat_count", None), form.pop("repeat_open", False)
    until = form.get("repeat_until")
    if not (n or open_ or until):
        return form
    w, ew, last = int(form["week"]), S.sem["exam_week"], S.sem["weeks"]
    notes = form.setdefault("assumptions", [])
    if n:
        cnt, u = 1, w
        while cnt < n and u < last:
            u += 1
            cnt += u != ew
        until = u
        notes.append(f"Repeats weekly for {n} weeks, so until week {u}. Exam week is skipped")
    elif open_:
        until = ew - 1 if w < ew - 1 else None
        notes.append(f"Repeats weekly. No end was given, so it runs until week {until}, the last week before exams. Change it if you want" if until
                     else "It sounds like a weekly repeat, but there is no week left before exams. Set the last week below if you need one")
    else:
        notes.append(f"Repeats weekly until week {until}. Exam week is skipped")
    form["repeat_until"] = until if until and until > w else None
    return form


# ---------------------------------------------------------------- bookings
@app.post("/api/bookings/parse")
async def bookings_parse(request: Request, user=Depends(current)):
    b = await request.json()
    week = int(b.get("week") or S.sem["fest_week"])
    first_monday = dt.date.today() - dt.timedelta(days=dt.date.today().weekday())
    form = parse_request(b["text"], S.data, role=user["role"], week=week)
    form["raw_text"] = b["text"]
    form["week"] = form.get("week_hint") or week
    apply_repeat(form)
    cap = S.data["role_category_cap"].get(user["role"], "club_event")
    form["role_cap"] = cap
    form["effective_category"] = effective_category(S.data, {"role": user["role"], "requested_category": form["requested_category"]})
    return form


def form_to_req(user, form):
    return {"id": "PREVIEW", "submitted_at": "9999", "requester": user["name"], "role": user["role"],
            "department": user.get("department"), "requested_category": form.get("requested_category", "club_event"),
            "title": form.get("title", "Request"), "attendance": int(form["attendance"]),
            "duration_periods": int(form["duration_periods"]), "windows": form["windows"], "room_types": form["room_types"],
            "needs": form.get("needs", []), "requested_room": form.get("requested_room"),
            "mandatory_for_groups": form.get("mandatory_for_groups", []), "series_id": None}


@app.post("/api/bookings/check")
async def bookings_check(request: Request, user=Depends(current)):
    """Live check while the form is edited: which rooms would work, and what would rank above."""
    refresh_lookups()
    from .bookings import Occupancy, free_for
    f = await request.json()
    week = int(f.get("week") or S.sem["fest_week"])
    problems = []
    if week == S.sem["exam_week"]:
        problems.append("This is exam week. Exams come first, so no events can be booked.")
    for k, label in (("attendance", "attendance"), ("duration_periods", "duration"), ("windows", "day and time")):
        if not f.get(k):
            problems.append(f"Add {label}")
    if problems:
        return {"ok": False, "problems": problems, "options": []}
    req = form_to_req(user, f)
    wa = S.week_assign(week)
    occ = Occupancy(S.data, wa)
    for rec in S.week_decisions(week):
        if rec["status"] in ("approved", "alternative_offered"):
            occ.add_booking(rec["request_id"], rec["room_id"], rec["day"], rec["start_period"], rec["end_period"])
    options = []
    dur = req["duration_periods"]
    for w in req["windows"]:
        for st in range(w["from_period"], min(w["to_period"], MAX_PERIOD) - dur + 2):
            for r in S.data["rooms"]:
                if room_ok_for(req, r) and free_for(occ, req, r, w["day"], st, st + dur - 1):
                    options.append({"room": r["id"], "capacity": r["capacity"], "day": w["day"], "start": st, "end": st + dur - 1})
    options.sort(key=lambda o: (o["capacity"], o["day"], o["start"]))
    eff = effective_category(S.data, req)
    rooms_by = {r["id"]: r for r in S.data["rooms"]}
    checks = []
    late = all(w["from_period"] >= 10 for w in req["windows"])
    anyday = any(w["from_period"] <= 9 for w in req["windows"])
    if late:
        checks.append({"ok": True, "text": "Evening slot (P10 to P13) is allowed for events. No classes run then."})
    elif anyday:
        checks.append({"ok": True, "text": "Daytime slot: a room is only used if no class is held there, and lunch (13:00 to 14:00) stays free."})
    checks.append({"ok": True, "text": f"Week {week} is not exam week, so events can be booked."})
    wished = req.get("requested_room")
    if wished:
        free_wished = [o for o in options if o["room"] == wished]
        if free_wished:
            o = free_wished[0]
            checks.append({"ok": True, "text": f"{wished} is free on {o['day'].title()} {pStart(o['start'])} to {pEnd(o['end'])}."})
        else:
            checks.append({"ok": False, "text": why_not(occ, req, wished, rooms_by) + ". Another room will be offered."})
    if options:
        best = options[0]
        r = rooms_by[best["room"]]
        checks.append({"ok": True, "text": f"{len(options)} option(s) fit. Best match: {best['room']} ({r['capacity']} seats) on {best['day'].title()} {pStart(best['start'])} to {pEnd(best['end'])}."})
        if "accessible" not in req["needs"] and not r["accessible"]:
            checks.append({"ok": False, "text": f"{best['room']} has no lift. Tick step-free access if anyone attending needs it."})
    else:
        checks.append({"ok": False, "text": "Nothing is free in your window. You can still send it: the app offers the nearest valid slot."})
    if eff != req["requested_category"]:
        checks.append({"ok": False, "text": f"Your role can ask for at most {PRIORITY_LABEL.get(eff, eff).lower()}, so it ranks there."})
    return {"ok": True, "problems": [], "options": options[:12], "count": len(options), "checks": checks,
            "effective_category": eff, "capped": eff != req["requested_category"],
            "message": (f"{len(options)} free option(s) right now" if options else
                        "Nothing is free in your window right now. You can still send it: the app will offer the nearest slot")}


@app.post("/api/bookings")
async def bookings_create(request: Request, user=Depends(current)):
    need(user, "admin", "department_coordinator", "faculty", "club")
    f = await request.json()
    if not f.get("title") or not f.get("windows") or not f.get("attendance") or not f.get("duration_periods"):
        raise ValueError("Add a title, how many people, how long, and at least one day and time")
    weeks, skipped = S.repeat_weeks(f.get("week") or S.sem["fest_week"], f.get("repeat_until"))
    ids = S.create_booking(user, f)
    refresh_lookups()
    out = []
    for i in ids:
        rec = S.decisions.get(i)
        req = next((r for r in S.requests if r["id"] == i), {})
        out.append({"id": i, "week": req.get("week"), "status": rec["status"] if rec else "pending", "reason": rec.get("reason") if rec else ""})
    return {"created": out, "weeks": weeks, "skipped": skipped, "series_id": next((r.get("series_id") for r in S.requests if r["id"] == ids[0]), None)}


def booking_row(rec, user):
    req = next((r for r in S.requests if r["id"] == rec["request_id"]), None)
    if not req:
        return None
    row = event_view(rec, req)
    row.update({"week": rec.get("week"), "requested_category": req["requested_category"], "attendance": req["attendance"],
                "windows": req["windows"], "duration": req["duration_periods"], "requested_room": req["requested_room"],
                "needs": req["needs"], "overrides": rec.get("overrides", []),
                "lab_departments": rec.get("lab_departments", []),
                "can_decide": bool(user and S.can_publish(user, rec) and rec.get("state") != "published" and req["owner"] != user["email"]),
                "own": bool(user and req["owner"] == user["email"]), "text": req.get("raw_text", ""),
                "cancelled": any(c["request_id"] == req["id"] for c in S.cancel_log)})
    sid = req.get("series_id")
    sib = S.series_of(sid) if sid else []
    if len(sib) > 1 and len({r["week"] for r in sib}) > 1:      # a weekly repeat (a multi-day booking in one week is not)
        def waiting(r):
            d = S.decisions.get(r["id"])
            return bool(d and user and S.can_publish(user, d) and d.get("state") != "published" and r["owner"] != user["email"])
        row.update({"series_id": sid, "series_total": len(sib), "series_pos": [r["id"] for r in sib].index(req["id"]) + 1,
                    "series_weeks": sorted({r["week"] for r in sib}), "series_waiting": sum(1 for r in sib if waiting(r)),
                    "series_live": sum(1 for r in sib if not any(c["request_id"] == r["id"] for c in S.cancel_log))})
    return row


@app.get("/api/bookings")
def bookings_list(week: int = 0, mine: int = 0, all: int = 0, user=Depends(current)):
    week = week or S.sem["fest_week"]
    rows = []
    for rec in S.decisions.values():
        if not all and rec.get("week") != week:
            continue
        row = booking_row(rec, user)
        if not row:
            continue
        if mine and not row["own"]:
            continue
        if user["role"] == "department_coordinator" and not mine and not (
                user["department"] in row["lab_departments"] or row["own"]):
            req_dept = next(r for r in S.requests if r["id"] == row["id"]).get("department")
            if req_dept != user["department"]:
                continue
        rows.append(row)
    cat_rank = {c: i for i, c in enumerate(S.data["priority_order"])}
    rows.sort(key=lambda r: ((r.get("week") or 0) if all else 0, cat_rank.get(r["category"], 9), r["id"]))
    return {"week": week, "rows": rows, "exam_week": week == S.sem["exam_week"]}


@app.post("/api/bookings/publish")
async def bookings_publish(request: Request, user=Depends(current)):
    b = await request.json()
    done, refused = S.publish(user, b["ids"])
    return {"published": done, "refused": refused,
            "message": ("Some could not be approved by you (your own requests, or outside your area)" if refused else "Done")}


@app.post("/api/bookings/series/{sid}/publish")
def bookings_series_publish(sid: str, user=Depends(current)):
    done, refused = S.publish_series(user, sid)
    return {"published": done, "refused": refused}


@app.post("/api/bookings/series/{sid}/cancel")
async def bookings_series_cancel(sid: str, request: Request, user=Depends(current)):
    b = await request.json() if (await request.body()) else {}
    return {"cancelled": S.cancel_series(user, sid, b.get("from_week"))}


@app.post("/api/bookings/{rid}/cancel")
def bookings_cancel(rid: str, user=Depends(current)):
    S.cancel_booking(user, rid)
    return {"ok": True}


# ---------------------------------------------------------------- changes
@app.post("/api/changes/parse")
async def changes_parse(request: Request, user=Depends(current)):
    """Turn a short plain-English note into a change form (leave, closure). Always editable."""
    from .parser import resolve_days
    b = await request.json()
    text = b["text"].lower()
    d = S.data
    days = resolve_days(text, dt.date.today())[0] if text else []
    kind = "room_unavailable" if any(w in text for w in ("room", "closed", "closure", "leak", "maintenance", "ac ")) else "faculty_unavailable"
    return {"type": kind, "days": days or d["calendar"]["days"][:1], "periods": list(range(1, 10)), "reason": b["text"][:80]}


@app.post("/api/changes")
async def changes_create(request: Request, user=Depends(current)):
    b = await request.json()
    dis = b["dis"]
    dis.setdefault("id", f"app-{len(S.changes) + 1}")
    if not dis.get("changes"):
        raise ValueError("Add at least one change")
    refresh_lookups()
    return S.create_change(user, dis, b.get("note", ""))


@app.get("/api/changes")
def changes_list(user=Depends(current)):
    rows = []
    for c in reversed(S.changes):
        if user["role"] == "admin" or c["by"] == user["email"] or (
                user["role"] == "department_coordinator"):
            rows.append(dict(c, can_decide=user["role"] == "admin" and c["status"] == "pending" and c["by"] != user["email"],
                             own=c["by"] == user["email"], can_undo=S.can_undo(user, "change", c["id"]),
                             undo_blocked=user["role"] == "admin" and c["status"] == "approved" and not S.can_undo(user, "change", c["id"])))
    if user["role"] == "department_coordinator":
        rows = [r for r in rows if r["own"] or r["status"] != "pending"]
    return {"rows": rows}


@app.post("/api/changes/{cid}/undo")
async def changes_undo(cid: str, request: Request, user=Depends(current)):
    b = await request.json() if (await request.body()) else {}
    refresh_lookups()
    return S.undo_change(user, cid, b.get("reason", ""))


@app.post("/api/swaps/{sid}/undo")
async def swaps_undo(sid: str, request: Request, user=Depends(current)):
    b = await request.json() if (await request.body()) else {}
    refresh_lookups()
    return S.swap_view(S.undo_swap(user, sid, b.get("reason", "")), user)


@app.post("/api/changes/preview")
async def changes_preview(request: Request, user=Depends(current)):
    """Run a draft through the solver and validator without saving it."""
    b = await request.json()
    dis = b["dis"]
    dis.setdefault("id", "preview")
    if not dis.get("changes"):
        raise ValueError("Add at least one change")
    refresh_lookups()
    return S.preview_change(user, dis, b.get("note", ""))


@app.get("/api/sessions/slots")
def session_slots(id: str, user=Depends(current)):
    """Every possible time for one class: free, free if another class moves, or ruled out with reasons."""
    refresh_lookups()
    sx = SESS.get(id)
    if not sx:
        raise KeyError(id)
    if user["role"] == "faculty" and sx["faculty_id"] != user.get("faculty_id"):
        raise PermissionError("You can look at your own classes")
    rows = S.session_slots(id)
    a = S.assign[id]
    return {"id": id, "title": COURSE[sx["course_id"]]["title"], "kind": sx["kind"], "now": {"day": a[0], "start": a[1], "room": a[2]},
            "dur": sx["duration"], "slots": rows}


@app.get("/api/explain/session")
def explain_session(id: str, user=Depends(current)):
    refresh_lookups()
    if id not in SESS:
        raise KeyError(id)
    return S.explain_session(id)


def booking_explain(bid):
    rec = S.decisions.get(bid)
    req = next((r for r in S.requests if r["id"] == bid), None)
    if not rec or not req:
        raise KeyError(bid)
    d = S.data
    order = d["priority_order"]
    eff = effective_category(d, req)
    lines = []
    asked = req["requested_category"]
    if eff != asked:
        lines.append(f"It was asked as “{PRIORITY_LABEL.get(asked, asked)}”, but {req['role']} requests can only rank as “{PRIORITY_LABEL.get(eff, eff)}”, so that is the level it was decided at.")
    else:
        lines.append(f"It ranks as “{PRIORITY_LABEL.get(eff, eff)}”.")
    lines.append(f"Decision: {rec['status'].replace('_', ' ')}. {rec.get('reason', '')}")
    for o in rec.get("overrides", []):
        lines.append(f"To make room, class {o['session_id']} moves to {o['day'].title()} P{o.get('start_period')} in {o['room_id']}.")
    rivals = []
    for r2 in S.decisions.values():
        if r2["request_id"] == bid or r2.get("week") != rec.get("week") or r2["status"] not in ("approved", "alternative_offered"):
            continue
        q2 = next((q for q in S.requests if q["id"] == r2["request_id"]), None)
        if not q2 or not r2.get("room_id"):
            continue
        for w in req["windows"]:
            if r2.get("day") == w["day"] and r2["start_period"] <= w["to_period"] and r2["end_period"] >= w["from_period"] and r2["room_id"] in (
                    [req["requested_room"]] if req["requested_room"] else [x["id"] for x in d["rooms"] if x["type"] in req["room_types"]]):
                higher = order.index(effective_category(d, q2)) <= order.index(eff)
                rivals.append(f"{q2['id']} ({PRIORITY_LABEL.get(effective_category(d, q2))}) holds {r2['room_id']} {r2['day'].title()} P{r2['start_period']} to P{r2['end_period']}"
                              + (", and it ranks equal or higher" if higher else ""))
                break
    if rivals and rec["status"] != "approved":
        lines.append("What stood in the way: " + "; ".join(rivals[:4]) + ".")
    lines.append("Rule: when two requests want the same room at the same time, the higher level wins; at the same level, the earlier request wins. Nobody approves their own request.")
    return {"booking_id": bid, "title": f"{bid} · {req['title']}", "lines": lines, "status": rec["status"]}


@app.get("/api/explain/booking")
def explain_booking(id: str, user=Depends(current)):
    return booking_explain(id)


@app.post("/api/assistant")
async def assistant(request: Request, user=Depends(current)):
    """One box: a question, a timetable request or a room request. Nothing here changes data."""
    from . import assistant as A
    b = await request.json()
    text = (b.get("text") or "").strip()
    if not text:
        raise ValueError("Type what you need first")
    refresh_lookups()
    intent = A.route(S, user, text)
    if intent == "explain":
        r = A.do_explain(S, user, text, booking_explain, lambda sid: S.explain_session(sid), b.get("session_id"))
        if r.get("kind") == "booking" and re.search(r"reject|denied|declin|refus|not approved", text.lower()):
            a = r["answers"][0]
            if a["status"] != "rejected":
                a["lines"].insert(0, f"{a['booking_id']} was not rejected. Its status is “{a['status'].replace('_', ' ')}”.")
        return r
    if intent == "change":
        if not S.generated:
            raise ValueError("Generate the timetable first")
        return A.do_change(S, user, text, b.get("session_id"))
    form = parse_request(text, S.data, role=user["role"], week=int(b.get("week") or S.sem["fest_week"]))
    form["raw_text"] = text
    form["week"] = form.get("week_hint") or int(b.get("week") or S.sem["fest_week"])
    apply_repeat(form)
    form["role_cap"] = S.data["role_category_cap"].get(user["role"], "club_event")
    form["effective_category"] = effective_category(S.data, {"role": user["role"], "requested_category": form["requested_category"]})
    return {"intent": "booking", "form": form}


@app.post("/api/changes/{cid}/decide")
async def changes_decide(cid: str, request: Request, user=Depends(current)):
    b = await request.json()
    ch = S.decide_change(user, cid, bool(b.get("approve")), b.get("reason", ""))
    refresh_lookups()
    return ch


# ---------------------------------------------------------------- class swaps between teachers
@app.get("/api/swaps")
def swaps_list(user=Depends(current)):
    refresh_lookups()
    return {"rows": S.list_swaps(user)}


@app.get("/api/swaps/options")
def swaps_options(give: str, week: int = 0, user=Depends(current)):
    refresh_lookups()
    return S.swap_options(user, give, week or None)


@app.post("/api/swaps")
async def swaps_create(request: Request, user=Depends(current)):
    b = await request.json()
    refresh_lookups()
    return S.swap_view(S.create_swap(user, b.get("give", ""), b.get("take", ""), b.get("note", ""), b.get("week"), b.get("scope", "day")), user)


@app.post("/api/swaps/{sid}/respond")
async def swaps_respond(sid: str, request: Request, user=Depends(current)):
    b = await request.json()
    refresh_lookups()
    return S.swap_view(S.respond_swap(user, sid, bool(b.get("approve")), b.get("reason", "")), user)


@app.post("/api/swaps/{sid}/decide")
async def swaps_decide(sid: str, request: Request, user=Depends(current)):
    b = await request.json()
    sw = S.decide_swap(user, sid, bool(b.get("approve")), b.get("reason", ""))
    refresh_lookups()
    return S.swap_view(sw, user)


@app.post("/api/swaps/{sid}/cancel")
def swaps_cancel(sid: str, user=Depends(current)):
    refresh_lookups()
    return S.swap_view(S.cancel_swap(user, sid), user)


# ---------------------------------------------------------------- online guest lectures
@app.get("/api/online")
def online_list(user=Depends(current)):
    return {"rows": S.list_online(user)}


@app.post("/api/online/check")
async def online_check(request: Request, user=Depends(current)):
    return S.check_online(await request.json())


@app.post("/api/online")
async def online_create(request: Request, user=Depends(current)):
    return S.create_online(user, await request.json())


@app.post("/api/online/{oid}/decide")
async def online_decide(oid: str, request: Request, user=Depends(current)):
    b = await request.json()
    return S.decide_online(user, oid, bool(b.get("approve")), b.get("reason", ""))


@app.post("/api/online/{oid}/cancel")
def online_cancel(oid: str, user=Depends(current)):
    return S.cancel_online(user, oid)


# ---------------------------------------------------------------- extra classes in exam week
@app.get("/api/extras")
def extras_list(user=Depends(current)):
    return {"rows": S.list_extras(user), "week": S.sem["exam_week"], "days": S.data["calendar"]["exam_week"]["days"]}


@app.post("/api/extras/check")
async def extras_check(request: Request, user=Depends(current)):
    need(user, "faculty")
    return S.check_extra(user, await request.json())


@app.post("/api/extras")
async def extras_create(request: Request, user=Depends(current)):
    return S.create_extra(user, await request.json())


@app.post("/api/extras/{xid}/decide")
async def extras_decide(xid: str, request: Request, user=Depends(current)):
    b = await request.json()
    return S.decide_extra(user, xid, bool(b.get("approve")), b.get("reason", ""))


@app.post("/api/extras/{xid}/cancel")
def extras_cancel(xid: str, user=Depends(current)):
    return S.cancel_extra(user, xid)


# ---------------------------------------------------------------- exams
@app.get("/api/exams")
def exams(user=Depends(current)):
    need(user, "admin", "department_coordinator", "faculty")
    d = S.data
    ex = {e["id"]: e for e in d["exams"]}
    rows = []
    for e in S.exams:
        x = ex[e["exam_id"]]
        rows.append({"exam_id": e["exam_id"], "courses": x["course_ids"], "groups": x["groups"], "size": x["size"],
                     "day": e["day"], "session": e["session"], "rooms": e["rooms"]})
    cal = d["calendar"]["exam_week"]
    return {"rows": rows, "sessions": cal["sessions"], "days": cal["days"], "week": S.sem["exam_week"]}


@app.post("/api/exams/reschedule")
def exams_reschedule(user=Depends(current)):
    need(user, "admin")
    S.reschedule_exams(user)
    return {"ok": True}


# ---------------------------------------------------------------- overview
def describe_dis(dis):
    out = []
    for c in dis.get("changes", []):
        t = c["type"]
        if t == "faculty_unavailable":
            out.append(f"{FAC.get(c['faculty_id'], {}).get('name', c['faculty_id'])} away {', '.join(x.title() for x in c['days'])}")
        elif t == "room_unavailable":
            out.append(f"{c['room_id']} closed {', '.join(x.title() for x in c['days'])}")
        elif t == "add_session":
            out.append(f"Add {c['session']['id']}")
        elif t == "remove_session":
            out.append(f"Remove {c['session_id']}")
        else:
            out.append(t)
    return "; ".join(out)


def attention_items(user):
    items = []
    for ch in reversed(S.changes):
        if ch["status"] == "pending":
            items.append({"type": "Change request", "tone": "warn", "title": f"{ch['id']} from {ch['by_name']}", "tab": "changes",
                          "text": describe_dis(ch["dis"]) + (f". {ch.get('moved', 0)} change time, {ch.get('room_only', 0)} change room." if ch["feasible"] else ". Cannot be done as asked."),
                          "action": "Review"})
        elif ch["status"] == "approved":
            items.append({"type": "Applied", "tone": "info", "title": describe_dis(ch["dis"]), "tab": "timetable",
                          "text": f"{ch['id']} approved. {ch.get('moved', 0) + ch.get('room_only', 0)} classes moved, everything else stayed put.", "action": "Open timetable"})
    for rec in S.decisions.values():
        if rec.get("overrides") and rec.get("state") != "published":
            rq = next(r for r in S.requests if r["id"] == rec["request_id"])
            items.append({"type": "Moves a class", "tone": "bad", "title": f"{rq['id']} {rq['title']}", "tab": "bookings",
                          "text": "To fit this institute event, " + ", ".join(o["session_id"] for o in rec["overrides"]) + " moves to another room or time.", "action": "Decide"})
    closed = {}
    for u in S.data.get("room_unavailability", []):
        closed.setdefault(u["room_id"], []).append(u)
    for rid, lst in list(closed.items())[:3]:
        days = sorted({x["day"] for x in lst}, key=lambda d: DAYS_ORDER.index(d))
        items.append({"type": "Room closed", "tone": "bad", "title": f"{rid} closed {', '.join(d.title() for d in days)}",
                      "text": (lst[0].get("reason") or "Closed") + ". Classes are placed in other rooms and shown as Room changed.", "tab": "rooms", "action": "Open rooms"})
    if S.generated:
        fw = S.sem["fest_week"]
        decs = [d for d in S.decisions.values() if d.get("week") == fw]
        waiting = sum(1 for d in decs if d.get("state") != "published" and d["status"] != "rejected")
        items.append({"type": "Event week", "tone": "info", "title": f"Week {fw} Spectra: {len(decs)} requests decided",
                      "text": f"{waiting} are waiting for approval. Rooms are kept free at event times, so approved events do not move classes.", "tab": "bookings", "action": "Open bookings"})
    return items


DAYS_ORDER = ["MON", "TUE", "WED", "THU", "FRI", "SAT"]


def club_rules():
    d = S.data
    evt = d["calendar"].get("event_only_periods", [10, 11, 12, 13])
    only_events = [r["id"] for r in d["rooms"] if "lecture" not in r["allowed_uses"] and "tutorial" not in r["allowed_uses"] and "event" in r["allowed_uses"]]
    nolift = [r["id"] for r in d["rooms"] if not r["accessible"] and "event" in r["allowed_uses"]]
    closed = {}
    for u in d.get("room_unavailability", []):
        closed.setdefault(u["room_id"], set()).add(u["day"])
    return [
        {"type": "Evenings", "tone": "ok", "title": f"{pStart(evt[0])} to {pEnd(evt[-1])} (P{evt[0]} to P{evt[-1]}) has no classes",
         "text": "Any suitable room can be asked for in the evening. Period 13 ends at 22:00, and nothing later exists."},
        {"type": "Daytime", "tone": "bad", "title": "08:00 to 18:00 (P1 to P9): classes keep their rooms",
         "text": "A club event can use a room at class time only if no class is there. Lunch is 13:00 to 14:00."},
        {"type": "Events only", "tone": "info", "title": ", ".join(only_events[:6]) + (" and more" if len(only_events) > 6 else "") + " never hold regular classes",
         "text": "These rooms are for events and exams, so they are the best first choice."},
        {"type": "Closed", "tone": "warn", "title": "; ".join(f"{r} on {', '.join(x.title() for x in sorted(ds, key=DAYS_ORDER.index))}" for r, ds in list(closed.items())[:3]) or "No closures",
         "text": "Closed for repairs. Do not ask for these rooms at those times."},
        {"type": "No lift", "tone": "gray", "title": ", ".join(nolift[:6]) + " have no step-free access",
         "text": "Tick step-free access if anyone attending needs it."},
    ]


@app.get("/api/overview")
def overview(day: str = "", user=Depends(current)):
    refresh_lookups()
    d = S.data
    notes = {"exam": "Always first. Exam week has no events.", "regular_session": "Timetabled classes keep their slot.",
             "institute_event": "May move a class if there is no other way.", "guest_lecture": "Needs a suitable hall.",
             "department_event": "Department level.", "club_event": "Lowest. Fits around everything else."}
    pri = [{"id": c, "label": PRIORITY_LABEL.get(c, c), "note": notes.get(c, "")} for c in d["priority_order"]]
    cap = d["role_category_cap"].get(user["role"])
    out = {"priority": pri, "your_cap": cap, "role": user["role"], "generated": S.generated, "week": S.current_week,
           "fest_week": S.sem["fest_week"], "exam_week": S.sem["exam_week"],
           "notifications": list(reversed(S.notes.get(user["email"], [])))[:8]}
    out["online_upcoming"] = [o for o in S.list_online(user) if o["status"] == "scheduled" and o["week"] >= S.current_week][:3]
    out["swaps_waiting"] = sum(1 for w in S.list_swaps(user) if w["can_respond"] or w["can_decide"])
    out["extras_waiting"] = sum(1 for x in S.list_extras(user) if x["can_decide"])
    wa = S.week_assign(S.current_week)
    wd = dt.date.today().weekday()
    today = day if day in DAYS_ORDER else (["MON", "TUE", "WED", "THU", "FRI"][wd] if wd < 5 else "MON")
    out["today"] = today
    out["today_is_weekend"] = wd > 4 and not day
    out["picked_day"] = bool(day)

    one0 = S.oneoff(S.current_week)

    def class_rows(pred, limit=60):
        rows = []
        for sid, a in sorted(wa.items(), key=lambda kv: (kv[1][0], kv[1][1])):
            s = SESS[sid]
            if pred(s, a):
                rows.append(cell_view(sid, a, S.baseline, set(), one0))
        return rows[:limit]

    def mine(pred_owner):
        return [booking_row(r, user) for r in S.decisions.values()
                if next((q for q in S.requests if q["id"] == r["request_id"]), {}).get("owner") == user["email"]]

    if user["role"] == "faculty":
        fid = user["faculty_id"]
        rows = class_rows(lambda s, a: one0.get(s["id"], s["faculty_id"]) == fid)
        out["classes_today"] = [c for c in rows if c["day"] == today]
        out["classes_week"] = len(rows)
        out["hours_week"] = sum(c["dur"] for c in rows)
        out["my_changes"] = [c for c in reversed(S.changes) if c["by"] == user["email"]][:5]
        out["away"] = FAC[fid].get("unavailable", [])
        out["my_bookings"] = mine(None)
        out["waiting_tiles"] = [{"n": sum(1 for c in S.changes if c["by"] == user["email"] and c["status"] == "pending"), "text": "of your away requests wait for approval", "tab": "requests"},
                                {"n": sum(1 for b in out["my_bookings"] if b and b["state"] != "published" and b["status"] != "rejected"), "text": "room requests wait for approval", "tab": "requests"}]
    elif user["role"] == "department_coordinator":
        dept = user["department"]
        dgroups = {g["id"] for g in d["student_groups"] if g["department"] == dept}
        rows = class_rows(lambda s, a: any(g in dgroups for g in s["groups"]), 400)
        out["classes_today"] = [c for c in rows if c["day"] == today]
        out["classes_week"] = len(rows)
        out["department"] = dept
        out["faculty_count"] = sum(1 for f in d["faculty"] if f["department"] == dept)
        out["labs_waiting"] = [booking_row(r, user) for r in S.decisions.values()
                               if r.get("state") != "published" and dept in r.get("lab_departments", []) and r["status"] != "rejected"]
        out["pending_changes"] = sum(1 for c in S.changes if c["status"] == "pending" and c["by"] == user["email"])
        out["my_bookings"] = mine(None)
        out["attention"] = [a for a in attention_items(user) if a["type"] in ("Change request", "Applied", "Room closed", "Event week")][:5]
        out["waiting_tiles"] = [{"n": len(out["labs_waiting"]), "text": "lab bookings wait for your approval", "tab": "bookings"},
                                {"n": out["pending_changes"], "text": "of your change requests wait for the Dean's office", "tab": "changes"}]
    elif user["role"] == "club":
        out["my_bookings"] = mine(None)
        out["rules"] = club_rules()
    else:
        waiting = [r for r in S.decisions.values() if r.get("state") == "proposed" and r["status"] != "rejected"]
        out["waiting"] = len(waiting)
        out["moves_needed"] = sum(1 for r in waiting if r.get("overrides"))
        out["changes_pending"] = sum(1 for c in S.changes if c["status"] == "pending" and c["by"] != user["email"])
        out["sessions"] = len(d["sessions"])
        out["exams"] = len(S.exams)
        out["rooms"] = len(d["rooms"])
        out["groups"] = len(d["student_groups"])
        out["faculty"] = len([f for f in d["faculty"] if f["department"] != "ADMIN"])
        st = {}
        for r in S.decisions.values():
            if r.get("week") == S.sem["fest_week"]:
                st[r["status"]] = st.get(r["status"], 0) + 1
        out["fest_status"] = st
        out["health"] = S.health() if S.generated else None
        out["audit"] = list(reversed(S.audit))[:8]
        rows = class_rows(lambda s, a: a[0] == today, 400) if S.generated else []
        rows.sort(key=lambda c: (c["status"] == "On time", c["start"]))
        out["classes_today"] = rows[:10]
        out["classes_today_total"] = len(rows)
        out["attention"] = attention_items(user)[:6] if S.generated else []
        out["waiting_tiles"] = [{"n": out["waiting"], "text": "booking requests to decide", "tab": "bookings"},
                                {"n": out["changes_pending"], "text": "timetable changes need approval", "tab": "changes"},
                                {"n": out["moves_needed"], "text": "bookings that would move a class", "tab": "bookings"}]
    return out


@app.get("/api/health")
def health(user=Depends(current)):
    need(user, "admin")
    return S.health()


@app.get("/api/audit")
def audit(user=Depends(current)):
    need(user, "admin")
    return {"rows": list(reversed(S.audit))[:200]}


@app.post("/api/notifications/read")
def notes_read(user=Depends(current)):
    for n in S.notes.get(user["email"], []):
        n["read"] = True
    S._save()
    return {"ok": True}


# ---------------------------------------------------------------- export
@app.get("/api/export/{name}")
def export(name: str, user=Depends(current)):
    need(user, "admin")
    if not S.generated:
        raise ValueError("Generate the timetable first")
    if name == "schedule.json":
        body = S.export_schedule("baseline")
    elif name == "schedule_after.json":
        body = S.export_schedule("current")
    else:
        raise KeyError(name)
    return Response(json.dumps(body, indent=1), media_type="application/json",
                    headers={"Content-Disposition": f'attachment; filename="{name}"'})


@app.get("/api/export-check/{name}")
def export_check(name: str, user=Depends(current)):
    need(user, "admin")
    body = S.export_schedule("baseline" if name == "schedule.json" else "current")
    rep = official.run(S.validation_data(original=(name == "schedule.json")), body, None)
    return {"hard": rep["hard_violation_count"], "by_rule": rep["hard_by_rule"], "soft": rep["soft_total"],
            "soft_by": rep["soft_penalties"], "bookings": rep.get("bookings"), "exam_penalty": rep.get("exam_soft_penalty"),
            "violations": rep["hard_violations"][:20], "warnings": rep["warnings"][:20]}


# ---------------------------------------------------------------- static site
WEB = os.path.join(ROOT, "web")
app.mount("/static", StaticFiles(directory=WEB), name="static")


@app.get("/")
def index():
    return FileResponse(os.path.join(WEB, "index.html"))
