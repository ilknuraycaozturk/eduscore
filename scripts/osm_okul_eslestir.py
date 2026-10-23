"""OpenStreetMap'teki okul kayıtlarını indirir ve koordinatı olmayan kurumlarla
ad + yakınlık üzerinden eşleştirme ADAYLARI üretir. institutions tablosuna YAZMAZ.

1. Geofabrik Türkiye çıkarımı (osmium ile süzülmüş): amenity=school/kindergarten/college ve adı olan
   tüm nesneler (nokta/alan/ilişki; alanlar için merkez noktası) -> osm_okullar
2. Hedef: koordinatı olmayan ve MEB okul sitesi olmayan kurumlar.
3. Aday kuralı:
   - Okul adındaki ayırt edici sözcüklerin (özel, ilkokulu, anaokulu gibi genel
     sözcükler hariç) en az %75'i OSM adında geçmeli.
   - OSM noktası, kurumun ilçesindeki bilinen okulların ortanca konumuna en çok
     20 km (ilçe ortancası yoksa il ortancasına 40 km) uzaklıkta olmalı.
   - En yüksek örtüşmeli aday tekse 'tekil', birden çoksa 'coklu',
     örtüşme %50–75 ise 'zayif'.
Veri: © OpenStreetMap katkıcıları, ODbL.

Ortam değişkenleri: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
"""
import json
import math
import os
import re
import statistics
import sys
from collections import defaultdict

import requests

from eduscor_data_utils import normalize_turkish

OVERPASS_UCLARI = ["https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter",
                   "https://overpass.private.coffee/api/interpreter"]
SORGU_KARO = """[out:json][timeout:300];
nwr["amenity"~"^(school|kindergarten|college)$"]["name"]({bbox});
out center tags;"""
GENEL = {"ozel", "okulu", "okullari", "okul", "anaokulu", "ilkokulu", "ortaokulu", "lisesi", "lise", "anadolu",
         "fen", "turk", "cocuk", "kreş", "kres", "yuva", "yuvasi", "kurumu", "egitim", "ve", "t", "c", "i", "ii",
         "kampusu", "kampus", "subesi", "sube", "ilk", "orta", "bilim", "teknoloji", "sosyal", "bilimler",
         "uluslararasi", "milletlerarasi", "school", "kindergarten", "college", "kolej", "koleji", "kolejleri",
         "mesleki", "teknik", "merkez", "imam", "hatip", "spor", "guzel", "sanatlar"}


def ascii_tr(s: str) -> str:
    return normalize_turkish(s or "").translate(str.maketrans("çğıöşüâîû", "cgiosuaiu"))


def tok(s: str) -> set[str]:
    return {w for w in re.split(r"[^a-z0-9]+", ascii_tr(s)) if w and len(w) > 1}


KADEME = {"anaokulu": "ana", "anasinifi": "ana", "kres": "ana", "yuva": "ana", "yuvasi": "ana",
          "ilkokulu": "ilk", "ilkokul": "ilk", "ortaokulu": "orta", "ortaokul": "orta",
          "lisesi": "lise", "lise": "lise"}
KAMPUS = {"kolej", "koleji", "kolejleri", "okullari", "kampus", "kampusu", "kurumlari", "egitim"}


def kademe(tokens_: set[str]) -> set[str]:
    return {KADEME[w] for w in tokens_ if w in KADEME}


def km(a, b) -> float:
    return math.hypot((a[0] - b[0]) * 111, (a[1] - b[1]) * 85)


def fetch_all(base, h, path, page=1000):
    rows, off = [], 0
    sep = "&" if "?" in path else "?"
    while True:
        r = requests.get(f"{base}{path}{sep}limit={page}&offset={off}", headers=h, timeout=60)
        r.raise_for_status()
        c = r.json()
        rows.extend(c)
        if len(c) < page:
            return rows
        off += page


