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

# EDU-DATA-001: normalize_name ve find_existing_match artik merkezi bir
# modulden geliyor - kod tekrarini onlemek icin. Ayni klasordeki
# eduscor_data_utils.py'yi bulabilmesi icin scripts/ klasorunun PATH'te
# olmasi gerekir (GitHub Actions workflow'larinda calisma dizini zaten
# bu klasor oldugu icin ek bir islem gerekmez).
from eduscor_data_utils import normalize_name as _shared_normalize_name, find_existing_match as _shared_find_existing_match

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
    """DEĞİŞTİ (19.09.2026): Bu, artık eduscor_data_utils.normalize_name'in
    bir alias'ı - kod tekrarını önlemek için. Davranış: eskiden sadece
    turkish_lower() (İ/I) kullanıyordu, şimdi normalize_turkish() (TÜM
    Türkçe karakterler: Ç/Ğ/Ö/Ş/Ü de dahil) kullanıyor. Bu, KARŞILAŞTIRMA
    tutarlılığını korur (yeni ve eski kayıtlar aynı fonksiyonla normalize
    edildiği sürece güvenlidir) ve DAHA GENİŞ bir yazım varyasyonu yakalar.
    Bkz. EDU-DATA-001."""
    return _shared_normalize_name(name)


find_existing_match = _shared_find_existing_match


# --- Aynı yerde eşleştirme (Ekim 2026) -----------------------------------
# find_existing_match() tüm Türkiye'de isim ALT DİZESİ ile eşleştiriyordu:
# Tunceli'deki "Atatürk İlkokulu", Ankara'daki "Atatürk İlkokulu" ile aynı
# sayılıp hiç eklenmiyor, üstelik bilgileri (kurum kodu, web) yanlış okula
# yazılıyordu. Bu yükleyici artık yalnızca AYNI İL (ve biliniyorsa AYNI
# İLÇE) içinde, normalize edilmiş adı BİREBİR aynı olan kaydı eşleştirir.
from eduscor_data_utils import normalize_turkish as _norm_tr


def _place_from_prefix(name: str) -> tuple[str | None, str | None]:
    parts = [p.strip() for p in (name or "").split(" - ")]
    if len(parts) >= 3:
        return _norm_tr(parts[0]), _norm_tr(parts[1])
    return None, None


def build_place_index(existing: list[dict], locations: list[dict]) -> dict[str, list[dict]]:
    """Mevcut kurumları normalize ad -> [{row, il, ilce}] olarak indeksler.
    İl/ilçe önce 'İL - İLÇE - Ad' önekinden, yoksa location_id'den bulunur."""
    by_id = {l["id"]: l for l in locations}

    def place_of_location(loc_id):
        loc = by_id.get(loc_id)
        il = ilce = None
        while loc:
            if loc.get("level") == "district" and ilce is None:
                ilce = _norm_tr(loc["name"])
            if loc.get("level") == "province":
                il = _norm_tr(loc["name"])
                break
            loc = by_id.get(loc.get("parent_id"))
        return il, ilce

    iller = {_norm_tr(l["name"]) for l in locations if l.get("level") == "province"}
    index: dict[str, list[dict]] = {}
    for row in existing:
        key = normalize_name(row["name"])
        il, ilce = _place_from_prefix(row["name"])
        if il is None:
            # "İL - Ad" (2 parçalı) biçimi: önceki lise yüklemeleri böyle kaydetmişti;
            # il önekini ayırmazsak "İL - İLÇE - Ad" biçimli MEB kaydıyla eşleşmiyor
            # ve kopya oluşuyordu (19.10.2026'da 4.733 kopya birleştirildi).
            parts = [p.strip() for p in row["name"].split(" - ")]
            if len(parts) == 2 and _norm_tr(parts[0]) in iller:
                key, il = normalize_name(parts[1]), _norm_tr(parts[0])
        if il is None:
            il, ilce = place_of_location(row.get("location_id"))
        index.setdefault(key, []).append({"row": row, "il": il, "ilce": ilce})
    return index


