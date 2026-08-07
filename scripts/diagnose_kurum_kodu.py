"""
MEB okul listesi sayfasındaki 'Bilgi' (ⓘ) ve 'Harita' (📍) linklerinin gerçek
href yapısını görmek için teşhis script'i - kurum kodunu nereden
çekebileceğimizi bulmak amacıyla.
"""
from playwright.sync_api import sync_playwright

URL = "https://www.meb.gov.tr/baglantilar/okullar/index.php?ILKODU=6"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto(URL, wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(2000)

    rows = page.query_selector_all("table tr")
    count = 0
    for row in rows:
        cells = row.query_selector_all("td")
        if len(cells) < 2:
            continue
        count += 1
        print(f"\n=== Satır {count}: {cells[0].inner_text().strip()[:60]} ===")
        print("TAM HTML:")
        print(row.inner_html()[:2000])
        if count >= 3:
            break

    browser.close()
