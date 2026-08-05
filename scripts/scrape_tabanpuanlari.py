"""
tabanpuanlari.net sitesinden il bazında LGS taban puanı / kontenjan verisini çeker.

ÖNEMLİ: Bu site sanal kaydırma (virtual scrolling) kullanıyor - DOM'da her an
sadece görünen satırlar (+ biraz tampon) render ediliyor. Bu yüzden sayfayı
adım adım kaydırıp, her adımda görünen satırları program_id'ye göre
tekilleştirerek (dedup) topluyoruz.

Kullanım:
    python scrape_tabanpuanlari.py --il ankara --output data/tabanpuan_raw.json
"""
import argparse
import json
import re
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE_URL = "https://tabanpuanlari.net/lgs"

IL_SLUG_MAP = {
    "ankara": "ankara", "istanbul": "istanbul", "izmir": "izmir",
}

DIL_KEYWORDS = ["İngilizce", "Almanca", "Fransızca", "Arapça", "Çince", "Rusça", "Japonca"]


def parse_ozellikler(text: str) -> dict:
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    result = {"cinsiyet": None, "dil": None, "sure": None, "pansiyon": None}
    for line in lines:
        if line in ("Kız/Erkek", "Kız", "Erkek"):
            result["cinsiyet"] = line
        elif line in DIL_KEYWORDS:
            result["dil"] = line
        elif re.match(r"^\d+\s*yıl$", line):
            result["sure"] = line
        elif "Pansiyon Var" in line:
            result["pansiyon"] = True
        elif "Pansiyon Yok" in line:
            result["pansiyon"] = False
    return result


def parse_number(text: str) -> float | None:
    text = (text or "").strip().replace(".", "").replace(",", ".")
    if not text or text == "-":
        return None
    try:
        return float(text)
    except ValueError:
        return None


def parse_int(text: str) -> int | None:
    text = (text or "").strip()
    if not text or text == "-":
        return None
    try:
        return int(text)
    except ValueError:
        return None


def extract_row(row) -> dict | None:
    cells = row.query_selector_all("td")
    if len(cells) < 7:
        return None

    lise_cell_lines = [l.strip() for l in cells[0].inner_text().strip().split("\n") if l.strip()]
    okul_adi = lise_cell_lines[0] if lise_cell_lines else None
    program_adi = lise_cell_lines[1] if len(lise_cell_lines) > 1 else None
    if not okul_adi:
        return None

    link_el = cells[0].query_selector("a[href*='/programs/']")
    program_id = None
    if link_el:
        href = link_el.get_attribute("href") or ""
        m = re.search(r"/programs/(\d+)", href)
        if m:
            program_id = m.group(1)

    ozellikler = parse_ozellikler(cells[5].inner_text())

    return {
        "okul_adi": okul_adi,
        "program_adi": program_adi,
        "program_id": program_id,
        "kontenjan_2026": parse_int(cells[1].inner_text()),
        "kontenjan_2025": parse_int(cells[2].inner_text()),
        "lgs_puani": parse_number(cells[3].inner_text()),
        "yuzdelik_2025": parse_number(cells[4].inner_text()),
        "cinsiyet": ozellikler["cinsiyet"],
        "dil": ozellikler["dil"],
        "sure": ozellikler["sure"],
        "pansiyon_var": ozellikler["pansiyon"],
    }


def scrape_il(il_slug: str, timeout_ms: int = 30000) -> list[dict]:
    url = f"{BASE_URL}/{il_slug}"
    collected: dict[str, dict] = {}  # program_id (ya da okul+program adı) -> satır

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        print(f"Sayfa açılıyor: {url}")
        page.goto(url, wait_until="networkidle", timeout=timeout_ms)
        page.wait_for_timeout(2000)

        tables = page.query_selector_all("table")
        target_table = None
        max_rows = 0
        for t in tables:
            rows = t.query_selector_all("tr")
            if len(rows) > max_rows:
                max_rows = len(rows)
                target_table = t

        if not target_table:
            print("HATA: Hiçbir <table> bulunamadı.")
            browser.close()
            return []

        # Kaydırılabilir konteyner tabloyu içeren en yakın scroll edilebilir
        # ata olabilir - bulamazsak sayfanın kendisini (window) kaydırırız.
        scroll_container = target_table.evaluate_handle(
            """(table) => {
                let el = table;
                while (el && el !== document.body) {
                    const style = window.getComputedStyle(el);
                    if ((style.overflowY === 'auto' || style.overflowY === 'scroll') && el.scrollHeight > el.clientHeight) {
                        return el;
                    }
                    el = el.parentElement;
                }
                return window;
            }"""
        )

        max_scrolls = 400
        stable_count = 0
        prev_total = 0

        for i in range(max_scrolls):
            rows = target_table.query_selector_all("tr")
            for row in rows:
                data = extract_row(row)
                if not data:
                    continue
                key = data["program_id"] or f"{data['okul_adi']}|{data['program_adi']}"
                # Kontenjan bilgisi eksikse ve daha önce doluysa üzerine yazma
                if key in collected and collected[key].get("kontenjan_2026") and not data.get("kontenjan_2026"):
                    continue
                collected[key] = data

            if len(collected) == prev_total:
                stable_count += 1
            else:
                stable_count = 0
            prev_total = len(collected)

            if stable_count >= 8:  # 8 kaydırma boyunca yeni satır gelmediyse bitti say
                print(f"  Kaydırma {i}: {len(collected)} benzersiz satır (sabitlendi, durduruluyor).")
                break

            scroll_container.evaluate(
                """(el) => {
                    if (el === window) { window.scrollBy(0, 400); }
                    else { el.scrollTop += 400; }
                }"""
            )
            page.wait_for_timeout(150)

            if i % 20 == 0:
                print(f"  Kaydırma {i}: şu ana kadar {len(collected)} benzersiz satır toplandı.")

        browser.close()

    return list(collected.values())


def main():
    parser = argparse.ArgumentParser(description="tabanpuanlari.net'ten LGS verisi çeker.")
    parser.add_argument("--il", required=True, help="İl slug'ı (örn. ankara)")
    parser.add_argument("--output", default="data/tabanpuan_raw.json")
    args = parser.parse_args()

    il_slug = IL_SLUG_MAP.get(args.il.lower(), args.il.lower())
    results = scrape_il(il_slug)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    eksik_kontenjan = sum(1 for r in results if not r.get("kontenjan_2026"))
    print(f"\nTOPLAM {len(results)} program kaydı -> {out_path}")
    print(f"Kontenjan bilgisi eksik olan satır: {eksik_kontenjan} / {len(results)}")
    if results:
        print("--- İlk 3 örnek ---")
        print(json.dumps(results[:3], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
