"""
load_ookgm_to_supabase.py
==========================
EduScor — scrape_ookgm.py çıktısını temizleyip Supabase 'institutions'
tablosuna yazar. load_to_supabase.py'dan farkı: ÖOKGM verisinde zaten
gerçek adres olduğu için geocoding'e gerek yok (adres metni saklanır,
koordinat isteğe bağlı olarak ayrı bir adımda eklenebilir).

Kullanım:
    export SUPABASE_URL="..."
    export SUPABASE_SERVICE_ROLE_KEY="..."
    python load_ookgm_to_supabase.py --input data/ookgm_raw.json --location-name "Bağlıca" --dry-run
"""

import argparse
import json
import os
import sys
from pathlib import Path

import requests

DRAFT_NOTICE = (
    "Bu sayfadaki bilgiler ÖOKGM'nin (Özel Öğretim Kurumları Genel Müdürlüğü) "
    "kamuya açık kaynaklarından otomatik olarak derlenmiştir. Doğruluğunu kontrol ediniz."
)

# ÖOKGM'nin ham "Kurum Türü" metnini bizim institution_types.slug değerine eşleştirir
TUR_MAP = {
    "özel çeşitli kurslar": "kisisel-gelisim-kursu",
    "özel hizmetiçi eğitim merkezi": "hizmetici-egitim-merkezi",
    "i̇şbirliği protokolü kapsamında açılan kurslar": "belediye-destek-kursu",
    "işbirliği protokolü kapsamında açılan kurslar": "belediye-destek-kursu",
    "özel uzaktan eğitim kursu": "uzaktan-egitim-kursu",
    "özel motorlu taşıt sürücü kursları": "surucu-kursu",
    "iş makineleri sürücü eğitim kursları": "is-makinesi-operatorlugu-kursu",
    "özel ulaştırma hizmetleri mesleki eğitim ve geliştirme kursları": "ulastirma-hizmetleri-kursu",
    "pilot yetiştirme kursları": "pilot-yetistirme-kursu",
    "sosyal etkinlik ve gelişim merkezi": "sosyal-etkinlik-merkezi",
    "sosyal etkinlik merkezi": "sosyal-etkinlik-merkezi",
    "özel eğitim ve rehabilitasyon merkezleri": "ozel-egitim-rehabilitasyon",
    "özel mesleki eğitim merkezleri": "is-makinesi-operatorlugu-kursu",  # en yakın eşleşme
    "özel öğretim kursları": "kisisel-gelisim-kursu",
    "öğrenci etkinlik merkezi": "sosyal-etkinlik-merkezi",
}


def turkish_lower(s: str) -> str:
    """Standart .lower() Türkçe 'İ' harfini bozduğu için (İ -> i̇, görünmez
    nokta işaretiyle) önce İ/I harflerini Türkçe kurallarına göre çeviriyoruz."""
    return s.replace("İ", "i").replace("I", "ı").lower()


def map_tur(ham_tur: str) -> str | None:
    return TUR_MAP.get(turkish_lower(ham_tur.strip()))


def normalize_name(name: str) -> str:
    n = turkish_lower(name.strip())
    n = n.replace("özel", "").strip()
    return " ".join(n.split())


def find_existing_match(new_name: str, existing: list[dict]) -> dict | None:
    target = normalize_name(new_name)
    for row in existing:
        existing_norm = normalize_name(row["name"])
        if target == existing_norm or target in existing_norm or existing_norm in target:
            return row
    return None


def get_lookup(base_url: str, headers: dict, table: str) -> dict[str, str]:
    """institution_types, categories: anahtar 'slug' (bu tablolarda 'name' yok, 'name_tr' var).
    locations: anahtar 'name'."""
    if table in ("institution_types", "categories"):
        resp = requests.get(f"{base_url}/rest/v1/{table}?select=id,slug", headers=headers)
        resp.raise_for_status()
        return {r["slug"]: r["id"] for r in resp.json()}

    resp = requests.get(f"{base_url}/rest/v1/{table}?select=id,name", headers=headers)
    resp.raise_for_status()
    return {r["name"]: r["id"] for r in resp.json()}


