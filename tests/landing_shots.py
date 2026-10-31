import sys, os
from playwright.sync_api import sync_playwright
OUT = sys.argv[1]; os.makedirs(OUT, exist_ok=True)
with sync_playwright() as p:
    b = p.chromium.launch(); errs = []
    for name, vp in (("desk", {"width": 1440, "height": 860}), ("phone", {"width": 390, "height": 800})):
        pg = b.new_page(viewport=vp); pg.on("pageerror", lambda e: errs.append(str(e))); pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
        pg.goto("http://localhost:8000/"); 
        for t in (500, 1300, 3600):
            pg.wait_for_timeout(t if t == 500 else (800 if t == 1300 else 2300)); pg.screenshot(path=f"{OUT}/land_{name}_{t}.png")
        pg.evaluate("document.getElementById('l-roles').scrollIntoView()"); pg.wait_for_timeout(1500); pg.screenshot(path=f"{OUT}/land_{name}_roles.png")
        pg.evaluate("document.getElementById('l-rules').scrollIntoView()"); pg.wait_for_timeout(2000); pg.screenshot(path=f"{OUT}/land_{name}_rules.png")
    print("errors", errs); b.close()
