"""
derive_address_from_website.py
================================
EduScor — website alanı dolu olan (özellikle .meb.k12.tr) kurumların KENDİ
SİTELERİNE gidip, sayfadaki metinden gerçek adresi (mahalle dahil) bulmaya
çalışır. Bulunan mahalle adı, bilinen mahalle->ilçe eşleştirmemizle veya
locations tablosundaki mahalle düzeyi kayıtlarla eşleştirilebilirse,
kurumun location_id'si de daha kesin (mahalle düzeyinde) bir konuma
güncellenir.

Kullanım:
    export SUPABASE_URL="..."
    export SUPABASE_SERVICE_ROLE_KEY="..."
    python derive_address_from_website.py --max-batch 100 --dry-run
"""
import argparse
import os
import re
import sys

import requests

HEADERS_HTTP = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
}

# Adres metninde "... Mahallesi/Mah. ..." kalıbını arıyoruz. Türkçe karakterler
# dahil, "Mahalle(si)" kelimesinden hemen önceki 1-4 kelimeyi mahalle adı adayı
# olarak alıyoruz.
MAHALLE_RE = re.compile(
    r"([A-ZÇĞİÖŞÜ][a-zA-ZçğıöşüÇĞİÖŞÜ]+(?:\s+[A-ZÇĞİÖŞÜ][a-zA-ZçğıöşüÇĞİÖŞÜ]+){0,3})\s+"
    r"(?:Mahallesi|Mah\.)",
)


def turkish_lower(s: str) -> str:
    return s.replace("İ", "i").replace("I", "ı").lower()


def normalize_for_match(s: str) -> str:
    """tr_normalize() SQL fonksiyonuyla aynı mantık - küçük harf + Türkçe
    karakterleri sadeleştir, karşılaştırma için kullanılıyor."""
    s = turkish_lower(s)
    trans = str.maketrans("çğıöşü", "cgiosu")
    return s.translate(trans).strip()


def fetch_all_paginated(base_url: str, headers: dict, path: str, page_size: int = 1000) -> list[dict]:
    all_rows, offset = [], 0
    sep = "&" if "?" in path else "?"
    while True:
        resp = requests.get(f"{base_url}{path}{sep}limit={page_size}&offset={offset}", headers=headers)
        resp.raise_for_status()
        page = resp.json()
        all_rows.extend(page)
        if len(page) < page_size:
            break
        offset += page_size
    return all_rows


def find_mahalle_candidate(website: str, timeout_s: int = 15) -> str | None:
    """Kurumun web sitesinin ana sayfasını basit bir HTTP isteğiyle çeker
    (Playwright'a gerek yok - bu tür siteler genelde JS'e bağımlı değil) ve
    metninde bir 'X Mahallesi' kalıbı arar."""
    try:
        resp = requests.get(website, headers=HEADERS_HTTP, timeout=timeout_s)
        resp.raise_for_status()
    except Exception:
        return None

    # Basit bir HTML->metin temizliği (BeautifulSoup'a gerek kalmadan hızlıca)
    text = re.sub(r"<[^>]+>", " ", resp.text)
    text = re.sub(r"\s+", " ", text)

    m = MAHALLE_RE.search(text)
    if not m:
        return None
    return m.group(1).strip()


def main():
    parser = argparse.ArgumentParser(description="Web sitesinden adres/mahalle türetir.")
    parser.add_argument("--max-batch", type=int, default=100)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    supabase_url = os.environ.get("SUPABASE_URL")
    service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not supabase_url or not service_key:
        print("HATA: SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY ortam değişkenleri eksik.")
        sys.exit(1)

    headers = {
        "apikey": service_key,
        "Authorization": f"Bearer {service_key}",
        "Content-Type": "application/json",
    }

    print("Bilinen mahalle->ilçe eşleştirmeleri yükleniyor...")
    mahalleler = fetch_all_paginated(supabase_url, headers, "/rest/v1/mahalle_ilce_eslesme?select=mahalle_adi,ilce_location_id,il_adi")
    mahalle_lookup = {normalize_for_match(m["mahalle_adi"]): m for m in mahalleler}
    print(f"  {len(mahalle_lookup)} mahalle biliniyor.")

    print("Mahalle düzeyindeki mevcut konumlar yükleniyor...")
    neighborhood_locations = fetch_all_paginated(
        supabase_url, headers,
        "/rest/v1/locations?select=id,name,parent_id&level=eq.neighborhood",
    )
    neighborhood_lookup = {normalize_for_match(l["name"]): l for l in neighborhood_locations}
    print(f"  {len(neighborhood_lookup)} mahalle düzeyinde konum kayıtlı.")

    print(f"E-postası/websitesi olan, adresi eksik kurumlar aranıyor (en fazla {args.max_batch})...")
    resp = requests.get(
        f"{supabase_url}/rest/v1/institutions"
        f"?select=id,name,website,location_id,address"
        f"&website=not.is.null&address=is.null"
        f"&order=id&limit={args.max_batch}",
        headers=headers,
    )
    resp.raise_for_status()
    todo = resp.json()
    print(f"Toplam {len(todo)} kurum bu çalıştırmada denenecek.")

    processed, bulundu, mahalle_eslesti = 0, 0, 0
    for inst in todo:
        processed += 1
        website = inst["website"]
        if not website.startswith("http"):
            website = "https://" + website

        candidate = find_mahalle_candidate(website)
        if not candidate:
            continue

        bulundu += 1
        norm_candidate = normalize_for_match(candidate)

        # Önce tam konum (neighborhood) tablosunda ara, yoksa mahalle
        # eşleştirme tablosuna (ilçe düzeyi) düş.
        new_location_id = None
        if norm_candidate in neighborhood_lookup:
            new_location_id = neighborhood_lookup[norm_candidate]["id"]
        elif norm_candidate in mahalle_lookup:
            new_location_id = mahalle_lookup[norm_candidate]["ilce_location_id"]

        address_text = f"{candidate} Mahallesi"
        payload = {"address": address_text}
        if new_location_id and new_location_id != inst["location_id"]:
            payload["location_id"] = new_location_id
            mahalle_eslesti += 1

        print(f"[{'DRY-RUN' if args.dry_run else 'YAZILDI'}] {inst['name']} -> mahalle='{candidate}'"
              + (f", konum güncellendi" if "location_id" in payload else ""))

        if not args.dry_run:
            r = requests.patch(
                f"{supabase_url}/rest/v1/institutions?id=eq.{inst['id']}",
                headers=headers, json=payload,
            )
            if r.status_code not in (200, 204):
                print(f"  UYARI: yazılamadı -> {r.status_code} {r.text[:200]}")

    print(f"\nTamamlandı: {processed} kurum denendi, {bulundu} adres bulundu, "
          f"{mahalle_eslesti} kurumun konumu daha kesin hale getirildi.")


if __name__ == "__main__":
    main()
