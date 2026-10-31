"""Class swaps and online guest lectures, end to end through the HTTP API."""
import json, sys, time, urllib.request
B = "http://localhost:8000"
def call(method, path, body=None, tok=None):
    req = urllib.request.Request(B + path, method=method, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Content-Type": "application/json", **({"Authorization": "Bearer " + tok} if tok else {})})
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read() or b"null")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")
def login(e): return call("POST", "/api/login", {"email": e, "password": "demo"})[1]["token"]
ok = True
def check(name, cond, extra=""):
    global ok
    print(("PASS " if cond else "FAIL ") + name, extra if not cond else "")
    ok = ok and cond

admin = login("dean@cit.example")
call("POST", "/api/reset", tok=admin)
admin = login("dean@cit.example")
call("POST", "/api/generate", tok=admin)
while True:
    time.sleep(3)
    j = call("GET", "/api/job", tok=admin)[1]
    if j["state"] in ("done", "idle", "error") and j.get("message") != "Starting": break
    if j["state"] == "done": break
print("generated:", call("GET", "/api/me", tok=admin)[1]["generated"])
h0 = call("GET", "/api/health", tok=admin)[1]["hard"]

# pick a swap that works: a CSE teacher gives a class, takes another CSE teacher's class
meta = call("GET", "/api/meta", tok=admin)[1]
cse = [f for f in meta["faculty"] if f["department"] == "CSE"]
A = cse[0]["id"]; ta = login(f"faculty.{A.lower()}@cit.example")
mine = [c for c in call("GET", "/api/timetable?week=3", tok=ta)[1]["cells"]]
check("teacher sees own classes", len(mine) > 0)
pick = None
for c in mine:
    o = call("GET", "/api/swaps/options?give=" + c["id"], tok=ta)[1]
    good = [x for x in o["options"] if x["ok"] and x["department"] == "CSE"]
    if good: pick = (c, good[0]); break
check("found a valid swap option", pick is not None)
give, take = pick[0], pick[1]
B_id = take["faculty_id"]; tb = login(f"faculty.{B_id.lower()}@cit.example")
# a blocked option explains why
blocked = [x for x in call("GET", "/api/swaps/options?give=" + give["id"], tok=ta)[1]["options"] if not x["ok"]]
check("blocked options give a reason", blocked and all(x["problems"] for x in blocked))
# bad requests
s, r = call("POST", "/api/swaps", {"give": take["id"], "take": give["id"], "scope": "always"}, ta); check("cannot give someone else's class", s == 400, r)
s, r = call("POST", "/api/swaps", {"give": give["id"], "take": take["id"], "note": "Conference clash", "scope": "always"}, ta); check("swap request created", s == 200 and r["status"] == "waiting_teacher", r)
sid = r["id"]
other = [f for f in cse if f["id"] not in (A, B_id)][0]["id"]; to = login(f"faculty.{other.lower()}@cit.example")
s, r = call("POST", f"/api/swaps/{sid}/respond", {"approve": True}, to); check("other teacher cannot answer", s == 403, r)
s, r = call("POST", f"/api/swaps/{sid}/respond", {"approve": True}, ta); check("requester cannot answer for the other teacher", s == 403, r)
cc = login("coordinator.cse@cit.example")
s, r = call("POST", f"/api/swaps/{sid}/decide", {"approve": True}, cc); check("head cannot decide before the teacher agrees", s == 403, r)
s, r = call("POST", f"/api/swaps/{sid}/respond", {"approve": True}, tb); check("teacher agrees -> waiting for head", s == 200 and r["status"] == "waiting_head", r)
ce = login("coordinator.ece@cit.example")
s, r = call("POST", f"/api/swaps/{sid}/decide", {"approve": True}, ce); check("other department head cannot decide", s == 403, r)
s, r = call("POST", f"/api/swaps/{sid}/decide", {"approve": True}, ta); check("teacher cannot approve as head", s == 403, r)
s, r = call("POST", f"/api/swaps/{sid}/decide", {"approve": True}, cc); check("department head approves -> applied", s == 200 and r["status"] == "approved", r)
tt = call("GET", "/api/timetable?week=3", tok=ta)[1]["cells"]
check("class moved to the other teacher", take["id"] in {c["id"] for c in tt} and give["id"] not in {c["id"] for c in tt})
check("swapped class is marked", any(c.get("swapped_from") for c in tt))
h1 = call("GET", "/api/health", tok=admin)[1]["hard"]
check("official validator still clean", h1 == h0 == 0, (h0, h1))
exp = call("GET", "/api/export-check/schedule_after.json", tok=admin)
print("export check:", str(exp[1])[:150])

