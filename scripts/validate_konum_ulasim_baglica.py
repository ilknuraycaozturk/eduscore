#!/usr/bin/env python3
"""
EduScor — konum_ulasim kriteri fizibilite doğrulaması (Bağlıca örneklemi, 10 kurum)
Modül: eduscor-data-engine

AMAÇ:
  Bu script SADECE DOĞRULAMA amaçlıdır. Veritabanına HİÇBİR ŞEY YAZMAZ.
  Sadece konsola / CSV'ye sonuç basar, siz gözden geçirip onaylarsınız.

KULLANILAN SERVİSLER (İKİSİ DE ÜCRETSİZ):
  1. Nominatim (OpenStreetMap)  -> adres metninden koordinat bulma (geocoding)
     Kullanım politikası: saniyede EN FAZLA 1 istek, açıklayıcı User-Agent zorunlu.
     https://operations.osmfoundation.org/policies/nominatim/
  2. Overpass API (OpenStreetMap) -> koordinat etrafında en yakın durak/istasyon
     Kamuya açık sunucularda kaba bir kota var (günde birkaç yüz sorgu civarı),
     bu yüzden bu script SADECE 10 kurumluk küçük örneklem için tasarlandı.
     Toplu/otomatik günlük tarama için KULLANMAYIN — production script'i ayrı,
     kademeli (örn. günde 50-100 kurum) çalışacak şekilde tasarlanmalı.

ÇIKTI:
  - Konsola tablo
  - baglica_konum_ulasim_validation.csv dosyası (script ile aynı klasörde)

VERİ KAYNAĞI (ATIF ZORUNLU):
  © OpenStreetMap contributors, ODbL 1.0 lisansı altında.
  Herhangi bir üretim kullanımında EduScor'un bu veriye atıf vermesi gerekir.

ÇALIŞTIRMA:
  pip install requests
  python validate_konum_ulasim_baglica.py
"""

import csv
import math
import time
import sys

import requests

# EduScor destek e-postanızla değiştirin — Nominatim politikası User-Agent'ta
# gerçek bir iletişim bilgisi ister, aksi halde IP'niz engellenebilir.
USER_AGENT = "EduScor-Validation/1.0 (destek@eduscor.com)"

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# Gerçek Supabase sorgusundan alınan 10 Bağlıca kurumu (2026-08-22 itibarıyla).
# id / name / address / lat / lng -> lat,lng zaten doluysa geocoding atlanır.
INSTITUTIONS = [
    {"id": "38ad90c2-f29b-40fb-9ee6-238b26d7af04", "name": "ANKARA - ETİMESGUT - BAĞLICA ANAOKULU",
     "address": None, "lat": 39.9492467, "lng": 32.6630925},
    {"id": "08d6174b-7a3b-4604-adf2-6859f4207b87", "name": "Bağlıca İlkokulu",
     "address": "YENİ BAĞLICA MAH. 2261 SK. 2 SİTESİ SÜLEYMANIYE EĞITIM KURUMLARI NO: 2 ETİMESGUT / ANKARA",
     "lat": 39.8940734, "lng": 32.6480435},
    {"id": "fa7ca10c-8dec-4d3e-b312-2276a1e14155", "name": "Bağlıca Ortaokulu",
     "address": "YENİ BAĞLICA MAH. 2261 SK. 2 SİTESİ SÜLEYMANIYE EĞITIM KURUMLARI NO: 2 ETİMESGUT / ANKARA",
     "lat": 39.9010544, "lng": 32.6518203},
    {"id": "f1b5e5f3-bd56-4a9a-86d9-89e5c3b5a8eb", "name": "ÖZEL AKADEMİK LİDERLİK KİŞİSEL GELİŞİM KURSU",
     "address": "YENİ BAĞLICA MAH. ETİMESGUT BUL. NO: 75 İÇ KAPI NO: 34 ETİMESGUT / ANKARA",
     "lat": None, "lng": None},
    {"id": "af8459ba-6bcc-4147-a5b7-3fd5c3e0929c", "name": "ÖZEL ALFA KUŞAĞI KİŞİSEL GELİŞİM KURSU",
     "address": "BAĞLICA MAH. ETİMESGUT BUL. NO: 110A İÇ KAPI NO: 2 ETİMESGUT / ANKARA",
     "lat": None, "lng": None},
    {"id": "3ede03e0-3974-43fc-ad83-78354f6eead6", "name": "ÖZEL ALTINCI DUYU KİŞİSEL GELİŞİM KURSU",
     "address": "YENİ BAĞLICA MAH. HÖYÜK CAD. ŞEHRIYAR BAĞLICA E BLOK NO: 38B ETİMESGUT / ANKARA",
     "lat": None, "lng": None},
    {"id": "73914bbd-ee21-4473-a382-10f3e03ffe71", "name": "ÖZEL ANAŞEHİR İLKOKULU",
     "address": "BAĞLICA MAH. ETİMESGUT BUL.  NO: 89  İÇ KAPI NO: 1 ETİMESGUT / ANKARA",
     "lat": None, "lng": None},
    {"id": "a32d1016-f731-4c03-a9b0-9d07c0ae9c0a", "name": "ÖZEL ANAŞEHİR ORTAOKULU",
     "address": "BAĞLICA MAH. ETİMESGUT BUL.  NO: 89  İÇ KAPI NO: 1 ETİMESGUT / ANKARA",
     "lat": None, "lng": None},
    {"id": "9cdbdc63-31b2-4a7b-875e-d68bd9cbcbfe", "name": "ÖZEL AYHAN IŞIK ÇOCUK AKADEMİ ANAOKULU",
     "address": "YENİ BAĞLICA MAH. ETİMESGUT BUL. NO: 31 ETİMESGUT / ANKARA",
     "lat": None, "lng": None},
    {"id": "26e62336-8c6b-478a-9d6a-e6c77101e376", "name": "ÖZEL BAĞLICA AMERİKAN KÜLTÜR YABANCI DİL KURSU",
     "address": "YENİ BAĞLICA MAH. ZİRVE CAD. NO: 81B ETİMESGUT / ANKARA",
     "lat": None, "lng": None},
]