def find_same_place_match(raw_name: str, il_ad: str | None, ilce_ad: str | None,
                          index: dict[str, list[dict]]) -> dict | None:
    adaylar = index.get(normalize_name(raw_name), [])
    il, ilce = (_norm_tr(il_ad) if il_ad else None), (_norm_tr(ilce_ad) if ilce_ad else None)
    if il is None:
        return None  # ili bilinmeyen kayıt için eşleştirme yapma (yanlış birleştirme riski)
    ayni_il = [a for a in adaylar if a["il"] == il]
    if ilce:
        ayni_ilce = [a for a in ayni_il if a["ilce"] == ilce]
        if len(ayni_ilce) == 1:
            return ayni_ilce[0]["row"]
        if len(ayni_ilce) > 1:
            return ayni_ilce[0]["row"]  # aynı ilçede aynı adla mükerrer kayıt zaten var
        ilcesiz = [a for a in ayni_il if a["ilce"] is None]
        return ilcesiz[0]["row"] if len(ilcesiz) == 1 else None
    return ayni_il[0]["row"] if len(ayni_il) == 1 else None


def guess_type(name: str) -> str | None:
    lower = turkish_lower(name)  # standart .lower() Türkçe 'İ'yi bozar, bkz. turkish_lower()
    # ÖNEMLİ: Kaynak verilerde (tabanpuanlari.net, MEB vb.) Türkçe "İ" harfi
    # bazen düz ASCII "I" ile yazılıyor (örn. "Imam Hatip" yerine "İmam Hatip"
    # olması gerekirken). turkish_lower() bunu kurallara göre "ı"ya çeviriyor,
    # ama asıl niyet "i" idi. Bu yüzden eşleştirmeyi ı/i farkına karşı
    # BAĞIŞIK yapıyoruz - her kalıba tek tek ASCII varyasyonu eklemek yerine,
    # hem metni hem kalıpları "ı"->"i" normalize edip karşılaştırıyoruz.
    lower_normalized = lower.replace("ı", "i")
    for slug, keywords in TYPE_KEYWORDS:
        if any(k.replace("ı", "i") in lower_normalized for k in keywords):
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
    return fetch_all_paginated(base_url, headers, "/rest/v1/institutions?select=id,name,address,lat,lng,website,meb_kurum_kodu,email,location_id")


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
    # Aynı ilin ilçeleri yazım farkı gözetmeden karşılaştırılır (ilce_anahtari).
    from eduscor_data_utils import ilce_anahtari
    resp = requests.get(
        f"{base_url}/rest/v1/locations?select=id,name&parent_id=eq.{parent_il_id}&level=eq.district",
        headers=headers,
    )
    resp.raise_for_status()
    rows = [r for r in resp.json() if ilce_anahtari(r["name"]) == ilce_anahtari(ilce_adi)]
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
    parser.add_argument("--max-geocode", type=int, default=0,
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
    place_index: dict[str, list[dict]] = {}

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
        all_locations = fetch_all_paginated(supabase_url, headers, "/rest/v1/locations?select=id,parent_id,level,name")
        place_index = build_place_index(existing, all_locations)
        print(f"Dedup kontrolü için {len(existing)} mevcut kurum yüklendi (aynı il/ilçe içinde eşleştirme).")

    skipped = 0
    skipped_admin = 0
    skipped_unknown_names = []
    inserted, enriched, skipped_dupe, geocode_calls = 0, 0, 0, 0
    failed, no_geocode = 0, 0
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
        # Coğrafi kodlamada kaydın KENDİ ili kullanılır (önceden her kayıt
        # "Ankara" ile sorgulanıyordu; Ankara dışı okullar Ankara'ya düşüyordu).
        geo_il = turkish_title(r["il_ad"]) if r.get("il_ad") else "Ankara"
        raw_name = r["raw_name"].strip()
        address = r.get("raw_info")
        lat, lng = r.get("lat"), r.get("lng")
        website = r.get("website")
        meb_kurum_kodu = r.get("meb_kurum_kodu")

        # dry-run modunda gerçek dedup verisi olmadığı için her zaman ilk 5
        # kaydı önizleme amaçlı işleriz (Nominatim'e de gerçekten istek atarız,
        # ama sınırlı sayıda - performans için)
        pref_il, pref_ilce = _place_from_prefix(r["raw_name"])
        row_place_il = r.get("il_ad") or pref_il
        row_place_ilce = ilce_ad or pref_ilce
        match = find_same_place_match(raw_name, row_place_il, row_place_ilce, place_index) if place_index else None

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
            effective_kod = meb_kurum_kodu or match.get("meb_kurum_kodu")
            if not match.get("meb_kurum_kodu") and meb_kurum_kodu:
                needs_update["meb_kurum_kodu"] = meb_kurum_kodu
            if not match.get("email") and effective_kod:
                needs_update["email"] = f"{effective_kod}@meb.k12.tr"
            if needs_update and not args.dry_run:
                resp = requests.patch(
                    f"{supabase_url}/rest/v1/institutions?id=eq.{match['id']}",
                    headers=headers, json=needs_update,
                )
                if resp.status_code in (200, 204):
                    enriched += 1
                else:
                    failed += 1
                    print(f"UYARI: '{raw_name}' güncellenemedi -> {resp.status_code} {resp.text[:200]}")
            else:
                skipped_dupe += 1
            continue

        # Coğrafi kodlama bütçesi dolduysa kaydı yine EKLE (koordinatsız);
        # önceden burada döngü kırılıyordu ve kalan okullar hiç eklenmiyordu.
        geocode_budget_left = geocode_calls < args.max_geocode
        if not geocode_budget_left:
            stopped_early = True

        geocoded_now = False
        if (not lat or not lng) and not geocode_budget_left:
            lat, lng = None, None
            is_approx_location = False
            no_geocode += 1
        elif not lat or not lng:
            geocoded_now = True
            clean_name = turkish_capitalize_words(normalize_name(raw_name))
            geocode_query = f"{clean_name}, {ilce_ad}, {geo_il}, Türkiye"
            lat, lng = geocode(geocode_query)
            geocode_calls += 1
            is_approx_location = False
            # 30.10.2026: İlçe merkezine "yaklaşık konum" yazan son çare KALDIRILDI.
            # Bu yol 3.300'den fazla okulu il/ilçe merkezindeki aynı noktaya
            # yığmıştı (ör. Antalya merkezinde 160 okul). Koordinat artık yalnızca
            # doğrulamalı ayrı işlerle yazılıyor (meb_site_coords, OSM, LocationIQ);
            # bu yükleyicide coğrafi kodlama varsayılan olarak kapalı (--max-geocode 0).
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
            "meb_kurum_kodu": meb_kurum_kodu,
            "email": f"{meb_kurum_kodu}@meb.k12.tr" if meb_kurum_kodu else None,
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
            effective_kod2 = meb_kurum_kodu or match.get("meb_kurum_kodu")
            if not match.get("meb_kurum_kodu") and meb_kurum_kodu:
                needs_update["meb_kurum_kodu"] = meb_kurum_kodu
            if not match.get("email") and effective_kod2:
                needs_update["email"] = f"{effective_kod2}@meb.k12.tr"
            if needs_update:
                resp = requests.patch(
                    f"{supabase_url}/rest/v1/institutions?id=eq.{match['id']}",
                    headers=headers, json=needs_update,
                )
                if resp.status_code in (200, 204):
                    enriched += 1
                else:
                    failed += 1
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
            "meb_kurum_kodu": meb_kurum_kodu,
            "email": f"{meb_kurum_kodu}@meb.k12.tr" if meb_kurum_kodu else None,
            "lat": lat,
            "lng": lng,
            # eduscor-trust-uncertainty: koordinatın kaynağı ve güveni puanlamaya aktarılır
            "konum_kaynagi": ("nominatim" if geocoded_now else "eski_bilinmiyor") if lat else None,
            "konum_guven": (("dusuk" if is_approx_location else "orta") if geocoded_now else "dusuk") if lat else None,
            "is_verified": False,
            "description": description,
        }
        resp = requests.post(f"{supabase_url}/rest/v1/institutions", headers={**headers, "Prefer": "return=representation"}, json=payload)
        if resp.status_code in (200, 201):
            inserted += 1
            new_row = resp.json()[0]
            new_entry = {"id": new_row["id"], "name": raw_name, "address": address, "lat": lat, "lng": lng, "website": website}
            existing.append(new_entry)
            place_index.setdefault(normalize_name(raw_name), []).append({
                "row": new_entry,
                "il": _norm_tr(row_place_il) if row_place_il else None,
                "ilce": _norm_tr(row_place_ilce) if row_place_ilce else None,
            })
        else:
            failed += 1
            print(f"UYARI: '{raw_name}' eklenemedi -> {resp.status_code} {resp.text[:200]}")

    print(f"{skipped} kayıt tipi tanınamadığı için atlandı, {skipped_admin} idari birim olduğu için atlandı.")
    if skipped_unknown_names:
        print(f"--- Tipi tanınamayan {len(skipped_unknown_names)} kayıt ---")
        for n in skipped_unknown_names:
            print(f"  ? {n}")

    summary = {
        "ham_kayit": len(raw), "idari_birim_atlandi": skipped_admin, "tipi_taninmadi": skipped,
        "eklendi": inserted, "zenginlestirildi": enriched, "zaten_vardi": skipped_dupe,
        "hata": failed, "cografi_kodlama": geocode_calls, "koordinatsiz_eklendi": no_geocode,
        "dry_run": bool(args.dry_run),
    }
    summary["hesaplanan_toplam"] = (skipped_admin + skipped + inserted + enriched + skipped_dupe + failed)
    cov_path = Path("data/meb_coverage.json")
    if cov_path.exists():
        try:
            cov = json.loads(cov_path.read_text(encoding="utf-8"))
            summary["meb_sorgu"] = len(cov)
            summary["meb_beklenen"] = sum(c["beklenen"] for c in cov if isinstance(c.get("beklenen"), int))
            summary["meb_cekilen"] = sum(c.get("cekilen", 0) for c in cov)
            summary["meb_sorunlu_sorgu"] = sum(1 for c in cov if c.get("beklenen") != c.get("cekilen"))
            summary["il_kodlari"] = sorted({c["il_kodu"] for c in cov})
            summary["sorunlu_sorgular"] = [
                {k: c.get(k) for k in ("il_kodu", "ilce_kodu", "beklenen", "cekilen", "durum")}
                for c in cov if c.get("beklenen") != c.get("cekilen")][:40]
        except Exception as e:
            print(f"UYARI: Kapsama dosyası okunamadı: {e}")
    summary["tipi_taninmayan_ornek"] = skipped_unknown_names[:30]
    print("YUKLEME_OZETI " + json.dumps(summary, ensure_ascii=False))
    # GitHub Actions loglarına her ortamdan erişilemediği için özet
    # scrape_progress tablosuna da yazılır (anahtar: meb_son_yukleme_ozeti).
    if not args.dry_run:
        try:
            requests.post(
                f"{supabase_url}/rest/v1/scrape_progress?on_conflict=key",
                headers={**headers, "Prefer": "resolution=merge-duplicates,return=minimal"},
                json={"key": "meb_son_yukleme_ozeti", "value": json.dumps(summary, ensure_ascii=False)[:5000]},
                timeout=15,
            ).raise_for_status()
        except Exception as e:
            print(f"UYARI: Özet scrape_progress'e yazılamadı: {e}")
    try:
        Path("data").mkdir(parents=True, exist_ok=True)
        Path("data/meb_load_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        print(f"UYARI: Yükleme özeti yazılamadı: {e}")

    if args.dry_run:
        print("... (dry-run, Supabase'e yazılmadı)")
        return

    print(f"Tamamlandı: {inserted} yeni kurum eklendi, {enriched} mevcut kurum zenginleştirildi, {skipped_dupe} zaten var olduğu için atlandı, {geocode_calls} yeni coğrafi kodlama yapıldı.")
    if stopped_early:
        print(f"\nNOT: Coğrafi kodlama bütçesi ({args.max_geocode}) doldu; {no_geocode} kurum koordinatsız eklendi. "
              f"Koordinatları ayrı bir adımda tamamlanmalı.")
    if failed:
        print(f"HATA: {failed} kayıt Supabase'e yazılamadı.")
        sys.exit(1)


if __name__ == "__main__":
    main()
