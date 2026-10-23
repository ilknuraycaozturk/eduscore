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
    # --- Okul türleri (tur=okul için) ---
    "özel türk okul öncesi kurumu": "anaokulu",
    "özel türk i̇lkokulu": "ilkokul",
    "özel türk ilkokulu": "ilkokul",
    "özel türk ortaokulu": "ortaokul",
    "özel hazırlık sınıfı bulunan anadolu lisesi": "anadolu-lisesi",
    "özel anadolu lisesi": "anadolu-lisesi",
    "özel fen lisesi": "fen-lisesi",
    "özel sosyal bilimler lisesi": "sosyal-bilimler-lisesi",
    "özel anadolu i̇mam hatip lisesi": "anadolu-imam-hatip-lisesi",
    "özel anadolu imam hatip lisesi": "anadolu-imam-hatip-lisesi",
    "özel mesleki ve teknik anadolu lisesi": "mesleki-teknik-anadolu-lisesi",
    "özel anadolu güzel sanatlar lisesi": "anadolu-guzel-sanatlar-lisesi",
    "özel akşam lisesi": "aksam-lisesi",
    "özel özel eğitim anaokulu": "ozel-egitim-okulu",
    "özel özel eğitim i̇lkokulu": "ozel-egitim-okulu",
    "özel özel eğitim ortaokulu": "ozel-egitim-okulu",
    "özel özel eğitim mesleki eğitim merkezi": "ozel-egitim-okulu",
}


def turkish_lower(s: str) -> str:
    """Standart .lower() Türkçe 'İ' harfini bozduğu için (İ -> i̇, görünmez
    nokta işaretiyle) önce İ/I harflerini Türkçe kurallarına göre çeviriyoruz."""
    return s.replace("İ", "i").replace("I", "ı").lower()


def turkish_title(s: str) -> str:
    """Python'un standart .title() metodu Türkçe İ/I harflerini bozar.
    İlk harfi olduğu gibi bırakır, kalanını Türkçe kurallarına göre küçültür."""
    def lower_char(c: str) -> str:
        if c == "I":
            return "ı"
        if c == "İ":
            return "i"
        return c.lower()

    words = s.strip().split(" ")
    result = []
    for w in words:
        if not w:
            continue
        result.append(w[0] + "".join(lower_char(c) for c in w[1:]))
    return " ".join(result)


FALLBACK_KEYWORD_RULES = [
    # Bunlar TUR_MAP'te tam eşleşmeyen ama içinde geçen anahtar kelimeye göre
    # sınıflandırılan türler (örn. '(III.Kademe)' gibi değişken sonekler içerdiği için).
    ("milletlerarası", "milletlerarasi-okul"),
    ("fen ve teknoloji lisesi", "fen-teknoloji-lisesi"),
    ("laboratuvar lisesi", "laboratuvar-lisesi"),
    ("yurt dışı eğitim danışmanlığı", "egitim-danismanligi"),
    ("hafif düzeyde zihinsel engelliler", "ozel-egitim-okulu"),
    ("özel eğitim uygulama okulu", "ozel-egitim-okulu"),
    ("özel eğitim meslek okulu", "ozel-egitim-okulu"),
    ("özel eğitim iş uygulama merkezi", "ozel-egitim-okulu"),
    ("çocuk etkinlik ve oyun evi", "sosyal-etkinlik-merkezi"),
]


def map_tur(ham_tur: str) -> str | None:
    lower = turkish_lower(ham_tur.strip())
    exact = TUR_MAP.get(lower)
    if exact:
        return exact
    for keyword, slug in FALLBACK_KEYWORD_RULES:
        if keyword in lower:
            return slug
    return None


from eduscor_data_utils import normalize_name, normalize_turkish  # EDU-DATA-001
# Aynı il/ilçe içinde, adı birebir aynı kaydı eşleştiren ortak kurallar (MEB
# yükleyicisiyle aynı; Ekim 2026'da il-bağımsız alt dize eşleştirmesinin yol
# açtığı kopya ve yanlış zenginleştirme hataları nedeniyle).
from load_to_supabase import build_place_index, find_same_place_match, get_existing_institutions as _get_existing_full


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


