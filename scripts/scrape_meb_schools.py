"""
load_to_supabase.py
====================
EduScor — scrape_meb_schools.py çıktısını (ham JSON) temizleyip
Supabase 'institutions' tablosuna yazar.

Kullanım:
    export SUPABASE_URL="https://xxxx.supabase.co"
    export SUPABASE_SERVICE_ROLE_KEY="..."   # service_role key (RLS'i bypass eder, sadece CI/CD'de kullanın)
    python load_to_supabase.py --input data/etimesgut_raw.json --filter-mahalle "Bağlıca"

Notlar:
- Bu script Aksiyon 1.3 (Taslak Veri Şeffaflık Uyarısı) prensibine uyar:
  eklenen her kayıt is_verified=false ve açıklayıcı bir 'description' ile işaretlenir.
- --filter-mahalle verilirse, sadece raw_info (adres) alanında o metni içeren
  kayıtlar aktarılır (pilot bölge: Bağlıca).
"""

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

import requests

TYPE_KEYWORDS = [
    ("anaokulu", ["anaokulu", "anasınıfı", "kreş"]),
    ("ilkokul", ["ilkokul", "i̇lköğretim okulu"]),
    ("ortaokul", ["ortaokul"]),
    ("lise", ["lise", "fen lisesi", "anadolu lisesi", "imam hatip"]),
]

DRAFT_NOTICE = (
    "Bu sayfadaki bilgiler MEB'in kamuya açık kaynaklarından otomatik olarak "
    "derlenmiştir. Doğruluğunu kontrol ediniz."
)


def geocode(query: str) -> tuple[float | None, float | None]:
    """OpenStreetMap Nominatim ile ücretsiz, açık kaynak geocoding.
    Kullanım politikası gereği: 1 istek/saniye sınırı ve tanımlayıcı User-Agent zorunlu.
    https://operations.osmfoundation.org/policies/nominatim/
    """
    try:
        resp = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": query, "format": "json", "limit": 1},
            headers={"User-Agent": "EduScor-Pilot/1.0 (egitim-arama-platformu)"},
            timeout=10,
        )
        resp.raise_for_status()
        results = resp.json()
        if results:
            lat, lon = float(results[0]["lat"]), float(results[0]["lon"])
            print(f"GEOCODE OK: '{query}' -> {lat}, {lon}")
            return lat, lon
        print(f"GEOCODE SONUÇ YOK: '{query}'")
    except Exception as e:
        print(f"GEOCODE HATA: '{query}' -> {e}")
    return None, None


def normalize_name(name: str) -> str:
    """MEB isimlerindeki 'İL - İLÇE - ' önekini ve 'Özel' gibi kelimeleri
    temizleyerek karşılaştırılabilir bir isim üretir.
    Örn: 'ANKARA - ETİMESGUT - Bağlıca İlkokulu' -> 'bağlıca ilkokulu'
    """
    n = name.strip().lower()
    # "X - Y - Gerçek İsim" kalıbındaki il/ilçe önekini at
    n = re.sub(r"^[^-]+-\s*[^-]+-\s*", "", n)
    n = n.replace("özel", "").strip()
    n = re.sub(r"\s+", " ", n)
    return n


def find_existing_match(new_name: str, existing: list[dict]) -> dict | None:
    """Aynı okulun veritabanında zaten (farklı yazımla) var olup olmadığını kontrol eder."""
    target = normalize_name(new_name)
    for row in existing:
        existing_norm = normalize_name(row["name"])
        if target == existing_norm or target in existing_norm or existing_norm in target:
            return row
    return None


def guess_type(name: str) -> str | None:
    lower = name.lower()
    for slug, keywords in TYPE_KEYWORDS:
        if any(k in lower for k in keywords):
            return slug
    return None


def load_raw(path: str) -> list[dict]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def get_lookup(base_url: str, headers: dict, table: str) -> dict[str, str]:
    """slug/name -> id sözlüğü döndürür.
    - institution_types, categories: eşleştirme anahtarı 'slug' (bu tablolarda 'name' sütunu yok, 'name_tr' var)
    - locations: eşleştirme anahtarı 'name'
    """
    if table in ("institution_types", "categories"):
        resp = requests.get(f"{base_url}/rest/v1/{table}?select=id,slug", headers=headers)
        resp.raise_for_status()
        return {r["slug"]: r["id"] for r in resp.json()}

    resp = requests.get(f"{base_url}/rest/v1/{table}?select=id,name", headers=headers)
    resp.raise_for_status()
    return {r["name"]: r["id"] for r in resp.json()}


def get_existing_institutions(base_url: str, headers: dict, location_id: str) -> list[dict]:
    resp = requests.get(
        f"{base_url}/rest/v1/institutions?select=id,name,address,lat,lng&location_id=eq.{location_id}",
        headers=headers,
    )
    resp.raise_for_status()
    return resp.json()


