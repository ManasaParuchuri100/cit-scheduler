"""Past events are deleted; approvers can cancel; exports stay valid."""
import copy, os, sys, tempfile, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["CIT_STATE"] = os.path.join(tempfile.mkdtemp(), "state.json")
from cit.store import Store
ok = True
def check(n, c, x=""):
    global ok; print(("PASS " if c else "FAIL ") + n, "" if c else x); ok = ok and c
s = Store()
check("seed loaded", s.generated and len(s.requests) > 20)
h0 = s.health()["hard"]
n0 = len(s.requests)
# 1. nothing in the future is touched
check("future events kept", s.purge_past(force=True) == 0 and len(s.requests) == n0)
# 2. online lecture and extra class in a past week are removed, a later one is kept
base = {"title": "x", "speaker": "y", "org": "", "day": "WED", "start": "18:00", "end": "19:00", "link": "https://meet.google.com/a", "groups": ["Y1-A"], "notes": "", "status": "scheduled"}
s.online += [dict(base, id="OL-90", week=2), dict(base, id="OL-91", week=5)]
s.extras += [{"id": "XC-90", "week": 2, "day": "MON", "start": "18:00", "end": "19:00", "status": "approved"}, {"id": "XC-91", "week": 9, "day": "MON", "start": "18:00", "end": "19:00", "status": "approved"}]
g = s.purge_past(force=True)
check("past online and extra removed", g == 2 and [o["id"] for o in s.online] == ["OL-91"] and [x["id"] for x in s.extras] == ["XC-91"], (g, s.online, s.extras))
# 3. same week: earlier today passed, later today not
mon9 = dt.datetime(2026, 11, 4, 12, 0)             # a Wednesday, noon
check("earlier day is past", s._is_past(3, "TUE", "18:00", mon9))
check("later today is not", not s._is_past(3, "WED", "18:00", mon9))
check("earlier today is past", s._is_past(3, "WED", "11:00", mon9))
check("weekend counts as before Monday", not s._is_past(3, "MON", "09:00", dt.datetime(2026, 10, 31, 20, 0)))
# 4. once the fest week has passed, bookings leave the app but the export stays valid
s.current_week = 8
live_before = len(s.decisions)
g = s.purge_past(force=True)
check("fest week events removed", g >= n0 and not s.requests and not s.decisions, (g, len(s.requests)))
check("kept for the export", len(s.archive["requests"]) == n0)
check("export still validates", s.health()["hard"] == h0 and s.health()["booking"].get("booking_score") == 67.0, s.health())
ex = s.export_schedule("current")
check("export still lists every booking", len(ex["fest_week"]["bookings"]) == n0, len(ex["fest_week"]["bookings"]))
s2 = Store(s.path)
check("survives restart", not s2.requests and len(s2.archive["requests"]) == n0)
# 5. approver can cancel
s3 = Store(os.path.join(tempfile.mkdtemp(), "s.json"))
s3.load_seed() if not s3.generated else None
cse = s3.users["coordinator.cse@cit.example"]
rid = next((i for i, d in s3.decisions.items() if "CSE" in d.get("lab_departments", []) and not d.get("overrides") and next(r for r in s3.requests if r["id"] == i)["owner"] != cse["email"]), None)
check("found a CSE lab booking to approve", rid is not None)
other = s3.users["coordinator.ece@cit.example"]
try: s3.cancel_booking(other, rid); bad = True
except PermissionError: bad = False
check("another department cannot cancel it", not bad)
s3.cancel_booking(cse, rid)
d = s3.decisions[rid]
check("CSE coordinator cancelled it", d["status"] == "rejected" and "Cancelled by" in d["reason"], d)
print("ALL OK" if ok else "SOME FAILED"); sys.exit(0 if ok else 1)
