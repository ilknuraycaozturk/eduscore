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


def guess_type(name: str) -> str | None:
    lower = name.lower()
    for slug, keywords in TYPE_KEYWORDS:
        if any(k in lower for k in keywords):
            return slug
    return None


def load_raw(path: str) -> list[dict]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def get_lookup(base_url: str, headers: dict, table: str) -> dict[str, str]:
    """slug/name -> id sözlüğü döndürür (institution_types ve locations için)."""
    resp = requests.get(f"{base_url}/rest/v1/{table}?select=id,slug,name" if table == "institution_types"
                         else f"{base_url}/rest/v1/{table}?select=id,name", headers=headers)
    resp.raise_for_status()
    rows = resp.json()
    if table == "institution_types":
        return {r["slug"]: r["id"] for r in rows}
    return {r["name"]: r["id"] for r in rows}


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
        prepared.append({
            "name": r["raw_name"].strip(),
            "institution_type_slug": type_slug,
            "address": r.get("raw_info"),
            "lat": r.get("lat"),
            "lng": r.get("lng"),
            "is_public": True,  # bu uç nokta resmi MEB okulları için; özel kurumlar ayrı script (ookgm) ile işlenir
            "is_verified": False,
            "description": DRAFT_NOTICE,
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

    inserted = 0
    for item in prepared:
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

    print(f"Tamamlandı: {inserted}/{len(prepared)} kurum Supabase'e eklendi.")


if __name__ == "__main__":
    main()
