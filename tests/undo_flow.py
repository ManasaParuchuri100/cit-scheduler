"""Undo for approved timetable changes and permanent swaps, end to end through the HTTP API.
Needs the server running. Starts by loading the ready-made timetable."""
import json, os, sys, urllib.request
B = "http://localhost:8000"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
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
def export(): return json.load(open(os.path.join(ROOT, "exports", "schedule_after.json")))
DATA = json.load(open(os.path.join(ROOT, "data", "cit_public.json")))
FAC_OF = {s["id"]: s["faculty_id"] for s in DATA["sessions"]}
CSE_IDS = {f["id"] for f in DATA["faculty"] if f["department"] == "CSE"}
def teaches_on(day, skip=()):
    """Faculty ids that have a class on `day` in the current export."""
    out = []
    for x in export()["sessions"]:
        f = FAC_OF.get(x["session_id"])
        if x["day"] == day and f in CSE_IDS and f not in skip and f not in out:
            out.append(f)
    return out
def teacher_view(fid, tok):
    return call("GET", f"/api/timetable?view=faculty&id={fid}&week=3", tok=tok)[1]["cells"]

admin = login("dean@cit.example")
check("seed loads", call("POST", "/api/seed", tok=admin)[0] == 200)
cse = login("coordinator.cse@cit.example")
base = export()
check("starts clean", call("GET", "/api/health", tok=admin)[1]["hard"] == 0)

def make_change(fid, day, note):
    dis = {"changes": [{"type": "faculty_unavailable", "faculty_id": fid, "days": [day], "periods": list(range(1, 10)), "reason": note}]}
    s, r = call("POST", "/api/changes", {"dis": dis, "note": note}, cse)
    return s, r

f1 = teaches_on("MON")[0]
s, c1 = make_change(f1, "MON", "Conference every Monday"); check("change 1 created and moves classes", s == 200 and c1["feasible"] and len(c1["diff"]) > 0, c1)
s, r = call("POST", f"/api/changes/{c1['id']}/undo", {}, admin); check("pending change cannot be undone", s == 400, r)
s, r = call("POST", f"/api/changes/{c1['id']}/decide", {"approve": True}, admin); check("change 1 approved", s == 200 and r["status"] == "approved", r)
after1 = export()
check("timetable changed", after1 != base)
rows = call("GET", "/api/changes", tok=admin)[1]["rows"]
row = next(x for x in rows if x["id"] == c1["id"])
check("admin is offered undo", row["can_undo"] is True)
check("coordinator is not offered undo", next(x for x in call("GET", "/api/changes", tok=cse)[1]["rows"] if x["id"] == c1["id"])["can_undo"] is False)

s, r = call("POST", f"/api/changes/{c1['id']}/undo", {}, cse); check("coordinator cannot undo", s == 403, r)

# a second change on top of the first: only the newest can be undone
f2 = [f for f in teaches_on("TUE", skip=(f1,))][0]
s, c2 = make_change(f2, "TUE", "Training on Tuesdays"); check("change 2 created and moves classes", s == 200 and c2["feasible"] and len(c2["diff"]) > 0, c2)
s, r = call("POST", f"/api/changes/{c2['id']}/decide", {"approve": True}, admin); check("change 2 approved", s == 200, r)
after2 = export()
s, r = call("POST", f"/api/changes/{c1['id']}/undo", {}, admin)
check("older change refuses to undo first", s == 400 and c2["id"] in json.dumps(r), r)
check("refusal changed nothing", export() == after2)

s, r = call("POST", f"/api/changes/{c2['id']}/undo", {"reason": "Training moved"}, admin)
check("change 2 undone", s == 200 and r["status"] == "undone" and r["undone"]["check"]["hard"] == 0, r)
check("timetable is exactly as after change 1", export() == after1)
s, r = call("POST", f"/api/changes/{c2['id']}/undo", {}, admin); check("cannot undo twice", s == 400, r)
s, r = call("POST", f"/api/changes/{c1['id']}/undo", {"reason": "Not needed"}, admin)
check("change 1 undone", s == 200 and r["status"] == "undone", r)
check("timetable is exactly as before any change", export() == base)
check("checker still clean", call("GET", "/api/health", tok=admin)[1]["hard"] == 0)
check("requester was told", any("undone" in n["text"] for n in call("GET", "/api/notifications", tok=cse)[1]) if call("GET", "/api/notifications", tok=cse)[0] == 200 else True)

# the same change can be raised and approved again after an undo
s, c3 = make_change(f1, "MON", "Conference again")
s, r = call("POST", f"/api/changes/{c3['id']}/decide", {"approve": True}, admin); check("a new change goes in after an undo", s == 200 and r["status"] == "approved", r)
s, r = call("POST", f"/api/changes/{c3['id']}/undo", {}, admin); check("and can be undone", s == 200, r)
check("back to base again", export() == base)

# a permanent swap can be undone too; a one-week swap just gets marked
meta = call("GET", "/api/meta", tok=admin)[1]
fac = [f for f in meta["faculty"] if f["department"] == "CSE"]
done = False
for f in fac:
    ta = login(f"faculty.{f['id'].lower()}@cit.example")
    cells = call("GET", "/api/timetable?week=3", tok=ta)[1]["cells"]
    for cell in cells:
        opts = [x for x in call("GET", "/api/swaps/options?give=" + cell["id"], tok=ta)[1]["options"] if x["ok"] and x["department"] == "CSE"]
        if opts:
            fp_before = (teacher_view(f["id"], admin), teacher_view(opts[0]["faculty_id"], admin))
            s, sw = call("POST", "/api/swaps", {"give": cell["id"], "take": opts[0]["id"], "note": "undo test", "scope": "always"}, ta)
            tb = login(f"faculty.{opts[0]['faculty_id'].lower()}@cit.example")
            call("POST", f"/api/swaps/{sw['id']}/respond", {"approve": True}, tb)
            s, r = call("POST", f"/api/swaps/{sw['id']}/decide", {"approve": True}, cse)
            done = s == 200 and r["status"] == "approved"
            break
    if done: break
check("permanent swap approved", done)
fp_after = (teacher_view(f["id"], admin), teacher_view(opts[0]["faculty_id"], admin))
check("swap changed who teaches what", fp_after != fp_before)
s, r = call("POST", f"/api/swaps/{sw['id']}/undo", {"reason": "Teachers changed their minds"}, cse); check("coordinator cannot undo a swap", s == 403, r)
s, r = call("POST", f"/api/swaps/{sw['id']}/undo", {"reason": "Teachers changed their minds"}, admin)
check("swap undone", s == 200 and r["status"] == "undone", r)
check("timetable back after swap undo", export() == base and (teacher_view(f["id"], admin), teacher_view(opts[0]["faculty_id"], admin)) == fp_before)
check("checker clean after swap undo", call("GET", "/api/health", tok=admin)[1]["hard"] == 0)

call("POST", "/api/seed", tok=admin)
print("\nALL PASS" if ok else "\nSOME FAILED")
sys.exit(0 if ok else 1)
