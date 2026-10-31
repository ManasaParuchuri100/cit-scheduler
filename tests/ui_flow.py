"""Click through the real flows in a browser: generate, club request, approval, faculty away, change approval."""
import sys, json, time
from playwright.sync_api import sync_playwright
OUT = sys.argv[1]
def login(b, email):
    pg = b.new_page(viewport={"width": 1280, "height": 900}); errs = []
    pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None); pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto("http://localhost:8000/"); pg.click('[data-act="tologin"] >> nth=0'); pg.fill("#lg-email2", email); pg.click("button[type=submit]"); pg.wait_for_selector(".side")
    return pg, errs
with sync_playwright() as p:
    b = p.chromium.launch()
    # reset + generate as dean
    pg, e1 = login(b, "dean@cit.example")
    pg.once("dialog", lambda d: d.accept())
    pg.click('[data-act="reset"]') if pg.query_selector('[data-act="reset"]') else None
    pg.wait_for_timeout(1500)
    pg.click('[data-act="generate"]'); pg.wait_for_selector(".progress"); pg.screenshot(path=f"{OUT}/gen_running.png")
    t = time.time(); pg.wait_for_selector('text=booking requests to decide', timeout=240000); print("generated in", round(time.time() - t)); pg.screenshot(path=f"{OUT}/gen_done.png")
    # club: natural language
    pc, e2 = login(b, "club.coding@cit.example")
    pc.click('.side button[data-v="newrequest"]')
    pc.fill("#bf-text", "Need a hall for 120 people kal 4 to 6 pm, with mic and projector")
    pc.click('[data-act="parse"]'); pc.wait_for_selector("text=Assumed, please confirm"); pc.wait_for_timeout(900)
    pc.screenshot(path=f"{OUT}/club_parsed.png", full_page=True)
    pc.fill('[data-bf="title"]', "Hackathon kickoff"); 
    pc.fill('[data-bf="week"]', "3"); pc.dispatch_event('[data-bf="week"]', "change"); pc.wait_for_timeout(900)
    pc.click('[data-act="sendbk"]'); pc.wait_for_selector("h2:text-is(\"Answer\")"); pc.wait_for_timeout(500); pc.screenshot(path=f"{OUT}/club_sent.png", full_page=True)
    print("club answer:", pc.inner_text("section.card:has(h2:text-is('Answer')) .sess").replace("\n", " | ")[:200])
    # registrar approves
    pr, e3 = login(b, "registrar@cit.example"); pr.click('.side button[data-v="bookings"]'); pr.wait_for_timeout(800)
    pr.fill("#bk-week", "7"); pr.dispatch_event("#bk-week", "change"); pr.wait_for_timeout(1000)
    pr.click('[data-act="approveall"]'); pr.wait_for_timeout(1200); pr.screenshot(path=f"{OUT}/reg_approved.png")
    # faculty away
    pf, e4 = login(b, "faculty.f07@cit.example"); pf.click('.side button[data-v="requests"]'); pf.wait_for_timeout(800)
    pf.click('label.tg:has([data-chday="TUE"])'); pf.fill("#ch-reason", "Conference"); pf.click('[data-act="chsend"]'); pf.wait_for_selector("text=Waiting for approval"); pf.wait_for_timeout(500)
    pf.screenshot(path=f"{OUT}/fac_away.png", full_page=True)
    # dean cannot approve own, registrar approves faculty's
    pr.click('.side button[data-v="changes"]'); pr.wait_for_timeout(1000); pr.screenshot(path=f"{OUT}/reg_changes.png", full_page=True)
    pr.click('[data-act="chapprove"]'); pr.wait_for_timeout(2500); print("changes after approve:", pr.inner_text("main")[:0], "Approved" in pr.inner_text("main"))
    pr.click('.side button[data-v="overview"]'); pr.wait_for_timeout(1500); pr.screenshot(path=f"{OUT}/reg_overview.png")
    pr.click('[data-act="check"]'); pr.wait_for_timeout(2000); print(pr.inner_text("#checkout"))
    print("errors", e1, e2, e3, e4)
    b.close()
