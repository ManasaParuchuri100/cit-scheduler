"""Extra classes in exam week: only exams are hard, everything else is a scored warning."""
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
call("POST", "/api/reset", tok=admin); admin = login("dean@cit.example")
call("POST", "/api/generate", tok=admin)
while True:
    time.sleep(3)
    j = call("GET", "/api/job", tok=admin)[1]
    if j["state"] == "done": break
    if j["state"] == "error": sys.exit("generation failed")
h0 = call("GET", "/api/health", tok=admin)[1]["hard"]
meta = call("GET", "/api/meta", tok=admin)[1]
cse = [f for f in meta["faculty"] if f["department"] == "CSE"]
F = cse[0]["id"]; tf = login(f"faculty.{F.lower()}@cit.example")
cells = call("GET", "/api/timetable?week=1", tok=tf)[1]["cells"]
check("teacher has classes", len(cells) > 0)
c = cells[0]
base = {"session_id": c["id"], "day": "MON", "start": "18:30", "end": "20:00", "size": 60, "topic": "Revision before the exam"}

st, r = call("POST", "/api/extras/check", base, tf)
check("check works after 17:00", st == 200 and not r["hard"], r)
check("evening class has penalty fields", "penalty" in r and r["level"] in ("none", "minor", "some", "many"))
check("room suggestions given", len(r["rooms"]) > 0)

# every exam day has the groups' exam in AM or PM; find one that clashes
hit = None
for d in ["MON", "TUE", "WED", "THU", "FRI", "SAT"]:
    for a, b in (("09:45", "10:45"), ("14:15", "15:15")):
        st, r = call("POST", "/api/extras/check", {**base, "day": d, "start": a, "end": b}, tf)
        if r["hard"]: hit = (d, a, b, r); break
    if hit: break
check("group exam is a hard block", hit is not None)
if hit:
    d, a, b, r = hit
    st, e = call("POST", "/api/extras", {**base, "day": d, "start": a, "end": b}, tf)
    check("cannot book over the group's exam", st >= 400, e)
    check("block names the exam", "exam" in json.dumps(r["hard"]).lower())

# an exam room is blocked
ex = call("GET", "/api/exams", tok=admin)[1]
rows = ex.get("rows") or ex.get("exams") or []
# soft: small room, late finish, lunch -> warns but allowed
st, r = call("POST", "/api/extras/check", {**base, "day": "SAT", "start": "12:30", "end": "21:30", "room": "CR-101", "size": 400}, tf)
soft_txt = json.dumps(r.get("soft"))
check("soft issues do not block", not r["hard"] or "exam" in json.dumps(r["hard"]).lower(), r)
if not r["hard"]:
    check("capacity warns", "seats" in soft_txt)
    check("late + long warn", "21:00" in soft_txt and "3 hours" in soft_txt)
    check("penalty adds up", r["penalty"] >= 7 and r["level"] in ("some", "many"))

# create a clean evening request
good = None
for d in ["MON", "TUE", "WED", "THU", "FRI", "SAT"]:
    st, r = call("POST", "/api/extras/check", {**base, "day": d, "start": "18:30", "end": "20:00"}, tf)
    if r["ok"]: good = d; break
check("found an evening slot", good is not None)
form = {**base, "day": good}
st, x = call("POST", "/api/extras", form, tf)
check("request created (room auto-picked)", st == 200 and x["status"] == "waiting" and x["room"], x)
st, _ = call("POST", "/api/extras", {**form, "topic": ""}, tf)
check("topic required", st >= 400)
st, _ = call("POST", "/api/extras", {**form, "end": "23:30"}, tf)
check("after 22:00 refused", st >= 400)
other = next(f for f in meta["faculty"] if f["id"] != F)
to = login(f"faculty.{other['id'].lower()}@cit.example")
check("other teacher cannot see it", all(r["id"] != x["id"] for r in call("GET", "/api/extras", tok=to)[1]["rows"]))
st, _ = call("POST", f"/api/extras/{x['id']}/decide", {"approve": True}, tf)
check("teacher cannot approve own", st == 403)
st, _ = call("POST", f"/api/extras/{x['id']}/decide", {"approve": True}, to)
check("other teacher cannot approve", st == 403)
dept = x["dept"].lower()
try:
    head = login(f"coordinator.{dept}@cit.example")
except Exception:
    head = admin
check("head sees it", any(r["id"] == x["id"] and r["can_decide"] for r in call("GET", "/api/extras", tok=head)[1]["rows"]))
ov = call("GET", "/api/overview", tok=head)[1]
check("overview counts waiting", ov.get("extras_waiting", 0) >= 1)
st, y = call("POST", f"/api/extras/{x['id']}/decide", {"approve": True}, head)
check("approved", st == 200 and y["status"] == "approved", y)
t9 = call("GET", "/api/timetable?week=9", tok=tf)[1]
check("exam-week timetable lists it", any(e["id"] == x["id"] for e in t9.get("extras", [])))
t1 = call("GET", "/api/timetable?week=1", tok=tf)[1]
check("regular weeks unaffected", not t1.get("extras"))
# a second one at same time warns, not blocks
st, r = call("POST", "/api/extras/check", form, tf)
check("overlap with own extra is soft", st == 200 and any("already have" in s["text"] for s in r["soft"]) and not r["hard"])
# decline path
st, z = call("POST", "/api/extras", {**form, "start": "20:30", "end": "21:30", "topic": "Doubt clearing"}, tf)
check("second request created", st == 200)
st, w = call("POST", f"/api/extras/{z['id']}/decide", {"approve": False, "reason": "Hostel curfew"}, head)
check("declined with reason", st == 200 and w["status"] == "declined" and w["reason"] == "Hostel curfew")
st, v = call("POST", f"/api/extras/{x['id']}/cancel", None, tf)
check("teacher can cancel", st == 200 and v["status"] == "cancelled")
check("exports still valid", call("GET", "/api/health", tok=admin)[1]["hard"] == h0)
print("ALL OK" if ok else "SOME FAILED"); sys.exit(0 if ok else 1)