def fetch_all_paginated(base_url: str, headers: dict, path_with_query: str, page_size: int = 1000) -> list[dict]:
    """PostgREST varsayılan olarak isteği 1000 satırla sınırlıyor - bu yüzden
    tüm satırları almak için limit/offset ile sayfalama yapıyoruz. Bu olmadan
    1000'den fazla kurum olduğunda dedup kontrolü eksik kalır ve mükerrer
    kayıt oluşabilir (bunu canlı ortamda fark ettik)."""
    all_rows: list[dict] = []
    offset = 0
    sep = "&" if "?" in path_with_query else "?"
    while True:
        resp = requests.get(
            f"{base_url}{path_with_query}{sep}limit={page_size}&offset={offset}",
            headers=headers,
        )
        resp.raise_for_status()
        page = resp.json()
        all_rows.extend(page)
        if len(page) < page_size:
            break
        offset += page_size
    return all_rows


def get_existing_institutions(base_url: str, headers: dict, location_id: str) -> list[dict]:
    """ÖNEMLİ: location_id ile SINIRLAMIYORUZ - tüm kurumlar arasında global
    dedup yapıyoruz (farklı konum granülerliğinde kaydedilmiş aynı okulun
    mükerrer eklenmesini önlemek için - bkz. diğer yükleme scriptlerindeki
    aynı düzeltme)."""
    return fetch_all_paginated(base_url, headers, "/rest/v1/institutions?select=id,name,address,phone")


def get_or_create_location(base_url: str, headers: dict, ilce_adi: str, ankara_id: str,
                            location_cache: dict, dry_run: bool) -> str | None:
    """ankara_id adı tarihsel; artık kaydın KENDİ ilinin id'si geçilir
    (önceden tüm ilçeler Ankara'nın altına açılıyordu)."""
    key = turkish_title(ilce_adi.strip())
    cache_key = f"{ankara_id}:{key}"
    if cache_key in location_cache:
        return location_cache[cache_key]

    resp = requests.get(
        f"{base_url}/rest/v1/locations?select=id,name&parent_id=eq.{ankara_id}&name=eq.{key}",
        headers=headers,
    )
    resp.raise_for_status()
    rows = resp.json()
    if rows:
        location_cache[cache_key] = rows[0]["id"]
        return rows[0]["id"]

    if dry_run:
        return None

    payload = {"parent_id": ankara_id, "level": "district", "name": key}
    resp = requests.post(f"{base_url}/rest/v1/locations", headers={**headers, "Prefer": "return=representation"}, json=payload)
    resp.raise_for_status()
    new_id = resp.json()[0]["id"]
    location_cache[cache_key] = new_id
    print(f"Yeni ilçe konumu oluşturuldu: {key}")
    return new_id


