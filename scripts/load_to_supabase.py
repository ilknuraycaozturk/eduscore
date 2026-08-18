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
    # ÖNEMLİ: Sıralama önemli - daha spesifik olanlar (fen lisesi, imam hatip vb.)
    # genel "lise" kontrolünden ÖNCE gelmeli, yoksa hepsi genel 'lise'ye düşer.
    ("anaokulu", ["anaokulu", "anasınıfı", "kreş"]),
    ("ilkokul", ["ilkokul", "i̇lköğretim okulu"]),
    ("ortaokul", ["ortaokul", "imam hatip ortaokulu", "ımam hatip ortaokulu"]),
    ("fen-lisesi", ["fen lisesi"]),
    ("fen-teknoloji-lisesi", ["fen ve teknoloji lisesi", "fen-teknoloji lisesi"]),
    ("sosyal-bilimler-lisesi", ["sosyal bilimler lisesi"]),
    ("anadolu-guzel-sanatlar-lisesi", ["güzel sanatlar lisesi", "güzel sanatlar ve spor lisesi"]),
    ("spor-lisesi", ["spor lisesi"]),
    ("laboratuvar-lisesi", ["laboratuvar lisesi", "laboratuvar okulu"]),
    ("anadolu-imam-hatip-lisesi", [
        "imam hatip lisesi", "imam-hatip lisesi",
        "ımam hatip lisesi", "ımam-hatip lisesi",  # kaynak veride "İmam" bazen düz ASCII "I" ile yazılıyor
    ]),
    ("mesleki-teknik-anadolu-lisesi", [
        "mesleki ve teknik anadolu lisesi", "mesleki eğitim merkezi",
        "ticaret mesleki", "teknik anadolu lisesi", "meslek lisesi",
    ]),
    ("anadolu-lisesi", ["anadolu lisesi"]),
    ("lise", ["lisesi", " lise "]),  # yukarıdakilere uymayan ama yine de "lise" olan genel durum
    ("halk-egitim-merkezi", ["halk eğitim merkezi", "halk eğitimi merkezi"]),
    ("dershane-etut-merkezi", ["etüt eğitim merkezi", "etüt merkezi"]),
    ("ozel-egitim-okulu", ["özel eğitim uygulama okulu", "özel eğitim meslek okulu", "özel eğitim okulu"]),
]

