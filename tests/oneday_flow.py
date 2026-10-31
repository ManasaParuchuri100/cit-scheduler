"""A swap lasts for the one week asked for. Every other week keeps the usual teacher."""
import json, sys, urllib.request
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
    print(("PASS " if cond else "FAIL ") + name, extra if not cond else ""); ok = ok and cond

admin = login("dean@cit.example")
check("ready-made timetable loads", call("POST", "/api/seed", {}, admin)[0] == 200)
admin = login("dean@cit.example")
h0 = call("GET", "/api/health", tok=admin)[1]["hard"]
sched0 = open("exports/schedule_after.json").read()
meta = call("GET", "/api/meta", tok=admin)[1]
cse = [f for f in meta["faculty"] if f["department"] == "CSE"]
A = cse[0]["id"]; ta = login(f"faculty.{A.lower()}@cit.example")
W = 5
mine = call("GET", f"/api/timetable?week={W}", tok=ta)[1]["cells"]
pick = None
for c in mine:
    o = call("GET", f"/api/swaps/options?give={c['id']}&week={W}", tok=ta)[1]
    good = [x for x in o["options"] if x["ok"] and x["department"] == "CSE"]
    if good: pick = (c, good[0]); break
check("found a one-day swap that works", pick is not None)
give, take = pick
B_id = take["faculty_id"]; tb = login(f"faculty.{B_id.lower()}@cit.example")
cc = login("coordinator.cse@cit.example")

s, r = call("POST", "/api/swaps", {"give": give["id"], "take": take["id"], "scope": "day"}, ta); check("a week is needed for a one-day swap", s == 400, r)
s, r = call("POST", "/api/swaps", {"give": give["id"], "take": take["id"], "scope": "day", "week": 9}, ta); check("exam week refused", s == 400, r)
s, r = call("POST", "/api/swaps", {"give": give["id"], "take": take["id"], "scope": "day", "week": 1}, ta); check("a week that has passed is refused", s == 400, r)
s, r = call("POST", "/api/swaps", {"give": give["id"], "take": take["id"], "scope": "day", "week": W, "note": "Conference"}, ta)
check("one-day request created", s == 200 and r["scope"] == "day" and r["week"] == W, r); sid = r["id"]
s, r2 = call("POST", "/api/swaps", {"give": give["id"], "take": take["id"], "scope": "day", "week": W}, ta); check("same class, same week is already asked", s == 400, r2)
call("POST", f"/api/swaps/{sid}/respond", {"approve": True}, tb)
s, r = call("POST", f"/api/swaps/{sid}/decide", {"approve": True}, cc); check("head approves", s == 200 and r["status"] == "approved", r)

ids = lambda t: {c["id"] for c in t["cells"]}
a5 = call("GET", f"/api/timetable?week={W}", tok=ta)[1]; b5 = call("GET", f"/api/timetable?week={W}", tok=tb)[1]
check("week %d: A no longer teaches the class" % W, give["id"] not in ids(a5) and take["id"] in ids(a5))
check("week %d: B teaches it instead" % W, give["id"] in ids(b5) and take["id"] not in ids(b5))
check("swapped classes are marked", any(c["one_day_swap"] for c in a5["cells"]))
for w in (W - 1, W + 1, 1):
    a = call("GET", f"/api/timetable?week={w}", tok=ta)[1]
    check(f"week {w}: nothing changed for A", give["id"] in ids(a) and take["id"] not in ids(a))
check("other weeks show no swap marks", not any(c["one_day_swap"] for c in call("GET", f"/api/timetable?week={W + 1}", tok=ta)[1]["cells"]))
check("the class list for room view follows the week", any(c["id"] == give["id"] and c["faculty_id"] == B_id for c in call("GET", f"/api/timetable?view=room&id={give['room']}&week={W}", tok=admin)[1]["cells"]))
check("weekly timetable and exports untouched", open("exports/schedule_after.json").read() == sched0 and call("GET", "/api/health", tok=admin)[1]["hard"] == h0)
# next week the same class can be swapped again, separately
o = call("GET", f"/api/swaps/options?give={give['id']}&week={W + 1}", tok=ta)[1]
check("next week is free to swap again", any(x["id"] == take["id"] and x["ok"] for x in o["options"]), [ (x["id"], x["problems"]) for x in o["options"] if x["id"] == take["id"]])
# permanent swaps still exist as an explicit choice
s, r = call("POST", "/api/swaps", {"give": give["id"], "take": take["id"], "scope": "always"}, ta)
check("a permanent swap can still be asked for, as its own choice", s == 200 and r["scope"] == "always" and r["week"] is None, r)
call("POST", f"/api/swaps/{r['id']}/cancel", None, ta)
import datetime as dt
mon = dt.date.fromisoformat(call("GET", "/api/me", tok=admin)[1]["week_monday"]) + dt.timedelta(days=7 * (W - 3))
sw = next(x for x in call("GET", "/api/swaps", tok=admin)[1]["rows"] if x["id"] == sid)
want = lambda d: (mon + dt.timedelta(days=["MON", "TUE", "WED", "THU", "FRI"].index(d))).isoformat()
check("swap shows the real date of each class", sw["give_slot"]["date"] == want(give["day"]) and sw["take_slot"]["date"] == want(take["day"]), (sw["give_slot"]["date"], want(give["day"])))
check("the history names the dates", any(w in " ".join(h["text"] for h in sw["history"]) for w in [sw["give_slot"]["date_label"]]), sw["history"])
check("timetable cells carry dates", all(c.get("date") for c in call("GET", f"/api/timetable?week={W}", tok=ta)[1]["cells"]))
print("ALL OK" if ok else "SOME FAILED"); sys.exit(0 if ok else 1)