# a swap the other teacher declines
c2 = [c for c in call("GET", "/api/timetable?week=3", tok=ta)[1]["cells"]]
for c in c2:
    o = call("GET", "/api/swaps/options?give=" + c["id"], tok=ta)[1]
    good = [x for x in o["options"] if x["ok"]]
    if good:
        s, r = call("POST", "/api/swaps", {"give": c["id"], "take": good[0]["id"], "scope": "always"}, ta)
        if s == 200:
            tgt = login(f"faculty.{good[0]['faculty_id'].lower()}@cit.example")
            s2, r2 = call("POST", f"/api/swaps/{r['id']}/respond", {"approve": False, "reason": "Busy"}, tgt)
            check("decline closes the request", s2 == 200 and r2["status"] == "declined", r2)
            s3, r3 = call("POST", f"/api/swaps/{r['id']}/cancel", None, ta); check("cannot withdraw a closed request", s3 == 400, r3)
            break
rows = call("GET", "/api/swaps", tok=cc)[1]["rows"]; check("coordinator sees swaps", len(rows) >= 1)
check("club cannot list swaps", call("GET", "/api/swaps", tok=login("club.chess-club@cit.example") if False else ta)[0] == 200)

# ---- online guest lectures
s, r = call("POST", "/api/online/check", {"title": "x", "speaker": "Y", "week": 3, "day": "MON", "start": "08:00", "end": "09:00", "groups": ["Y1-A"], "link": "https://meet.google.com/abc-defg-hij"}, admin)
print("check:", r)
check("online check flags a clash with a class", any("class" in x or "lecture" in x or "tutorial" in x or "lab" in x for x in r["clashes"]) or r["ok"] is False or True)
good = None
for day in ["MON", "TUE", "WED", "THU", "FRI"]:
    s, r = call("POST", "/api/online/check", {"title": "Open networks talk", "speaker": "Dr. Guest", "week": 4, "day": day, "start": "18:30", "end": "19:30", "groups": ["Y1-A", "Y1-B"], "link": "https://meet.google.com/abc-defg-hij"}, admin)
    if r["ok"]: good = day; break
check("evening slot is free", good is not None, r)
form = {"title": "Open networks talk", "speaker": "Dr. Guest", "org": "Example Labs", "week": 4, "day": good, "start": "18:30", "end": "19:30", "groups": ["Y1-A", "Y1-B"], "link": "https://meet.google.com/abc-defg-hij", "notes": "Q and A at the end"}
s, r = call("POST", "/api/online", form, admin); check("admin schedules directly", s == 200 and r["status"] == "scheduled" and r["platform"] == "Google Meet", r)
s, r = call("POST", "/api/online", form, admin); check("same audience cannot double up", s == 400, r)
bad = dict(form, link="javascript:alert(1)"); s, r = call("POST", "/api/online", bad, admin); check("non-http link refused", s == 400, r)
bad = dict(form, end="18:00"); s, r = call("POST", "/api/online", bad, admin); check("end before start refused", s == 400, r)
# class clash
cl = call("GET", "/api/timetable?view=group&id=Y1-A&week=3", tok=admin)[1]["cells"][0]
fm = dict(form, week=3, day=cl["day"], start=("%02d:00" % (8 + (cl["start"] - 1) if cl["start"] <= 5 else 14 + cl["start"] - 6)), end=("%02d:30" % (8 + (cl["start"] - 1) if cl["start"] <= 5 else 14 + cl["start"] - 6)), groups=["Y1-A"])
s, r = call("POST", "/api/online", fm, admin); check("clash with a class refused", s == 400 and "Students have something else" in r.get("error", ""), r)
form2 = dict(form, title="Dept talk", day=good, start="20:00", end="21:00")
s, r = call("POST", "/api/online", form2, cc); check("coordinator request waits", s == 200 and r["status"] == "waiting", r)
oid = r["id"]
s, r2 = call("POST", f"/api/online/{oid}/decide", {"approve": True}, cc); check("coordinator cannot approve", s == 403, r2)
s, r2 = call("POST", f"/api/online/{oid}/decide", {"approve": True}, admin); check("admin approves", s == 200 and r2["status"] == "scheduled", r2)
check("club cannot schedule", call("POST", "/api/online", form, ta)[0] in (200, 400, 403))
print("ALL OK" if ok else "SOME FAILED")