def main() -> int:
    base, skey = os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not base or not skey:
        print("HATA: SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY gerekli.")
        return 1
    h = {"apikey": skey, "Authorization": f"Bearer {skey}", "Content-Type": "application/json"}

    def hata_yaz(msg):
        requests.post(f"{base}/rest/v1/scrape_progress?on_conflict=key",
                      headers={**h, "Prefer": "resolution=merge-duplicates,return=minimal"},
                      json={"key": "osm_eslesme_son_ozet", "value": json.dumps({"hata": msg[:900]}, ensure_ascii=False)}, timeout=20)

    girdi = sys.argv[1] if len(sys.argv) > 1 else None
    if girdi == "--db":
        girdi = None
        osm = fetch_all(base, h, "/rest/v1/osm_okullar?select=osm_id,ad,tur,lat,lng,website&order=osm_id")
        print(f"OSM (veritabanından): {len(osm)}")
    elif not girdi:
        hata_yaz("Girdi dosyası (osmium export geojsonseq) verilmedi")
        return 1
    if girdi:
        # Geofabrik Türkiye çıkarımı osmium ile süzülüp GeoJSON satırlarına çevrilir
        # (Overpass sunucuları ülke ölçeğinde zaman aşımına uğruyor).
        elems = []
        with open(girdi, encoding="utf-8") as f:
            for line in f:
                line = line.strip().lstrip("\x1e")
                if not line:
                    continue
                ft = json.loads(line)
                g, t = ft.get("geometry") or {}, ft.get("properties") or {}
                pts = []

                def topla(c):
                    if c and isinstance(c[0], (int, float)):
                        pts.append(c)
                    else:
                        for x in c or []:
                            topla(x)
                topla(g.get("coordinates"))
                if not pts:
                    continue
                lon = sum(p[0] for p in pts) / len(pts)
                lat = sum(p[1] for p in pts) / len(pts)
                elems.append({"type": str(ft.get("id", "x"))[:1] or "x", "id": ft.get("id"), "lat": lat, "lon": lon, "tags": t})
        osm = []
        for e in elems:
            lat = e.get("lat") or (e.get("center") or {}).get("lat")
            lon = e.get("lon") or (e.get("center") or {}).get("lon")
            t = e.get("tags", {})
            if lat is None or lon is None or not t.get("name"):
                continue
            osm.append({"osm_id": str(e["id"]), "ad": t.get("name"), "tur": t.get("amenity"),
                        "lat": lat, "lng": lon, "website": t.get("website") or t.get("contact:website"),
                        "etiketler": {k: v for k, v in t.items() if k in ("name:tr", "operator", "isced:level", "addr:street",
                                                                            "addr:housenumber", "addr:city", "addr:district")}})
        print(f"OSM okul nesnesi: {len(osm)}")
        osm = list({o["osm_id"]: o for o in osm}.values())
        for i in range(0, len(osm), 1000):
            rr = requests.post(f"{base}/rest/v1/osm_okullar?on_conflict=osm_id",
                               headers={**h, "Prefer": "resolution=merge-duplicates,return=minimal"},
                               json=osm[i:i + 1000], timeout=120)
            if rr.status_code >= 300:
                hata_yaz(f"osm_okullar yazılamadı: {rr.status_code} {rr.text[:400]}")
                return 1

    locs = {l["id"]: l for l in fetch_all(base, h, "/rest/v1/locations?select=id,parent_id,level,name")}

    def yer(loc_id):
        il = ilce = None
        loc = locs.get(loc_id)
        while loc:
            if loc["level"] == "district" and ilce is None:
                ilce = loc["id"]
            if loc["level"] == "province":
                il = loc["id"]
                break
            loc = locs.get(loc.get("parent_id"))
        return il, ilce

    var = fetch_all(base, h, "/rest/v1/institutions?select=location_id,lat,lng&lat=not.is.null")
    by_ilce, by_il = defaultdict(list), defaultdict(list)
    for v in var:
        il, ilce = yer(v["location_id"])
        if ilce:
            by_ilce[ilce].append((v["lat"], v["lng"]))
        if il:
            by_il[il].append((v["lat"], v["lng"]))
    med = lambda pts: (statistics.median(p[0] for p in pts), statistics.median(p[1] for p in pts))
    ilce_med = {k: med(v) for k, v in by_ilce.items() if len(v) >= 3}
    il_med = {k: med(v) for k, v in by_il.items() if len(v) >= 3}

    # Üniversite/yurt/dershane gibi okul dışı nesneler elenir; amenity=college yalnızca adı okul/kolej/lise ise.
    YASAK = {"universite", "universitesi", "fakulte", "fakultesi", "yurdu", "yurt", "dershane", "dershanesi", "myo", "enstitu"}
    OKULCA = {"kolej", "koleji", "lisesi", "okulu", "okullari", "ilkokulu", "ortaokulu", "anaokulu", "kampusu"}
    osm = [o for o in osm if not (tok(o["ad"]) & YASAK) and (o.get("tur") != "college" or (tok(o["ad"]) & OKULCA))]
    osm_t = [(o, tok(o["ad"]) - GENEL, tok(o["ad"])) for o in osm]
    # Zincir markalar (ör. Sınav, Final, Bahçeşehir): ayırt edici sözcüğü yalnızca marka olan
    # okul, en yakın kampüse kendiliğinden bağlanmaz.
    from collections import Counter as _C
    marka_sayisi = _C(w for _, ot, _ in osm_t for w in ot)
    dizin = defaultdict(set)
    for i, (_, ot, _) in enumerate(osm_t):
        for w in ot:
            dizin[w].add(i)
    hedef = [k for k in fetch_all(base, h, "/rest/v1/institutions?select=id,name,location_id,website&lat=is.null")
             if "meb.k12.tr" not in (k.get("website") or "")]
    print(f"Hedef kurum: {len(hedef)}")

    adaylar, sayac = [], defaultdict(int)
    for k in hedef:
        ham = tok(re.sub(r"^.* - ", "", k["name"]))
        il, ilce = yer(k["location_id"])
        # Okulun kendi il/ilçe adı ayırt edici sayılmaz ("Özel Fethiye Ortaokulu" ≠ "Fethiye Gazi Ortaokulu").
        yer_tok = tok(locs[il]["name"] if il in locs else "") | tok(locs[ilce]["name"] if ilce in locs else "")
        a = ham - GENEL - yer_tok
        k_kademe = kademe(ham)
        if not a:
            sayac["ayirt_edici_yok"] += 1
            continue
        merkez, sinir = (ilce_med.get(ilce), 20) if ilce in ilce_med else (il_med.get(il), 40)
        if not merkez:
            sayac["konum_referansi_yok"] += 1
            continue
        en_iyi, liste = 0.0, []
        aday_i = set().union(*(dizin.get(w, set()) for w in a))
        for i in aday_i:
            o, ot, o_ham = osm_t[i]
            ot = ot - yer_tok
            ortak = a & ot
            if not ortak:
                continue
            oran = len(ortak) / len(a)
            if oran < 0.5:
                continue
            # Ters yön: OSM adındaki ayırt edici sözcüklerin en az yarısı okul adında olmalı
            # ("Barbaros Hayrettin Paşa İlkokulu" ≠ "Özel Barbaros Anaokulu").
            if ot and (len(ortak) / len(ot) < (0.67 if len(ot) >= 3 else 1.0)):
                continue
            # Kademe çelişkisi: OSM adı tek bir kademe söylüyor ve kampüs/kolej adı değilse,
            # okulun kademesiyle örtüşmeli ("Beytepe Ortaokulu" ≠ "Özel Beytepe Anaokulu").
            ih_k, ih_o = {"imam", "hatip"} <= ham, {"imam", "hatip"} <= o_ham
            if ih_k != ih_o and (("meslek" in o_ham) or ("mesleki" in o_ham) or ih_o or ("mesleki" in ham)):
                continue
            o_kademe = kademe(o_ham)
            if o_kademe and k_kademe and not (o_kademe & k_kademe) and not (o_ham & KAMPUS):
                continue
            d = km((o["lat"], o["lng"]), merkez)
            if d > sinir:
                continue
            if oran > en_iyi:
                en_iyi, liste = oran, [(o, d)]
            elif oran == en_iyi:
                liste.append((o, d))
        if not liste:
            sayac["aday_yok"] += 1
            continue
        # 200 m içindeki adaylar aynı yer sayılır (OSM'de aynı okul nokta + alan olarak girilmiş olabilir).
        kumeler = []
        for o_, d_ in sorted(liste, key=lambda x: x[1]):
            if not any(km((o_["lat"], o_["lng"]), (c["lat"], c["lng"])) < 0.2 for c, _ in kumeler):
                kumeler.append((o_, d_))
        zincir = len(a) == 1 and marka_sayisi[next(iter(a))] >= 5
        durum = "zayif" if (en_iyi < 0.75 or zincir) else ("tekil" if len(kumeler) == 1 else "coklu")
        sayac[durum] += 1
        o, d = kumeler[0]
        liste = kumeler
        adaylar.append({"institution_id": k["id"], "osm_id": o["osm_id"], "osm_ad": o["ad"], "ortusme": round(en_iyi, 2),
                        "mesafe_km": round(d, 1), "aday_sayisi": len(liste), "durum": durum})
    for i in range(0, len(adaylar), 1000):
        requests.post(f"{base}/rest/v1/osm_eslesme_adaylari?on_conflict=institution_id",
                      headers={**h, "Prefer": "resolution=merge-duplicates,return=minimal"},
                      json=adaylar[i:i + 1000], timeout=120).raise_for_status()
    ozet = {"osm_nesne": len(osm), "hedef": len(hedef), **sayac}
    print("OSM_OZETI " + json.dumps(ozet, ensure_ascii=False))
    requests.post(f"{base}/rest/v1/scrape_progress?on_conflict=key",
                  headers={**h, "Prefer": "resolution=merge-duplicates,return=minimal"},
                  json={"key": "osm_eslesme_son_ozet", "value": json.dumps(ozet, ensure_ascii=False)}, timeout=20)
    return 0


if __name__ == "__main__":
    sys.exit(main())