def main():
    parser = argparse.ArgumentParser(description="ÖOKGM verisini Supabase'e yükler.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--location-name", default=None,
                         help="Belirtilirse TÜM kayıtlar bu tek konuma bağlanır (pilot bölge testleri için). "
                              "Belirtilmezse her kayıt kendi ilçesine (r['ilce']) göre otomatik konumlandırılır (tüm il için).")
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
            "il": (r.get("il") or "").strip(),
            "name": r["raw_name"].strip(),
            "ilce": r.get("ilce", "").strip(),
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

    # Sabit tek konum (pilot mod) mu, yoksa ilçe bazlı otomatik mod mu?
    fixed_location_id = None
    location_cache: dict[str, str] = {}
    ankara_id = None

    if args.location_name:
        fixed_location_id = location_lookup.get(args.location_name)
        if not fixed_location_id:
            print(f"HATA: '{args.location_name}' locations tablosunda bulunamadı.")
            sys.exit(1)
    resp = requests.get(f"{supabase_url}/rest/v1/locations?select=id,name&level=eq.province", headers=headers)
    resp.raise_for_status()
    il_id = {normalize_turkish(r["name"]): r["id"] for r in resp.json()}

    existing = _get_existing_full(supabase_url, headers, None)
    all_locations = fetch_all_paginated(supabase_url, headers, "/rest/v1/locations?select=id,parent_id,level,name")
    place_index = build_place_index(existing, all_locations)
    print(f"Dedup için {len(existing)} mevcut kurum yüklendi (aynı il/ilçe içinde eşleştirme).")

    inserted, enriched, skipped_dupe, failed, il_yok = 0, 0, 0, 0, 0
    for item in prepared:
        il_parent = il_id.get(normalize_turkish(item["il"])) if item["il"] else None
        if fixed_location_id:
            location_id = fixed_location_id
        else:
            if not il_parent:
                il_yok += 1
                print(f"ATLANDI (il bulunamadı): '{item['name']}' il='{item['il']}'")
                continue
            location_id = get_or_create_location(supabase_url, headers, item["ilce"], il_parent, location_cache, args.dry_run)
            if not location_id:
                continue

        match = find_same_place_match(item["name"], item["il"] or None, item["ilce"] or None, place_index)
        if match:
            needs_update = {}
            if not match.get("address") and item["address"]:
                needs_update["address"] = item["address"]
            if not match.get("phone") and item.get("phone"):
                needs_update["phone"] = item["phone"]
            if needs_update:
                pr = requests.patch(
                    f"{supabase_url}/rest/v1/institutions?id=eq.{match['id']}",
                    headers=headers, json=needs_update,
                )
                if pr.status_code in (200, 204):
                    enriched += 1
                else:
                    failed += 1
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
            "phone": item.get("phone"),
            "is_verified": item["is_verified"],
            "description": item["description"],
        }
        resp = requests.post(f"{supabase_url}/rest/v1/institutions", headers={**headers, "Prefer": "return=representation"}, json=payload)
        if resp.status_code in (200, 201):
            inserted += 1
            new_row = resp.json()[0]
            entry = {"id": new_row["id"], "name": item["name"], "address": item["address"]}
            existing.append(entry)
            place_index.setdefault(normalize_name(item["name"]), []).append(
                {"row": entry, "il": normalize_turkish(item["il"]) if item["il"] else None,
                 "ilce": normalize_turkish(item["ilce"]) if item["ilce"] else None})
        else:
            failed += 1
            print(f"UYARI: '{item['name']}' eklenemedi -> {resp.status_code} {resp.text[:200]}")

    summary = {"ham_kayit": len(raw), "tipi_taninmadi": skipped, "il_bulunamadi": il_yok,
               "eklendi": inserted, "zenginlestirildi": enriched, "zaten_vardi": skipped_dupe, "hata": failed}
    cov_path = Path("data/ookgm_coverage.json")
    sorunlu = []
    if cov_path.exists():
        cov = json.loads(cov_path.read_text(encoding="utf-8"))
        sorunlu = [c for c in cov if c.get("beklenen") is None or c.get("beklenen") != c.get("cekilen")]
        summary.update({"iller": len(cov), "ookgm_beklenen": sum(c["beklenen"] or 0 for c in cov),
                        "ookgm_cekilen": sum(c["cekilen"] for c in cov), "sorunlu_iller": sorunlu[:40]})
    print("OOKGM_OZETI " + json.dumps(summary, ensure_ascii=False))
    try:
        requests.post(f"{supabase_url}/rest/v1/scrape_progress?on_conflict=key",
                      headers={**headers, "Prefer": "resolution=merge-duplicates,return=minimal"},
                      json={"key": "ookgm_son_yukleme_ozeti", "value": json.dumps(summary, ensure_ascii=False)[:5000]},
                      timeout=15).raise_for_status()
    except Exception as e:
        print(f"UYARI: özet yazılamadı: {e}")
    print(f"Tamamlandı: {inserted} yeni, {enriched} zenginleştirildi, {skipped_dupe} zaten vardı.")
    if failed or sorunlu or il_yok:
        print("HATA: yazma hatası, il eşleşmesi ya da ÖOKGM toplamıyla uyuşmazlık var (bkz. özet).")
        sys.exit(1)


if __name__ == "__main__":
    main()
