"""Open the site as each role in headless Chromium, visit every tab, save screenshots, print JS errors."""
import sys
from playwright.sync_api import sync_playwright
OUT = sys.argv[1] if len(sys.argv) > 1 else "/tmp/shots"
import os; os.makedirs(OUT, exist_ok=True)
plan = {"admin": ("dean@cit.example", ["overview", "timetable", "rooms", "bookings", "changes", "exams"]),
        "dept": ("coordinator.cse@cit.example", ["overview", "timetable", "rooms", "bookings", "changes"]),
        "fac": ("faculty.f07@cit.example", ["overview", "timetable", "requests"]),
        "club": ("club.coding@cit.example", ["overview", "rooms", "newrequest", "myrequests"])}
with sync_playwright() as p:
    b = p.chromium.launch()
    for name, (email, tabs) in plan.items():
        pg = b.new_page(viewport={"width": 1280, "height": 900}); errs = []
        pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto("http://localhost:8000/")
        if name == "admin":
            pg.wait_for_timeout(3500); pg.screenshot(path=f"{OUT}/landing.png")
        pg.click('[data-act="tologin"] >> nth=0')
        if name == "admin":
            pg.screenshot(path=f"{OUT}/login.png")
        pg.fill("#lg-email2", email); pg.click("button[type=submit]"); pg.wait_for_selector(".side")
        for t in tabs:
            pg.click(f'.side button[data-v="{t}"]'); pg.wait_for_timeout(1200)
            pg.screenshot(path=f"{OUT}/{name}_{t}.png")
        print(name, errs)
    b.close()
