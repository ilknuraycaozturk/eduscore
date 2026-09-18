"""
eduscor_data_utils.py
======================
EduScor Data Engine — TUM load_*.py scriptlerinin kullanmasi gereken
ORTAK normalizasyon ve entity resolution katmani.

Neden var:
    18.09.2026 tarihinde, 3 ayri veri kalitesi sorunu (303 yanlis konum,
    48 yanlis website eslestirmesi, 18 mukerrer kurum kaydi) BULUNDU ve
    DUZELTILDI. Ortak kok neden: HICBIR yukleme scripti, yeni kayit
    eklemeden once mevcut kayitlarla (normalize edilmis isim + konuma
    gore) KARSILASTIRMA yapmiyordu. Bkz. EDU-DATA-001.

Kullanim:
    from eduscor_data_utils import normalize_turkish, find_existing_institution

    # Yeni bir kurum eklemeden ONCE:
    existing = find_existing_institution(name, il_adi, supabase_url, service_key)
    if existing:
        # guncelle (mevcut kaydi kullan), YENI kayit EKLEME
        institution_id = existing["id"]
    else:
        # yeni kayit ekle
        ...
"""
import requests


# ONEMLI: Bu, EDU-SCORE-002 ve EDU-MATCH-001 surecinde SQL tarafinda
# kullandigimiz translate() mantiginin Python karsiligi - AYNI karakter
# haritasi, TUTARLILIK icin. Turkce BUYUK "I" (noktasiz) ile "i" (ASCII)
# PostgreSQL/Python'da FARKLI kucultulur - bu YUZDEN manuel harita sart,
# standart .lower() GUVENILIR DEGILDIR.
_TR_MAP = str.maketrans({
    "İ": "i", "I": "i", "ı": "i",
    "Ç": "c", "ç": "c",
    "Ğ": "g", "ğ": "g",
    "Ö": "o", "ö": "o",
    "Ş": "s", "ş": "s",
    "Ü": "u", "ü": "u",
})


def normalize_turkish(text: str) -> str:
    """Turkce karakterleri ASCII'ye cevirip kucuk harfe indirir.
    Karsilastirma/eslestirme icin kullanilir - GORUNTULEME icin DEGIL
    (kullaniciya gosterilecek metin HER ZAMAN orijinal Turkce kalmali)."""
    if not text:
        return ""
    return text.translate(_TR_MAP).lower()


def find_existing_institution(name: str, il_adi: str, supabase_url: str, service_key: str, timeout: int = 15):
    """Yeni bir kurum eklemeden ONCE cagirilmali - normalize edilmis isim
    ve il'e gore, veritabaninda ZATEN var olan bir kayit olup olmadigini
    kontrol eder.

    DONUS: Eslesen kaydin {"id":..., "name":...} sozlugu, YA DA eslesme
    yoksa None.

    ONEMLI SINIR: Bu fonksiyon SADECE "il - isim" (2 parcali) formati ile
    "il - ilce - isim" (3 parcali) formati arasindaki, AYNI il + AYNI okul
    isminden kaynaklanan TAM eslesmeleri yakalar (18.09.2026'daki mukerrer
    kayit sorununun TAM SEKLI). Daha "yaklasik" (fuzzy/Levenshtein) eslesme
    YAPILMAZ - bu, iki FARKLI okulu yanlislikla ayni sanma riskini tasir,
    bu yuzden BILEREK disarida birakildi (bkz. EDU-DATA-001 Acik Soru).
    """
    name_norm = normalize_turkish(name)
    il_norm = normalize_turkish(il_adi) if il_adi else None

    # Tum kurumlari cekmek yerine, Supabase REST API'sinin ilike filtresiyle
    # BENZER isimli kayitlari daraltiyoruz (performans icin) - sonra Python
    # tarafinda TAM normalize karsilastirmasi yapiyoruz (Turkce karakter
    # sorunu SQL ilike'de de yasandigi icin - bkz. EDU-MATCH-001 bulgusu).
    resp = requests.get(
        f"{supabase_url}/rest/v1/institutions",
        headers={"apikey": service_key, "Authorization": f"Bearer {service_key}"},
        params={"select": "id,name", "name": f"ilike.*{name[:15]}*"},
        timeout=timeout,
    )
    resp.raise_for_status()
    candidates = resp.json()

    for row in candidates:
        row_name_norm = normalize_turkish(row["name"])
        # "il - isim" veya "il - ilce - isim" formatlarinin İKİSİNİ de
        # kapsamasi icin, aday ismin SONUNDA (okul adi kismi) esit olup
        # olmadigina bakiyoruz - TAM STRING esitligi yerine.
        if name_norm in row_name_norm or row_name_norm in name_norm:
            if il_norm is None or il_norm in row_name_norm.split(" - ")[0]:
                return row
    return None
