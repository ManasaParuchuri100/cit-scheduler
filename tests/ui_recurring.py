"""Recurring booking in the browser. Usage: python tests/ui_recurring.py OUT_DIR"""
import json, sys, urllib.request
from playwright.sync_api import sync_playwright
OUT = sys.argv[1]; B = "http://localhost:8000"
def call(method, path, body=None, tok=None):
    req = urllib.request.Request(B + path, method=method, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Content-Type": "application/json", **({"Authorization": "Bearer " + tok} if tok else {})})
    with urllib.request.urlopen(req) as r: return json.loads(r.read() or b"null")
admin = call("POST", "/api/login", {"email": "dean@cit.example", "password": "demo"})["token"]; call("POST", "/api/seed", tok=admin)
errs = []
def login(b, email):
    pg = b.new_page(viewport={"width": 1280, "height": 1000}); pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
    pg.goto(B + "/"); pg.click('[data-act="tologin"] >> nth=0'); pg.fill("#lg-email2", email); pg.click("button[type=submit]"); pg.wait_for_selector(".side"); return pg
with sync_playwright() as p:
    b = p.chromium.launch()
    pc = login(b, "club.coding@cit.example")
    pc.click('.side button[data-v="newrequest"]')
    pc.fill("#bf-text", "Coding club rehearsal every Tuesday 6 to 8 pm, 30 people, for 6 weeks")
    pc.fill('[data-bf="week"]', "4"); pc.dispatch_event('[data-bf="week"]', "change")
    pc.click('[data-act="parse"]'); pc.wait_for_selector("text=Assumed, please confirm"); pc.wait_for_timeout(800)
    note = pc.inner_text("#bf-repeat"); print("note:", note)
    assert "6 bookings" in note and "weeks 4, 5, 6, 7, 8, 10" in note, note
    pc.screenshot(path=f"{OUT}/rec_form.png", full_page=True)
    # change the last week by hand, the note follows
    pc.fill('[data-bf="repeat_until"]', "6"); pc.dispatch_event('[data-bf="repeat_until"]', "change"); pc.wait_for_timeout(300)
    assert "3 bookings" in pc.inner_text("#bf-repeat"), pc.inner_text("#bf-repeat")
    pc.fill('[data-bf="repeat_until"]', "10"); pc.dispatch_event('[data-bf="repeat_until"]', "change"); pc.wait_for_timeout(300)
    pc.fill('[data-bf="title"]', "Weekly rehearsal")
    pc.click('[data-act="sendbk"]'); pc.wait_for_selector("h2:text-is(\"Answer\")"); pc.wait_for_timeout(500)
    assert pc.locator("section.card:has(h2:text-is('Answer')) .sess").count() == 6
    pc.screenshot(path=f"{OUT}/rec_answer.png", full_page=True)
    pc.click('.side button[data-v="myrequests"]'); pc.wait_for_timeout(1200)
    print("rows:", pc.locator(".bk").count(), pc.inner_text("main")[:300].replace("\n"," | "))
    assert pc.locator(".bk").filter(has_text="Weekly rehearsal").count() == 6 and "Repeats weekly" in pc.inner_text("main"), "My bookings"
    assert pc.locator('[data-act="approveseries"]').count() == 0
    pc.screenshot(path=f"{OUT}/rec_mine.png", full_page=True)
    # the Dean approves everything once
    pa = login(b, "dean@cit.example"); pa.click('.side button[data-v="bookings"]'); pa.wait_for_timeout(800)
    pa.fill("#bk-week", "4"); pa.dispatch_event("#bk-week", "change"); pa.wait_for_timeout(1000)
    btn = pa.locator('[data-act="approveseries"]'); assert btn.count() == 1 and "Approve all 6 weeks" in btn.inner_text(), btn.count()
    pa.screenshot(path=f"{OUT}/rec_admin.png", full_page=True)
    btn.click(); pa.wait_for_timeout(1500)
    assert pa.locator('[data-act="approveseries"]').count() == 0 and pa.locator('[data-act="approve"]').count() == 0
    pa.fill("#bk-week", "8"); pa.dispatch_event("#bk-week", "change"); pa.wait_for_timeout(1000)
    assert "Approved" in pa.inner_text("main") and pa.locator('[data-act="approve"]').count() == 0, "week 8 should be approved too"
    # cancel this and later weeks as the club
    pc.click('.side button[data-v="myrequests"]'); pc.wait_for_timeout(500)
    pc.once("dialog", lambda d: d.accept())
    pc.locator('[data-act="cancelseries"]').nth(3).click(); pc.wait_for_timeout(2000)
    n = pc.locator(".bk").filter(has_text="Weekly rehearsal").filter(has_text="Cancelled").count(); print("cancelled rows:", n); assert n == 3, n
    pc.screenshot(path=f"{OUT}/rec_cancelled.png", full_page=True)
    b.close()
print("page errors:", errs)
call("POST", "/api/seed", tok=admin)
print("UI RECURRING OK" if not errs else "UI RECURRING ERRORS")
