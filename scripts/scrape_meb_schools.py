"""
scrape_meb_schools.py
======================
EduScor — Aksiyon 1.1: MEB Resmi Veri Çekimi (Seeding)

MEB'in "Okullar ve Diğer Kurumlar" sayfası (www.meb.gov.tr/baglantilar/okullar/)
tablo verisini AJAX ile sonradan yüklüyor; düz HTTP fetch bu yüzden çalışmıyor.
Bu script Playwright (headless Chromium) kullanarak sayfayı gerçekten render eder,
tablo dolduktan sonra satırları okur.

Kullanım:
    python scrape_meb_schools.py --il-kodu 6 --ilce-kodu 27 --output data/etimesgut_raw.json

İl/ilçe kodları için: https://www.meb.gov.tr/baglantilar/okullar/index.php
(il kodu plaka koduyla aynıdır; Ankara = 6)

NOT: Bu script meb.gov.tr'ye canlı erişim gerektirir. Geliştirme sandbox'ında
(Claude'un çalıştığı ortamda) bu domain'e ağ erişimi yok — bu yüzden test
GitHub Actions üzerinde ya da yerel makinenizde yapılmalıdır.
"""

import argparse
import json
import sys
import time
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("Playwright kurulu değil. Kurulum için: pip install playwright && playwright install chromium")
    sys.exit(1)


MEB_URL = "https://www.meb.gov.tr/baglantilar/okullar/index.php"


def scrape_okullar(il_kodu: str, ilce_kodu: str | None = None, timeout_ms: int = 20000) -> list[dict]:
    """MEB okullar tablosunu render edip satırları döndürür."""
    url = f"{MEB_URL}?ILKODU={il_kodu}"
    if ilce_kodu:
        url += f"&ILCEKODU={ilce_kodu}"

    results: list[dict] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, wait_until="networkidle", timeout=timeout_ms)

        # Tablo AJAX ile dolduğu için satırların görünmesini bekle
        try:
            page.wait_for_selector("table tr td", timeout=timeout_ms)
        except Exception:
            print(f"UYARI: {url} için tablo satırı bulunamadı (boş sonuç ya da sayfa yapısı değişmiş olabilir).")
            browser.close()
            return results

        rows = page.query_selector_all("table tr")
        for row in rows:
            cells = row.query_selector_all("td")
            if len(cells) < 2:
                continue  # başlık satırı ya da boş satır

            name = cells[0].inner_text().strip()
            info = cells[1].inner_text().strip() if len(cells) > 1 else ""

            # Harita sütununda genelde lat/lng barındıran bir link/onclick olur
            lat, lng = None, None
            if len(cells) > 2:
                map_link = cells[2].query_selector("a")
                if map_link:
                    href = map_link.get_attribute("href") or ""
                    onclick = map_link.get_attribute("onclick") or ""
                    coords_source = href + onclick
                    lat, lng = _extract_coords(coords_source)

            if not name:
                continue

            results.append({
                "raw_name": name,
                "raw_info": info,
                "lat": lat,
                "lng": lng,
                "il_kodu": il_kodu,
                "ilce_kodu": ilce_kodu,
            })

        browser.close()

    return results


def _extract_coords(text: str) -> tuple[float | None, float | None]:
    """href/onclick içinden basit bir regex ile lat,lng çıkarmayı dener."""
    import re
    match = re.search(r"(-?\d{1,3}\.\d+)\s*,\s*(-?\d{1,3}\.\d+)", text)
    if match:
        return float(match.group(1)), float(match.group(2))
    return None, None


def main():
    parser = argparse.ArgumentParser(description="MEB okul listesini çeker (Playwright).")
    parser.add_argument("--il-kodu", required=True, help="İl plaka kodu (Ankara=6)")
    parser.add_argument("--ilce-kodu", default=None, help="İlçe kodu (opsiyonel)")
    parser.add_argument("--output", default="data/meb_raw.json", help="Çıktı JSON dosyası")
    args = parser.parse_args()

    print(f"MEB verisi çekiliyor: il={args.il_kodu} ilçe={args.ilce_kodu}")
    data = scrape_okullar(args.il_kodu, args.ilce_kodu)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"{len(data)} kayıt bulundu -> {out_path}")


if __name__ == "__main__":
    main()
