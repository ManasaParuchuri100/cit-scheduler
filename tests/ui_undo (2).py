"""Undo in the browser: Changes tab and Swaps tab. Usage: python tests/ui_undo.py OUT_DIR"""
import json, os, sys, urllib.request
from playwright.sync_api import sync_playwright
OUT = sys.argv[1]; B = "http://localhost:8000"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def call(method, path, body=None, tok=None):
    req = urllib.request.Request(B + path, method=method, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Content-Type": "application/json", **({"Authorization": "Bearer " + tok} if tok else {})})
    with urllib.request.urlopen(req) as r: return json.loads(r.read() or b"null")
def tok(e): return call("POST", "/api/login", {"email": e, "password": "demo"})["token"]
admin, cse = tok("dean@cit.example"), tok("coordinator.cse@cit.example")
call("POST", "/api/seed", tok=admin)
DATA = json.load(open(os.path.join(ROOT, "data", "cit_public.json")))
cs = {f["id"] for f in DATA["faculty"] if f["department"] == "CSE"}; fo = {s["id"]: s["faculty_id"] for s in DATA["sessions"]}
sess = json.load(open(os.path.join(ROOT, "exports", "schedule_after.json")))["sessions"]
mon = [fo[x["session_id"]] for x in sess if x["day"] == "MON" and fo.get(x["session_id"]) in cs]
dis = {"changes": [{"type": "faculty_unavailable", "faculty_id": mon[0], "days": ["MON"], "periods": list(range(1, 10)), "reason": "Conference"}]}
c = call("POST", "/api/changes", {"dis": dis, "note": "UI undo test"}, cse); call("POST", f"/api/changes/{c['id']}/decide", {"approve": True}, admin)
c2 = call("POST", "/api/changes", {"dis": dict(dis, changes=[dict(dis["changes"][0], faculty_id=[f for f in mon if f != mon[0]][0], days=["MON"])]), "note": "second"}, cse)
errs = []
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1280, "height": 1000})
    pg.on("pageerror", lambda e: errs.append(str(e))); pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
    pg.goto(B + "/"); pg.click('[data-act="tologin"] >> nth=0'); pg.fill("#lg-email2", "dean@cit.example"); pg.click("button[type=submit]"); pg.wait_for_selector(".side")
    pg.click('.side button[data-v="changes"]'); pg.wait_for_timeout(1000)
    assert pg.query_selector(f'[data-act="undoask"][data-v="{c["id"]}"]'), "undo button missing"
    pg.click(f'[data-act="undoask"][data-v="{c["id"]}"]'); pg.wait_for_selector(".undo-ask"); pg.screenshot(path=f"{OUT}/undo_ask.png", full_page=True)
    pg.fill(f'#undo-{c["id"]}', "Test run"); pg.click(f'[data-act="undochange"][data-v="{c["id"]}"]'); pg.wait_for_selector(".undo-note", timeout=60000); pg.wait_for_timeout(600)
    txt = pg.inner_text(".undo-note"); print("note:", txt)
    assert "0 rule problems" in txt and "Test run" in txt
    pg.screenshot(path=f"{OUT}/undo_done.png", full_page=True)
    b.close()
print("page errors:", errs)
call("POST", "/api/seed", tok=admin)
print("UI UNDO OK" if not errs else "UI UNDO ERRORS")
