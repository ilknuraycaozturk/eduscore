"""
tabanpuanlari.net sitesinden il bazında LGS taban puanı / kontenjan verisini çeker.

Bu site MEB'in resmi (ama artık bot korumalı) e-okul sisteminden derlenmiş veriyi
tek bir sayfada (il başına) sunuyor - okul adı, program, 2026/2025 kontenjan,
taban puan, yüzdelik dilim, dil, pansiyon durumu dahil.

ÖNEMLİ: Bu sitenin tam HTML/DOM yapısını önceden göremedik (sandbox'tan erişim
kısıtlı). Bu script TEŞHİS ÇIKTILARI içerir - ilk çalıştırmada beklenen yapı
bulunamazsa, GitHub Actions loglarına bakıp seçicileri güncellememiz gerekebilir
(bugün MEB script'inde yaptığımız gibi).

Kullanım:
    python scrape_tabanpuanlari.py --il ankara --output data/tabanpuan_raw.json
"""
import argparse
import json
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE_URL = "https://tabanpuanlari.net/lgs"

# İl adı -> URL slug eşleşmesi (Türkçe karakterler URL'de genelde sadeleşir)
IL_SLUG_MAP = {
    "ankara": "ankara", "istanbul": "istanbul", "izmir": "izmir",
    # Diğer iller ilk test başarılı olunca eklenecek
}


def scrape_il(il_slug: str, timeout_ms: int = 30000) -> list[dict]:
    url = f"{BASE_URL}/{il_slug}"
    results: list[dict] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        print(f"Sayfa açılıyor: {url}")
        page.goto(url, wait_until="networkidle", timeout=timeout_ms)
        page.wait_for_timeout(2000)  # JS render için ekstra bekleme

        # TEŞHİS 1: Sayfada kaç tane <table> var, her birinde kaç satır?
        tables = page.query_selector_all("table")
        print(f"TEŞHİS: Sayfada {len(tables)} <table> elemanı bulundu.")
        for i, t in enumerate(tables):
            rows = t.query_selector_all("tr")
            print(f"  Tablo {i}: {len(rows)} satır")

        # TEŞHİS 2: 'Kontenjan' veya 'Puan' geçen herhangi bir tekrarlayan kart/satır yapısı var mı?
        # (Site tablo değil, kart/div listesi kullanıyor olabilir)
        possible_rows = page.query_selector_all(
            "[class*='row' i], [class*='card' i], [class*='item' i], [class*='lise' i], li"
        )
        print(f"TEŞHİS: 'row/card/item/lise' class'lı ya da <li> {len(possible_rows)} eleman bulundu.")

        # En büyük tabloyu (en çok satırlı) hedef tablo kabul edelim
        target_table = None
        max_rows = 0
        for t in tables:
            rows = t.query_selector_all("tr")
            if len(rows) > max_rows:
                max_rows = len(rows)
                target_table = t

        if not target_table:
            print("HATA: Hiçbir <table> bulunamadı - site yapısı farklı olabilir (kart/div tabanlı).")
            print("TEŞHİS: Sayfanın ilk 3000 karakteri:")
            print(page.content()[:3000])
            browser.close()
            return results

        rows = target_table.query_selector_all("tr")
        print(f"Hedef tablo seçildi: {len(rows)} satır. İlk satırın hücreleri:")
        if rows:
            first_cells = rows[0].query_selector_all("td, th")
            for c in first_cells:
                print(f"  hücre: '{c.inner_text().strip()}'")

        for row in rows:
            cells = row.query_selector_all("td")
            if len(cells) < 3:
                continue  # başlık satırı
            cell_texts = [c.inner_text().strip() for c in cells]
            results.append({"il_slug": il_slug, "cells": cell_texts})

        browser.close()

    return results


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

    print(f"\nTOPLAM {len(results)} satır (ham hücre verisiyle) -> {out_path}")
    print("NOT: Bu ilk teşhis çalıştırması - hücre verisi henüz alan adlarına "
          "(okul adı, kontenjan, puan vb.) ayrıştırılmadı. Çıktıyı inceleyip "
          "script'i bir sonraki adımda tamamlayacağız.")


if __name__ == "__main__":
    main()