def get_existing_institutions(base_url: str, headers: dict, location_id: str) -> list[dict]:
    """ÖNEMLİ: location_id ile SINIRLAMIYORUZ - tüm kurumlar arasında global
    dedup yapıyoruz (farklı konum granülerliğinde kaydedilmiş aynı okulun
    mükerrer eklenmesini önlemek için - bkz. diğer yükleme scriptlerindeki
    aynı düzeltme)."""
    resp = requests.get(
        f"{base_url}/rest/v1/institutions?select=id,name,address",
        headers=headers,
    )
    resp.raise_for_status()
    return resp.json()


def main():
    parser = argparse.ArgumentParser(description="ÖOKGM verisini Supabase'e yükler.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--location-name", required=True)
    parser.add_argument("--category-slug", default=None, help="Belirtilmezse her kayıt kendi tipinin ait olduğu kategoriye eklenir")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    supabase_url = os.environ.get("SUPABASE_URL")
    service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not args.dry_run and (not supabase_url or not service_key):
        print("HATA: SUPABASE_URL ve SUPABASE_SERVICE_ROLE_KEY gerekli.")
        sys.exit(1)

    raw = json.loads(Path(args.input).read_text(encoding="utf-8"))
    print(f"{len(raw)} ham kayıt okundu.")

    prepared, skipped = [], 0
    for r in raw:
        type_slug = map_tur(r["kurum_turu_ham"])
        if not type_slug:
            skipped += 1
            print(f"ATLANDI (tanınamayan tür): '{r['raw_name']}' -> '{r['kurum_turu_ham']}'")
            continue
        prepared.append({
            "name": r["raw_name"].strip(),
            "institution_type_slug": type_slug,
            "address": r.get("address") or None,
            "phone": r.get("phone") or None,
            "is_public": type_slug == "belediye-destek-kursu",  # belediye kursu haricinde hepsi özel
            "is_verified": False,
            "description": DRAFT_NOTICE + (f" Programlar: {r['programs_raw'][:300]}" if r.get("programs_raw") else ""),
        })

    print(f"{len(prepared)} kayıt tipi tanınarak hazırlandı, {skipped} kayıt atlandı.")

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
    type_category_lookup = {}  # slug -> category_id (institution_types tablosundan)

    resp = requests.get(f"{supabase_url}/rest/v1/institution_types?select=slug,category_id", headers=headers)
    resp.raise_for_status()
    for row in resp.json():
        type_category_lookup[row["slug"]] = row["category_id"]

    location_id = location_lookup.get(args.location_name)
    if not location_id:
        print(f"HATA: '{args.location_name}' locations tablosunda bulunamadı.")
        sys.exit(1)

    existing = get_existing_institutions(supabase_url, headers, location_id)
    print(f"Bu konumda {len(existing)} mevcut kurum bulundu.")

    inserted, enriched, skipped_dupe = 0, 0, 0
    for item in prepared:
        match = find_existing_match(item["name"], existing)
        if match:
            if not match.get("address") and item["address"]:
                requests.patch(
                    f"{supabase_url}/rest/v1/institutions?id=eq.{match['id']}",
                    headers=headers, json={"address": item["address"]},
                )
                enriched += 1
            else:
                skipped_dupe += 1
            continue

        type_id = type_lookup.get(item["institution_type_slug"])
        if not type_id:
            continue
        payload = {
            "name": item["name"],
            "institution_type_id": type_id,
            "category_id": args.category_slug and category_lookup.get(args.category_slug) or type_category_lookup.get(item["institution_type_slug"]),
            "location_id": location_id,
            "is_public": item["is_public"],
            "address": item["address"],
            "is_verified": item["is_verified"],
            "description": item["description"],
        }
        resp = requests.post(f"{supabase_url}/rest/v1/institutions", headers=headers, json=payload)
        if resp.status_code in (200, 201):
            inserted += 1
        else:
            print(f"UYARI: '{item['name']}' eklenemedi -> {resp.status_code} {resp.text[:200]}")

    print(f"Tamamlandı: {inserted} yeni, {enriched} zenginleştirildi, {skipped_dupe} zaten vardı.")


if __name__ == "__main__":
    main()
