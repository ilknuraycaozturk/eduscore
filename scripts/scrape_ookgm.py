"""
scrape_ookgm.py
================
EduScor — Aksiyon 1.2: Özel Öğretim Kurumları (ÖOKGM) Veri Çekimi

MEB'in aksine, ÖOKGM'nin (ookgm.meb.gov.tr) kurum listesi düz HTML tablo
olarak sunuluyor (JS render gerektirmiyor) — bu yüzden burada Playwright
değil, basit requests + BeautifulSoup kullanıyoruz. Çok daha hızlı ve
CI'da daha az kaynak tüketir.

Kapsam: dil kursları, sürücü kursları (MTSK), özel eğitim ve rehabilitasyon
merkezleri, etüt/kişisel gelişim kursları, mesleki eğitim merkezleri vb.
(kısaca "tur=kurs" altındaki her şey) + "tur=okul" (özel okullar).

Kullanım:
    python scrape_ookgm.py --il ANKARA --tur kurs --filter-metin "Bağlıca" --output data/ookgm_raw.json
    python scrape_ookgm.py --il ANKARA --tur okul --filter-metin "Bağlıca" --output data/ookgm_okul_raw.json

NOT: ookgm.meb.gov.tr'ye bu sandbox'tan (Claude'un çalıştığı ortam) ağ
erişimi yok — test GitHub Actions'ta ya da yerel makinede yapılmalıdır.
"""

import argparse
import json
import re
import sys
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://ookgm.meb.gov.tr/kurumlar.php"
HEADERS = {"User-Agent": "Mozilla/5.0 (EduScor-Pilot/1.0; egitim-arama-platformu)"}


def fetch_page(il: str, tur: str, sayfa: int) -> str:
    resp = requests.get(
        BASE_URL,
        params={"il": il, "tur": tur, "sayfa": sayfa},
        headers=HEADERS,
        timeout=20,
    )
    resp.raise_for_status()
    return resp.text


def parse_table(html: str) -> list[dict]:
    """Sayfadaki kurum tablosunu ayrıştırır."""
    soup = BeautifulSoup(html, "html.parser")
    rows = []

    table = soup.find("table")
    if not table:
        return rows

    for tr in table.find_all("tr"):
        cells = tr.find_all("td")
        if len(cells) < 5:
            continue  # başlık satırı ya da eksik satır

        # Beklenen sütun sırası: # | İlçe | Kurum Adı | Kurum Türü | Adres | Telefon | Eğitim Programları
        try:
            ilce = cells[1].get_text(strip=True)
            name = cells[2].get_text(strip=True)
            kurum_turu = cells[3].get_text(strip=True)
            adres = cells[4].get_text(strip=True)
            telefon = cells[5].get_text(strip=True) if len(cells) > 5 else ""
            programlar = cells[6].get_text(strip=True) if len(cells) > 6 else ""
        except IndexError:
            continue

        if not name:
            continue

        rows.append({
            "raw_name": name,
            "ilce": ilce,
            "kurum_turu_ham": kurum_turu,
            "address": adres,
            "phone": telefon,
            "programs_raw": programlar,
        })

    return rows


def get_total_pages(html: str) -> int:
    """'934 adet kurum bulundu' gibi bir metinden toplam kayıt sayısını bulup
    sayfa sayısını tahmin eder (sayfa başına satır sayısı sabit değilse
    bu sadece kaba bir üst sınırdır; asıl döngü boş sayfa gelince durur)."""
    match = re.search(r"(\d+)\s*adet kurum bulundu", html)
    if match:
        total = int(match.group(1))
        # Sayfa başına görülen satır sayısı ~65-70 civarı; güvenli bir üst sınır ver
        return max(1, (total // 50) + 2)
    return 50  # bilinmiyorsa güvenli bir üst sınır, boş sayfa gelince zaten duracak


def scrape_all(il: str, tur: str, max_pages: int = 50) -> list[dict]:
    all_rows: list[dict] = []
    first_page_html = fetch_page(il, tur, 1)
    all_rows.extend(parse_table(first_page_html))
    est_pages = min(get_total_pages(first_page_html), max_pages)

    print(f"Tahmini sayfa sayısı: {est_pages} (il={il}, tur={tur})")

    for page in range(2, est_pages + 1):
        time.sleep(0.5)  # sunucuya nazik davran
        html = fetch_page(il, tur, page)
        rows = parse_table(html)
        if not rows:
            print(f"Sayfa {page}: kayıt yok, durduruluyor.")
            break
        all_rows.extend(rows)
        print(f"Sayfa {page}: {len(rows)} kayıt.")

    return all_rows


def main():
    parser = argparse.ArgumentParser(description="ÖOKGM özel kurum/kurs listesini çeker.")
    parser.add_argument("--il", required=True, help="İl adı BÜYÜK HARF (örn. ANKARA)")
    parser.add_argument("--tur", required=True, choices=["kurs", "okul"], help="kurs: özel kurslar, okul: özel okullar")
    parser.add_argument("--filter-metin", default=None, help="Sadece adres/ilçe içinde bu metni içeren kayıtlar tutulur (örn. Bağlıca)")
    parser.add_argument("--output", default="data/ookgm_raw.json")
    args = parser.parse_args()

    print(f"ÖOKGM verisi çekiliyor: il={args.il} tur={args.tur}")
    rows = scrape_all(args.il, args.tur)
    print(f"Toplam {len(rows)} ham kayıt bulundu.")

    if args.filter_metin:
        needle = args.filter_metin.lower()
        rows = [r for r in rows if needle in (r["address"] + r["ilce"]).lower()]
        print(f"'{args.filter_metin}' filtresinden sonra {len(rows)} kayıt kaldı.")

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Kaydedildi -> {out_path}")


if __name__ == "__main__":
    main()
