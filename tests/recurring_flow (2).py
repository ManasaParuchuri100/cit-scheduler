"""Weekly repeating bookings: one request, one approval for the series. Needs the server running."""
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
    print(("PASS " if cond else "FAIL ") + name, extra if not cond else "")
    ok = ok and cond

admin = login("dean@cit.example"); call("POST", "/api/seed", tok=admin)
club = login("club.coding@cit.example"); other = login("club.music@cit.example") if call("POST", "/api/login", {"email": "club.music@cit.example", "password": "demo"})[0] == 200 else login("club.robotics@cit.example")
exam_week = call("GET", "/api/me", tok=admin)[1]["sem"]["exam_week"]
form = {"title": "Weekly rehearsal", "attendance": 30, "duration_periods": 2, "windows": [{"day": "TUE", "from_period": 10, "to_period": 13}],
        "room_types": ["classroom", "lecture_hall", "auditorium"], "needs": [], "requested_category": "club_event", "week": 4, "repeat_until": 10}

s, r = call("POST", "/api/bookings", dict(form, repeat_until=3), club); check("last week before first week is refused", s == 400, r)
s, r = call("POST", "/api/bookings", dict(form, week=4, repeat_until=60), club); check("repeat beyond the semester is refused", s == 400, r)
s, r = call("POST", "/api/bookings", form, club)
check("repeat created", s == 200 and len(r["created"]) == 6, r)
weeks = [c["week"] for c in r["created"]]
check("exam week is skipped and reported", exam_week not in weeks and r["skipped"] == [exam_week] and weeks == [4, 5, 6, 7, 8, 10], (weeks, r.get("skipped")))
sid = r["series_id"]; ids = [c["id"] for c in r["created"]]
check("ids share one number with letters", len({i[:-1] for i in ids}) == 1 and ids[0].endswith("a"), ids)
check("every week got its own answer", all(c["status"] for c in r["created"]))

rows = call("GET", "/api/bookings?all=1&mine=1", tok=club)[1]["rows"]
mine = [x for x in rows if x.get("series_id") == sid]
check("My bookings shows all six with series info", len(mine) == 6 and all(x["series_total"] == 6 for x in mine) and mine[0]["series_weeks"] == weeks, mine[:1])
check("the club cannot approve its own series", all(x["series_waiting"] == 0 for x in mine))
s, r = call("POST", f"/api/bookings/series/{sid}/publish", tok=club); check("club approving own series: nothing published", s == 200 and r["published"] == [] and len(r["refused"]) == 6, r)

wk4 = call("GET", "/api/bookings?week=4", tok=admin)[1]["rows"]
row = next(x for x in wk4 if x["id"] == ids[0])
check("admin sees 'waiting' for the whole series", row["series_waiting"] == 6 and row["can_decide"], row)

s, r = call("POST", f"/api/bookings/series/{sid}/publish", tok=admin)
check("one approval publishes all six", s == 200 and sorted(r["published"]) == sorted(ids) and r["refused"] == [], r)
rows = call("GET", "/api/bookings?all=1&mine=1", tok=club)[1]["rows"]
check("all six are published", all(x["state"] == "published" for x in rows if x.get("series_id") == sid))
check("nothing is left waiting", all(x["series_waiting"] == 0 for x in call("GET", "/api/bookings?all=1", tok=admin)[1]["rows"] if x.get("series_id") == sid))
s, r = call("POST", f"/api/bookings/series/{sid}/publish", tok=admin); check("approving again does nothing", s == 200 and r["published"] == [])
h = call("GET", "/api/health", tok=admin)[1]
check("official checker still has 0 hard problems with the Spectra week occurrence in", h["hard"] == 0, h)

# cancel one week, then the rest of the series
s, r = call("POST", f"/api/bookings/{ids[1]}/cancel", tok=other); check("another club cannot cancel it", s == 403, r)
s, r = call("POST", f"/api/bookings/{ids[1]}/cancel", tok=club); check("owner cancels one week", s == 200, r)
rows = {x["id"]: x for x in call("GET", "/api/bookings?all=1&mine=1", tok=club)[1]["rows"]}
check("only that week is cancelled", rows[ids[1]]["cancelled"] and not rows[ids[0]]["cancelled"] and not rows[ids[2]]["cancelled"])
s, r = call("POST", f"/api/bookings/series/{sid}/cancel", {"from_week": 7}, club)
check("cancel from week 7 on (weeks 7, 8 and 10)", s == 200 and r["cancelled"] == 3, r)
rows = {x["id"]: x for x in call("GET", "/api/bookings?all=1&mine=1", tok=club)[1]["rows"]}
check("weeks 4 and 6 stay, 5 and 7+ are gone", [i for i in ids if not rows[i]["cancelled"]] == [ids[0], ids[2]], {i: rows[i]["cancelled"] for i in ids})
s, r = call("POST", f"/api/bookings/series/{sid}/cancel", {}, other); check("another club cannot cancel the series", s == 403, r)
s, r = call("POST", f"/api/bookings/series/{sid}/cancel", {}, club); check("cancel the rest", s == 200 and r["cancelled"] == 2, r)
check("official checker still clean after cancelling", call("GET", "/api/health", tok=admin)[1]["hard"] == 0)

# a repeat plus several days stays under the limit of 26
two = dict(form, windows=[{"day": "TUE", "from_period": 10, "to_period": 13}, {"day": "THU", "from_period": 10, "to_period": 13}], series=True, week=4, repeat_until=10)
s, r = call("POST", "/api/bookings", two, club); check("two days a week for six weeks = 12 bookings", s == 200 and len(r["created"]) == 12, r)
big = dict(two, windows=two["windows"] + [{"day": "WED", "from_period": 10, "to_period": 13}] * 3, week=3, repeat_until=15)
s, r = call("POST", "/api/bookings", big, club); check("more than 26 is refused with a clear message", s == 400 and "26" in json.dumps(r), r)
# a plain, non-repeating booking still works as before
s, r = call("POST", "/api/bookings", dict(form, repeat_until=None, week=5), club); check("plain booking unchanged", s == 200 and len(r["created"]) == 1 and r["created"][0]["id"].count("-") == 1 and not r["created"][0]["id"][-1].isalpha(), r)

# the plain-English reader picks up repeats
def parse(text, week=4): return call("POST", "/api/bookings/parse", {"text": text, "week": week}, club)[1]
f = parse("Coding club rehearsal every Tuesday 6 to 8 pm, 30 people, for 6 weeks")
check("'for 6 weeks' gives six bookings, skipping exam week", f.get("repeat_until") == 10 and f["week"] == 4, {k: f.get(k) for k in ("repeat_until", "week", "assumptions")})
f = parse("Coding club rehearsal every Tuesday 6 to 8 pm, 30 people")
check("'every Tuesday' alone runs to the last week before exams and says so", f.get("repeat_until") == exam_week - 1 and any("last week before exams" in a for a in f["assumptions"]), f.get("assumptions"))
f = parse("Weekly band practice Thursday 7 to 9 pm, 20 people, until week 8")
check("'until week 8'", f.get("repeat_until") == 8, f.get("repeat_until"))
f = parse("Need a hall tomorrow 4 to 6 pm for 120 people")
check("a one-off request does not repeat", not f.get("repeat_until"))
f = parse("Quiz every day of fest week 6 to 8 pm, 40 people", 7)
check("'every day of fest week' is not a weekly repeat", not f.get("repeat_until"), f.get("repeat_until"))

call("POST", "/api/seed", tok=admin)
print("\nALL PASS" if ok else "\nSOME FAILED")
sys.exit(0 if ok else 1)