def main():
    parser = argparse.ArgumentParser(description="MEB ham verisini Supabase'e yükler.")
    parser.add_argument("--input", required=True, help="scrape_meb_schools.py çıktısı JSON dosyası")
    parser.add_argument("--filter-mahalle", default=None, help="Sadece bu mahalleyi içeren adresler aktarılır")
    parser.add_argument("--location-name", required=True, help="Kayıtların bağlanacağı locations.name (örn. 'Bağlıca')")
    parser.add_argument("--category-slug", default="okul-oncesi-k12")
    parser.add_argument("--dry-run", action="store_true", help="Sadece ne ekleneceğini yazdır, Supabase'e yazma")
    args = parser.parse_args()

    supabase_url = os.environ.get("SUPABASE_URL")
    service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not args.dry_run and (not supabase_url or not service_key):
        print("HATA: SUPABASE_URL ve SUPABASE_SERVICE_ROLE_KEY ortam değişkenleri gerekli.")
        sys.exit(1)

    raw = load_raw(args.input)
    print(f"{len(raw)} ham kayıt okundu.")

    if args.filter_mahalle:
        raw = [r for r in raw if args.filter_mahalle.lower() in (r.get("raw_info") or "").lower()
               or args.filter_mahalle.lower() in (r.get("raw_name") or "").lower()]
        print(f"'{args.filter_mahalle}' filtresinden sonra {len(raw)} kayıt kaldı.")

    prepared = []
    skipped = 0
    for r in raw:
        type_slug = guess_type(r["raw_name"])
        if not type_slug:
            skipped += 1
            continue

        lat, lng = r.get("lat"), r.get("lng")
        address = r.get("raw_info")

        if not lat or not lng:
            clean_name = normalize_name(r["raw_name"]).title()
            geocode_query = f"{clean_name}, Etimesgut, Ankara, Türkiye"
            lat, lng = geocode(geocode_query)
            if not lat:
                time.sleep(1)
                fallback_query = f"{clean_name}, Ankara, Türkiye"
                lat, lng = geocode(fallback_query)
            is_approx_location = False
            if not lat:
                # Bina OSM'de haritalanmamış olabilir (küçük/yeni okullarda sık görülür).
                # Son çare: mahalle merkezini kullan, yaklaşık konum olarak işaretle.
                time.sleep(1)
                mahalle_query = f"{args.location_name}, Etimesgut, Ankara, Türkiye"
                lat, lng = geocode(mahalle_query)
                is_approx_location = bool(lat)
            time.sleep(1)  # Nominatim kullanım politikası: en fazla 1 istek/saniye
        else:
            is_approx_location = False

        description = DRAFT_NOTICE
        if is_approx_location:
            description += (
                " Not: Bu kurumun tam adresi bulunamadığı için harita konumu "
                f"'{args.location_name}' mahalle merkezine yaklaşık olarak yerleştirilmiştir."
            )

        prepared.append({
            "name": r["raw_name"].strip(),
            "institution_type_slug": type_slug,
            "address": address,
            "lat": lat,
            "lng": lng,
            "is_public": True,  # bu uç nokta resmi MEB okulları için; özel kurumlar ayrı script (ookgm) ile işlenir
            "is_verified": False,
            "description": description,
        })

    print(f"{len(prepared)} kayıt tipi tanınarak hazırlandı, {skipped} kayıt tipi tanınamadığı için atlandı.")

    if args.dry_run:
        print(json.dumps(prepared[:5], ensure_ascii=False, indent=2))
        print("... (dry-run, Supabase'e yazılmadı)")
        return

    headers = {
        "apikey": service_key,
        "Authorization": f"Bearer {service_key}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }

    type_lookup = get_lookup(supabase_url, headers, "institution_types")
    location_lookup = get_lookup(supabase_url, headers, "locations")
    category_lookup = get_lookup(supabase_url, headers, "categories")

    location_id = location_lookup.get(args.location_name)
    if not location_id:
        print(f"HATA: '{args.location_name}' locations tablosunda bulunamadı.")
        sys.exit(1)

    existing = get_existing_institutions(supabase_url, headers, location_id)
    print(f"Bu konumda {len(existing)} mevcut kurum bulundu, çakışma kontrolü yapılacak.")

    inserted, enriched, skipped_dupe = 0, 0, 0
    for item in prepared:
        match = find_existing_match(item["name"], existing)

        if match:
            # Aynı okul zaten var — sadece eksik alanları (adres/koordinat) doldur, yeni satır açma
            needs_update = {}
            if not match.get("address") and item["address"]:
                needs_update["address"] = item["address"]
            if not match.get("lat") and item["lat"]:
                needs_update["lat"] = item["lat"]
            if not match.get("lng") and item["lng"]:
                needs_update["lng"] = item["lng"]

            if needs_update:
                resp = requests.patch(
                    f"{supabase_url}/rest/v1/institutions?id=eq.{match['id']}",
                    headers=headers, json=needs_update,
                )
                if resp.status_code in (200, 204):
                    enriched += 1
                    print(f"ZENGİNLEŞTİRİLDİ: '{item['name']}' -> mevcut kayıt '{match['name']}' güncellendi ({list(needs_update.keys())})")
                else:
                    print(f"UYARI: '{item['name']}' güncellenemedi -> {resp.status_code} {resp.text[:200]}")
            else:
                skipped_dupe += 1
                print(f"ATLANDI (zaten var, eklenecek yeni bilgi yok): '{item['name']}' ~ '{match['name']}'")
            continue

        type_id = type_lookup.get(item["institution_type_slug"])
        if not type_id:
            continue
        payload = {
            "name": item["name"],
            "institution_type_id": type_id,
            "category_id": category_lookup.get(args.category_slug),
            "location_id": location_id,
            "is_public": item["is_public"],
            "address": item["address"],
            "lat": item["lat"],
            "lng": item["lng"],
            "is_verified": item["is_verified"],
            "description": item["description"],
        }
        resp = requests.post(f"{supabase_url}/rest/v1/institutions", headers=headers, json=payload)
        if resp.status_code in (200, 201):
            inserted += 1
        else:
            print(f"UYARI: '{item['name']}' eklenemedi -> {resp.status_code} {resp.text[:200]}")

    print(f"Tamamlandı: {inserted} yeni kurum eklendi, {enriched} mevcut kurum zenginleştirildi, {skipped_dupe} zaten var olduğu için atlandı.")


if __name__ == "__main__":
    main()
