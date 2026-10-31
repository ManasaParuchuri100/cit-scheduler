"""Logic checks through the real API: explanations, assistant, move requests, rules."""
import json, sys, time, urllib.request
B = "http://localhost:8000"
def call(path, body=None, tok=None):
    req = urllib.request.Request(B + path, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Content-Type": "application/json", **({"Authorization": "Bearer " + tok} if tok else {})})
    try:
        return json.load(urllib.request.urlopen(req, timeout=180))
    except urllib.error.HTTPError as e:
        return {"_err": e.code, **json.load(e)}
def login(e): return call("/api/login", {"email": e, "password": "demo"})["token"]
admin, admin2, fac, dept, club = (login(x) for x in ("dean@cit.example", "registrar@cit.example", "faculty.f07@cit.example", "coordinator.cse@cit.example", "club.coding@cit.example"))
ov = call("/api/overview", tok=admin)
if not ov.get("generated"):
    call("/api/generate", {}, admin)
    while call("/api/job", tok=admin).get("state") == "running": time.sleep(3)
for who, tok, text in [("fac", fac, "why is my Data Structures class at 8 AM"), ("admin", admin, "why was BR-14 rejected"),
                       ("fac", fac, "I am away on Thursday morning"), ("fac", fac, "move my Digital Logic Design lecture to Wednesday afternoon"),
                       ("fac", fac, "I can't teach Digital Logic Design on Friday"), ("dept", dept, "Dr. Ananya Mishra is on leave Monday"),
                       ("admin", admin, "LH-4 is closed on Wednesday for repairs"), ("club", club, "move CS101 to Monday"),
                       ("club", club, "seminar hall kal shaam 6 baje, 2 ghante, 100 log, mic chahiye")]:
    r = call("/api/assistant", {"text": text}, tok)
    print("\n##", who, "|", text, "\n  ->", json.dumps({k: v for k, v in r.items() if k not in ("form", "answers", "dis")})[:420])
    if r.get("answers"):
        for a in r["answers"][:1]: print("  ", a["title"]); [print("    -", l) for l in a["lines"]]
    if r.get("dis"):
        p = call("/api/changes/preview", {"dis": r["dis"]}, tok if who != "club" else fac)
        print("  preview feasible:", p.get("feasible"), "moved", p.get("moved"), "room_only", p.get("room_only"), "why_not", p.get("why_not"), p.get("_err"), p.get("error"))
        for d in (p.get("diff") or [])[:4]: print("    ", d["session_id"], d["type"], d["before"], "->", d["after"], "|", d["why"])
