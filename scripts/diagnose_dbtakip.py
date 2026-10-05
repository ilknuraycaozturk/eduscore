"""
dbtakip.com sayfa yapisini kesfeden teshis scripti.
GERCEK CSS selector'lari, filtre mekanizmasini, pagination yapisini,
ve tablo/kart formatinin nasil oldugunu ogrenmek icin - asil scraper'i
YAZMADAN ONCE bu bilgiler gerekiyor.

Kullanim:
    python scripts/diagnose_dbtakip.py --output data/dbtakip_diagnose.json
"""
import argparse
import json
from pathlib import Path

from playwright.sync_api import sync_playwright

URL = "https://dbtakip.com/liseler/i-stanbul"


def diagnose(output_path: str):
    result = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(URL, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(3000)

        # 1) Sayfanin tam HTML'ini kaydet (offline inceleme icin)
        result["full_html_length"] = len(page.content())
        Path("data").mkdir(exist_ok=True)
        with open("data/dbtakip_page.html", "w", encoding="utf-8") as f:
            f.write(page.content())

        # 2) Tur/tip filtresi (select elemanlari) - "Ozel Lise" secenegini bulmak icin
        selects = page.query_selector_all("select")
        result["select_count"] = len(selects)
        result["selects"] = []
        for i, sel in enumerate(selects):
            options = sel.query_selector_all("option")
            opt_data = [{"value": o.get_attribute("value"), "text": o.inner_text()} for o in options[:30]]
            result["selects"].append({
                "index": i,
                "id": sel.get_attribute("id"),
                "name": sel.get_attribute("name"),
                "class": sel.get_attribute("class"),
                "options_sample": opt_data,
                "options_total": len(options),
            })

        # 3) Tablo/kart yapisi - okul satirlarinin nasil goruntulendigini bul
        # Once bir tablo var mi bak
        tables = page.query_selector_all("table")
        result["table_count"] = len(tables)
        if tables:
            rows = tables[0].query_selector_all("tr")
            result["first_table_row_count"] = len(rows)
            if len(rows) > 1:
                result["first_table_row1_html"] = rows[1].inner_html()[:2000]

        # 4) Alternatif: kart/div bazli liste yapisi olabilir
        # "okul" veya "lise" içeren class isimlerini bulmaya calis
        possible_cards = page.query_selector_all("[class*='school'], [class*='lise'], [class*='card'], [class*='row']")
        result["possible_card_count"] = len(possible_cards)
        if possible_cards:
            result["possible_card_sample_html"] = possible_cards[0].evaluate("e => e.outerHTML")[:1500]
            result["possible_card_sample_class"] = possible_cards[0].get_attribute("class")

        # 5) Pagination / "sonraki sayfa" linkleri
        pagination_links = page.query_selector_all("a[href*='page='], [class*='pag']")
        result["pagination_element_count"] = len(pagination_links)
        result["pagination_samples"] = []
        for el in pagination_links[:10]:
            result["pagination_samples"].append({
                "text": el.inner_text()[:50],
                "href": el.get_attribute("href"),
                "class": el.get_attribute("class"),
            })

        # 6) URL parametreleriyle filtreleme dener - "type" gibi bir parametre var mi test et
        page.goto(URL + "?type=ozel-lise", wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(2000)
        result["type_param_test_title"] = page.title()
        result["type_param_test_url_after_load"] = page.url

        browser.close()

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"Teşhis tamamlandı: {output_path}")
    print(json.dumps({k: v for k, v in result.items() if k not in ("full_html_length",)}, ensure_ascii=False, indent=2)[:3000])


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="data/dbtakip_diagnose.json")
    args = parser.parse_args()
    diagnose(args.output)