# Bu isim kalıpları bir "kurum tipi" değil, idari/destek birimi olduğu için
# bilinçli olarak atlanıyor (okul değiller): İlçe Milli Eğitim Müdürlüğü,
# Rehberlik ve Araştırma Merkezi (RAM), Öğretmenevi vb.
ADMINISTRATIVE_UNIT_PATTERNS = [
    "milli eğitim müdürlüğü", "rehberlik ve araştırma merkezi",
    "öğretmenevi", "bilim ve sanat merkezi",
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


def turkish_lower(s: str) -> str:
    """Python'ın standart .lower()'ı Türkçe 'İ' harfini 'i' + görünmez nokta
    işaretine çevirir (i̇), düz 'i' harfine değil — bu da 'İlkokulu' ile
    'ilkokulu' gibi görünüşte aynı olan metinlerin string olarak FARKLI
    sayılmasına yol açar. Önce İ/I harflerini Türkçe kurallarına göre
    manuel çevirip sonra lowercase yaparak bunu önlüyoruz.
    """
    return s.replace("İ", "i").replace("I", "ı").lower()


def turkish_title(s: str) -> str:
    """Python'un standart .title() metodu Türkçe İ/I harflerini bozar
    (örn. 'AĞRI'.title() -> 'Ağri' olur, 'Ağrı' olması gerekirken). Bu
    fonksiyon ilk harfi olduğu gibi bırakır (kaynak zaten büyük harf ve
    İ/I ayrımı doğru), kalan harfleri Türkçe kurallarına göre küçültür."""
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


def turkish_capitalize_words(s: str) -> str:
    """Zaten TAMAMEN KÜÇÜK HARF olan bir metni Türkçe kurallarına göre
    başlık formatına çevirir (her kelimenin ilk harfi büyütülür).
    Python'un .title()'ı 'i' harfini yanlışlıkla 'I' yapar (İ olması
    gerekirken); bu fonksiyon bunu düzeltir."""
    def upper_first(c: str) -> str:
        if c == "i":
            return "İ"
        if c == "ı":
            return "I"
        return c.upper()

    words = s.strip().split(" ")
    return " ".join((upper_first(w[0]) + w[1:]) if w else w for w in words)


def normalize_name(name: str) -> str:
    """MEB isimlerindeki 'İL - İLÇE - ' önekini ve 'Özel' gibi kelimeleri
    temizleyerek karşılaştırılabilir bir isim üretir.
    Örn: 'ANKARA - ETİMESGUT - Bağlıca İlkokulu' -> 'bağlıca ilkokulu'
    """
    n = turkish_lower(name.strip())
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
    lower = turkish_lower(name)  # standart .lower() Türkçe 'İ'yi bozar, bkz. turkish_lower()
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


def fetch_all_paginated(base_url: str, headers: dict, path_with_query: str, page_size: int = 1000) -> list[dict]:
    """PostgREST varsayılan olarak isteği 1000 satırla sınırlıyor - tüm
    satırları almak için limit/offset ile sayfalama yapıyoruz."""
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
    dedup yapıyoruz. Aksi halde farklı konum granülerliğinde (mahalle vs
    ilçe) kaydedilmiş aynı okul mükerrer eklenebilir (bu bug'ı canlıda
    yaşadık ve LGS scriptinde düzelttik, aynı düzeltmeyi burada da uyguluyoruz)."""
    return fetch_all_paginated(base_url, headers, "/rest/v1/institutions?select=id,name,address,lat,lng,website")


def get_or_create_location(base_url: str, headers: dict, ilce_adi: str, parent_il_id: str,
                            location_cache: dict, dry_run: bool) -> str | None:
    # ÖNEMLİ (hata düzeltmesi): Önbellek anahtarına İL id'sini de dahil
    # ediyoruz - aksi halde "Merkez" gibi birden fazla ilde aynı isimde olan
    # ilçeler, çok-illi (il_kodu_listesi) taramalarda birbirine karışıyordu
    # (örn. Adıyaman'ın "Merkez" ilçesi yanlışlıkla Ankara'nın "Merkez"
    # ilçesiyle aynı kayıt sanılıyordu).
    key = f"{parent_il_id}:{turkish_title(ilce_adi.strip())}"
    if key in location_cache:
        return location_cache[key]

    district_name = turkish_title(ilce_adi.strip())
    resp = requests.get(
        f"{base_url}/rest/v1/locations?select=id,name&parent_id=eq.{parent_il_id}&name=eq.{district_name}",
        headers=headers,
    )
    resp.raise_for_status()
    rows = resp.json()
    if rows:
        location_cache[key] = rows[0]["id"]
        return rows[0]["id"]

    if dry_run:
        return None

    payload = {"parent_id": parent_il_id, "level": "district", "name": district_name}
    resp = requests.post(f"{base_url}/rest/v1/locations", headers={**headers, "Prefer": "return=representation"}, json=payload)
    resp.raise_for_status()
    new_id = resp.json()[0]["id"]
    location_cache[key] = new_id
    print(f"Yeni ilçe konumu oluşturuldu: {district_name} (il: {parent_il_id})")
    return new_id


def main():
    parser = argparse.ArgumentParser(description="MEB ham verisini Supabase'e yükler.")
    parser.add_argument("--input", required=True, help="scrape_meb_schools.py çıktısı JSON dosyası")
    parser.add_argument("--filter-mahalle", default=None, help="Sadece bu mahalleyi içeren adresler aktarılır")
    parser.add_argument("--location-name", default=None,
                         help="Belirtilirse TÜM kayıtlar bu tek konuma bağlanır (tek ilçe/pilot modu). "
                              "Belirtilmezse her kayıt kendi ilçesine (--all-ilceler çıktısındaki 'ilce_ad') göre otomatik konumlandırılır.")
    parser.add_argument("--category-slug", default="okul-oncesi-k12")
    parser.add_argument("--dry-run", action="store_true", help="Sadece ne ekleneceğini yazdır, Supabase'e yazma")
    parser.add_argument("--max-geocode", type=int, default=400,
                         help="ÖNEMLİ: GitHub Actions'ın 6 saatlik zaman aşımına takılmamak için, bu "
                              "çalıştırmada YENİ coğrafi kodlama (geocode) çağrısı sayısını sınırlar. "
                              "Zaten işlenmiş/eşleşen kayıtlar bu sınıra dahil değildir (hızlıca atlanır). "
                              "Sınıra ulaşılınca script durur - workflow'u tekrar çalıştırınca kaldığı "
                              "yerden devam eder (aynı kayıtlar tekrar coğrafi kodlanmaz).")
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

    headers = {
        "apikey": service_key,
        "Authorization": f"Bearer {service_key}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }

    type_lookup = {}
    location_lookup = {}
    category_lookup = {}
    fixed_location_id = None
    location_cache: dict[str, str] = {}
    ankara_id = None
    province_lookup: dict[str, str] = {}
    existing = []

    if not args.dry_run:
        type_lookup = get_lookup(supabase_url, headers, "institution_types")
        location_lookup = get_lookup(supabase_url, headers, "locations")
        category_lookup = get_lookup(supabase_url, headers, "categories")

        if args.location_name:
            fixed_location_id = location_lookup.get(args.location_name)
            if not fixed_location_id:
                print(f"HATA: '{args.location_name}' locations tablosunda bulunamadı.")
                sys.exit(1)
        else:
            # ÖNEMLİ (hata düzeltmesi): Önceden SADECE Ankara'nın id'si alınıp
            # TÜM illerin yeni ilçeleri yanlışlıkla Ankara'nın altına
            # ekleniyordu (çok-illi taramalarda ciddi bir veri karışıklığına
            # yol açıyordu). Şimdi TÜM illerin id'lerini önceden çekip, her
            # satır için kendi ilini kullanıyoruz.
            resp = requests.get(f"{supabase_url}/rest/v1/locations?select=id,name&level=eq.province", headers=headers)
            resp.raise_for_status()
            for row in resp.json():
                province_lookup[turkish_title(row["name"])] = row["id"]
            ankara_id = province_lookup.get("Ankara")
            if not ankara_id:
                print("HATA: 'Ankara' locations tablosunda bulunamadı.")
                sys.exit(1)

        # ÖNEMLİ: dedup kontrolünü coğrafi kodlamadan ÖNCE yapıyoruz - böylece
        # daha önceki bir çalıştırmada zaten işlenmiş kayıtlar için gereksiz
        # yere Nominatim'e istek atılmıyor (önceki sürümün 6 saatlik zaman
        # aşımına tekrar tekrar takılmasının asıl sebebi buydu).
        existing = get_existing_institutions(supabase_url, headers, None)
        print(f"Global dedup kontrolü için {len(existing)} mevcut kurum yüklendi.")

    skipped = 0
    skipped_admin = 0
    skipped_unknown_names = []
    inserted, enriched, skipped_dupe, geocode_calls = 0, 0, 0, 0
    stopped_early = False

    for r in raw:
        name_lower = turkish_lower(r["raw_name"])
        if any(pat in name_lower for pat in ADMINISTRATIVE_UNIT_PATTERNS):
            skipped_admin += 1
            continue

        type_slug = guess_type(r["raw_name"])
        if not type_slug:
            skipped += 1
            skipped_unknown_names.append(r["raw_name"])
            continue

        ilce_ad = r.get("ilce_ad") or args.location_name or ""
        raw_name = r["raw_name"].strip()
        address = r.get("raw_info")
        lat, lng = r.get("lat"), r.get("lng")
        website = r.get("website")

        # dry-run modunda gerçek dedup verisi olmadığı için her zaman ilk 5
        # kaydı önizleme amaçlı işleriz (Nominatim'e de gerçekten istek atarız,
        # ama sınırlı sayıda - performans için)
        match = find_existing_match(raw_name, existing) if existing else None

        if match and match.get("lat"):
            # ÖNEMLİ: Koordinatı zaten varsa BİR DAHA coğrafi kodlama yapma
            # (Nominatim'e boşuna istek atıp bütçeyi tüketmeyelim - önceden
            # adres/web sitesi de dolu olmasını şart koşuyorduk ama bu alanlar
            # bazı kayıtlarda kaynakta hiç yok, bu da aynı kayıtların her
            # çalıştırmada sonsuza dek tekrar denenmesine yol açıyordu).
            # Yine de web sitesi/adres gibi ÜCRETSİZ (API gerektirmeyen)
            # alanları, elimizde varsa güncelleyelim.
            needs_update = {}
            if not match.get("address") and address:
                needs_update["address"] = address
            if not match.get("website") and website:
                needs_update["website"] = website
            if needs_update and not args.dry_run:
                resp = requests.patch(
                    f"{supabase_url}/rest/v1/institutions?id=eq.{match['id']}",
                    headers=headers, json=needs_update,
                )
                if resp.status_code in (200, 204):
                    enriched += 1
                else:
                    print(f"UYARI: '{raw_name}' güncellenemedi -> {resp.status_code} {resp.text[:200]}")
            else:
                skipped_dupe += 1
            continue

        if geocode_calls >= args.max_geocode:
            stopped_early = True
            break

        if not lat or not lng:
            clean_name = turkish_capitalize_words(normalize_name(raw_name))
            geocode_query = f"{clean_name}, {ilce_ad}, Ankara, Türkiye"
            lat, lng = geocode(geocode_query)
            geocode_calls += 1
            is_approx_location = False
            if not lat:
                time.sleep(1)
                # Bina OSM'de haritalanmamış olabilir (küçük/yeni okullarda sık görülür).
                # Son çare: ilçe merkezini kullan, yaklaşık konum olarak işaretle.
                ilce_query = f"{ilce_ad}, Ankara, Türkiye"
                lat, lng = geocode(ilce_query)
                is_approx_location = bool(lat)
            time.sleep(1)  # Nominatim kullanım politikası: en fazla 1 istek/saniye
        else:
            is_approx_location = False

        description = DRAFT_NOTICE
        if is_approx_location:
            description += (
                " Not: Bu kurumun tam adresi bulunamadığı için harita konumu "
                f"'{ilce_ad}' ilçe merkezine yaklaşık olarak yerleştirilmiştir."
            )

        item = {
            "name": raw_name, "ilce": ilce_ad, "institution_type_slug": type_slug,
            "address": address, "website": website, "lat": lat, "lng": lng,
            "is_public": True, "is_verified": False, "description": description,
        }

        if args.dry_run:
            print(json.dumps(item, ensure_ascii=False))
            if geocode_calls >= 5:
                print("... (dry-run önizlemesi ilk birkaç kayıtla sınırlandı)")
                break
            continue

        if fixed_location_id:
            location_id = fixed_location_id
        else:
            # ÖNEMLİ: Her kaydın KENDİ ilini kullanıyoruz (scrape_meb_schools.py
            # 'il_ad' alanını satıra ekliyor). Bulunamazsa (eski formattaki
            # veriler için) Ankara'ya düşüyoruz - ama bu artık istisna, kural
            # değil.
            row_il_ad = r.get("il_ad")
            parent_il_id = province_lookup.get(turkish_title(row_il_ad)) if row_il_ad else None
            if not parent_il_id:
                parent_il_id = ankara_id
            location_id = get_or_create_location(supabase_url, headers, ilce_ad, parent_il_id, location_cache, args.dry_run)
            if not location_id:
                continue

        if match:
            needs_update = {}
            if not match.get("address") and address:
                needs_update["address"] = address
            if not match.get("lat") and lat:
                needs_update["lat"] = lat
            if not match.get("lng") and lng:
                needs_update["lng"] = lng
            if not match.get("website") and website:
                needs_update["website"] = website
            if needs_update:
                resp = requests.patch(
                    f"{supabase_url}/rest/v1/institutions?id=eq.{match['id']}",
                    headers=headers, json=needs_update,
                )
                if resp.status_code in (200, 204):
                    enriched += 1
                else:
                    print(f"UYARI: '{raw_name}' güncellenemedi -> {resp.status_code} {resp.text[:200]}")
            else:
                skipped_dupe += 1
            continue

        type_id = type_lookup.get(type_slug)
        if not type_id:
            continue
        # ÖNEMLİ (tutarlılık düzeltmesi): Diğer script'lerimiz (tabanpuanlari.net
        # vb.) kurum isimlerini "İL - İLÇE - İsim" formatında saklıyor - bu
        # script bugüne kadar sadece çıplak ismi kaydediyordu, bu da hem
        # görünüm tutarsızlığına hem de mükerrer kayıt tespitinin bazı
        # durumlarda kaçırılmasına yol açıyordu.
        display_name = f"{row_il_ad.upper()} - {ilce_ad.upper()} - {raw_name}" if row_il_ad else raw_name
        payload = {
            "name": display_name,
            "institution_type_id": type_id,
            "category_id": category_lookup.get(args.category_slug),
            "location_id": location_id,
            "is_public": True,
            "address": address,
            "website": website,
            "lat": lat,
            "lng": lng,
            "is_verified": False,
            "description": description,
        }
        resp = requests.post(f"{supabase_url}/rest/v1/institutions", headers={**headers, "Prefer": "return=representation"}, json=payload)
        if resp.status_code in (200, 201):
            inserted += 1
            new_row = resp.json()[0]
            existing.append({"id": new_row["id"], "name": raw_name, "address": address, "lat": lat, "lng": lng, "website": website})
        else:
            print(f"UYARI: '{raw_name}' eklenemedi -> {resp.status_code} {resp.text[:200]}")

    print(f"{skipped} kayıt tipi tanınamadığı için atlandı, {skipped_admin} idari birim olduğu için atlandı.")
    if skipped_unknown_names:
        print(f"--- Tipi tanınamayan {len(skipped_unknown_names)} kayıt ---")
        for n in skipped_unknown_names:
            print(f"  ? {n}")

    if args.dry_run:
        print("... (dry-run, Supabase'e yazılmadı)")
        return

    print(f"Tamamlandı: {inserted} yeni kurum eklendi, {enriched} mevcut kurum zenginleştirildi, {skipped_dupe} zaten var olduğu için atlandı, {geocode_calls} yeni coğrafi kodlama yapıldı.")
    if stopped_early:
        print(f"\n⚠️ PARTİ SINIRINA ULAŞILDI ({args.max_geocode} yeni coğrafi kodlama). "
              f"İşlenmemiş kayıtlar kaldı - workflow'u TEKRAR ÇALIŞTIRIN, kaldığı yerden devam edecek "
              f"(zaten eklenen kayıtlar tekrar işlenmeyecek, hızlıca atlanacak).")


if __name__ == "__main__":
    main()
