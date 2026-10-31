import sys, os
from playwright.sync_api import sync_playwright
OUT = sys.argv[1]; os.makedirs(OUT, exist_ok=True)
def login(pg, email):
    pg.goto("http://localhost:8000/"); pg.click('[data-act="tologin"] >> nth=0'); pg.fill("#lg-email2", email); pg.click("button[type=submit]"); pg.wait_for_selector(".side")
with sync_playwright() as p:
    b = p.chromium.launch(); errs = []
    pg = b.new_page(viewport={"width": 1280, "height": 900})
    pg.on("pageerror", lambda e: errs.append(str(e))); pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
    login(pg, "faculty.f07@cit.example")
    pg.screenshot(path=f"{OUT}/fac_ov.png")
    pg.click('button[data-act="askopen"]'); pg.fill("#ask-text", "move my Digital Logic Design lecture to Wednesday afternoon"); pg.click('button[data-act="askgo"]'); pg.wait_for_selector('[data-act="askpick"]')
    pg.screenshot(path=f"{OUT}/ask_choose.png")
    pg.click('[data-act="askpick"] >> nth=0'); pg.wait_for_selector('[data-act="askpreview"]'); pg.screenshot(path=f"{OUT}/ask_change.png")
    pg.click('[data-act="askpreview"]'); pg.wait_for_selector('[data-act="asksend"], .diff', timeout=90000); pg.screenshot(path=f"{OUT}/ask_preview.png")
    pg.click('[data-act="askclose"] >> nth=-1') if False else pg.keyboard.press("Escape")
    pg.reload(); pg.wait_for_selector(".side")
    pg.click('button[data-act="askopen"]'); pg.fill("#ask-text", "why is my Data Structures class on Thursday?"); pg.click('button[data-act="askgo"]'); pg.wait_for_selector(".why-list"); pg.screenshot(path=f"{OUT}/ask_explain.png")
    pg.reload(); pg.wait_for_selector(".side"); pg.click('.side button[data-v="timetable"]'); pg.wait_for_selector(".blk[data-act]"); pg.click(".blk[data-act] >> nth=0"); pg.wait_for_selector(".why-list"); pg.screenshot(path=f"{OUT}/cls_why.png")
    pg.click('[data-act="clstab"][data-v="move"]'); pg.wait_for_selector(".slot"); pg.screenshot(path=f"{OUT}/cls_move.png")
    pg.click('[data-act="clspick"] >> nth=0'); pg.wait_for_selector('[data-act="clssend"], .diff', timeout=90000); pg.screenshot(path=f"{OUT}/cls_preview.png")
    print("errors:", errs); b.close()