def geocode_nominatim(address: str):
    """Adres metnini Nominatim ile koordinata çevirir. Bulamazsa None döner.
    Ham (raw) sonuç döner — bu 'doğrulanmış koordinat' değil, tek kaynaklı bir tahmindir."""
    params = {
        "q": address,
        "format": "json",
        "countrycodes": "tr",
        "limit": 1,
    }
    headers = {"User-Agent": USER_AGENT}
    try:
        resp = requests.get(NOMINATIM_URL, params=params, headers=headers, timeout=15)
        resp.raise_for_status()
        results = resp.json()
        if not results:
            return None, "sonuç yok"
        top = results[0]
        return (float(top["lat"]), float(top["lon"])), top.get("display_name", "")
    except Exception as exc:
        return None, f"hata: {exc}"


def haversine_m(lat1, lon1, lat2, lon2):
    """İki koordinat arası mesafe (metre)."""
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def nearest_transit_overpass(lat: float, lng: float, radius_m: int = 1200):
    """Overpass API ile koordinat etrafında en yakın toplu taşıma noktasını bulur.
    Ham sonuç döner: (mesafe_metre, isim, tip) ya da (None, None, None)."""
    query = f"""
    [out:json][timeout:25];
    (
      node["highway"="bus_stop"](around:{radius_m},{lat},{lng});
      node["public_transport"="platform"](around:{radius_m},{lat},{lng});
      node["railway"~"station|tram_stop|halt"](around:{radius_m},{lat},{lng});
      node["amenity"="bus_station"](around:{radius_m},{lat},{lng});
    );
    out body;
    """
    headers = {"User-Agent": USER_AGENT}
    try:
        resp = requests.post(OVERPASS_URL, data={"data": query}, headers=headers, timeout=30)
        resp.raise_for_status()
        elements = resp.json().get("elements", [])
        if not elements:
            return None, None, None
        best = None
        for el in elements:
            d = haversine_m(lat, lng, el["lat"], el["lon"])
            if best is None or d < best[0]:
                name = el.get("tags", {}).get("name", "(isimsiz durak)")
                kind = el.get("tags", {}).get("highway") or el.get("tags", {}).get("railway") \
                    or el.get("tags", {}).get("public_transport") or el.get("tags", {}).get("amenity")
                best = (d, name, kind)
        return best
    except Exception as exc:
        return None, f"hata: {exc}", None


def main():
    rows = []
    print(f"{'Kurum':45s} {'Koord. Kaynağı':18s} {'En Yakın Durak':30s} {'Mesafe (m)':>10s}")
    print("-" * 110)

    for inst in INSTITUTIONS:
        lat, lng = inst["lat"], inst["lng"]
        coord_source = "veritabanı (mevcut)"

        if lat is None or lng is None:
            if not inst["address"]:
                rows.append({**inst, "geocode_source": "adres yok", "distance_m": None,
                             "nearest_name": None, "nearest_type": None})
                print(f"{inst['name'][:44]:45s} {'ADRES YOK':18s} {'-':30s} {'-':>10s}")
                continue
            time.sleep(1)  # Nominatim politikası: saniyede max 1 istek
            coord, note = geocode_nominatim(inst["address"] + ", Ankara, Türkiye")
            if coord is None:
                rows.append({**inst, "geocode_source": f"Nominatim başarısız ({note})",
                             "distance_m": None, "nearest_name": None, "nearest_type": None})
                print(f"{inst['name'][:44]:45s} {'BULUNAMADI':18s} {'-':30s} {'-':>10s}")
                continue
            lat, lng = coord
            coord_source = "Nominatim (yeni)"

        time.sleep(1)  # Overpass'a nazik davranmak için
        dist, name, kind = nearest_transit_overpass(lat, lng)

        if dist is None:
            rows.append({**inst, "lat": lat, "lng": lng, "geocode_source": coord_source,
                         "distance_m": None, "nearest_name": None, "nearest_type": None})
            print(f"{inst['name'][:44]:45s} {coord_source:18s} {'DURAK BULUNAMADI':30s} {'-':>10s}")
        else:
            rows.append({**inst, "lat": lat, "lng": lng, "geocode_source": coord_source,
                         "distance_m": round(dist, 1), "nearest_name": name, "nearest_type": kind})
            print(f"{inst['name'][:44]:45s} {coord_source:18s} {str(name)[:29]:30s} {round(dist):>10d}")

    with open("baglica_konum_ulasim_validation.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "id", "name", "address", "lat", "lng", "geocode_source",
            "distance_m", "nearest_name", "nearest_type"])
        writer.writeheader()
        for r in rows:
            writer.writerow({k: r.get(k) for k in writer.fieldnames})

    print("\nSonuçlar 'baglica_konum_ulasim_validation.csv' dosyasına yazıldı.")
    print("NOT: Bu script veritabanına HİÇBİR ŞEY YAZMADI. Sonuçları gözden geçirip")
    print("onayladıktan sonra ayrı bir production script'iyle institution_criteria_scores'a işlenmeli.")


if __name__ == "__main__":
    sys.exit(main())
