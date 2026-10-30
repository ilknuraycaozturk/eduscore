"""Hâlâ koordinatı olmayan (MEB sitesi de olmayan) kurumlara, adresindeki
mahallenin merkezini DÜŞÜK güvenle yazar.

Kaynak: Geofabrik Türkiye çıkarımı (osmium ile süzülmüş): place=neighbourhood/
suburb/quarter/village nesneleri ve admin_level=10 sınırları (mahalle). Alan
nesnelerinde merkez, köşe noktalarının ortalamasıdır. © OpenStreetMap katkıcıları, ODbL.

Eşleştirme kuralı:
- Adresten mahalle adı ayrıştırılır ("X MAH." -> "x").
- Aynı adlı OSM mahallesi, kurumun ilçesindeki bilinen kurumların ortanca
  konumuna en çok 15 km (ilçe ortancası yoksa il ortancasına 30 km) uzaklıkta olmalı.
- 500 m içindeki adaylar tek yer sayılır; birden çok ayrı yer kalırsa yazılmaz.
Yazılan: lat/lng, konum_kaynagi='mahalle_merkezi', konum_guven='dusuk'.
Geri almak için: konum_kaynagi='mahalle_merkezi' olanların lat/lng'si boşaltılır.

Kullanım: python scripts/mahalle_merkezi.py mahalleler.geojsonseq [--dry-run]
Ortam değişkenleri: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
"""
import json
import math
import os
import re
import statistics
import sys
from collections import Counter, defaultdict

import requests

from eduscor_data_utils import normalize_turkish


def ascii_tr(s: str) -> str:
    return normalize_turkish(s or "").translate(str.maketrans("çğıöşüâîû", "cgiosuaiu"))


def mah_anahtar(ad: str) -> str:
    a = ascii_tr(ad)
    a = re.sub(r"\b(mahallesi|mahalle|mah|mh)\b\.?", " ", a)
    return re.sub(r"[^a-z0-9]+", "", a)


def adres_mahalle(adres: str) -> str | None:
    m = re.search(r"^(.*?)\s+MAH(?:ALLESİ|\.|\b)", (adres or "").strip(), re.I)
    return m.group(1).strip() if m else None


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
    if len(sys.argv) < 2:
        print("Kullanım: mahalle_merkezi.py <geojsonseq> [--dry-run]")
        return 1
    girdi, dry = sys.argv[1], "--dry-run" in sys.argv
    base, skey = os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not base or not skey:
        print("HATA: SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY gerekli.")
        return 1
    h = {"apikey": skey, "Authorization": f"Bearer {skey}", "Content-Type": "application/json"}

    mahalleler = []
    with open(girdi, encoding="utf-8") as f:
        for line in f:
            line = line.strip().lstrip("\x1e")
            if not line:
                continue
            ft = json.loads(line)
            t, g = ft.get("properties") or {}, ft.get("geometry") or {}
            ad = t.get("name:tr") or t.get("name")
            if not ad:
                continue
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
            mahalleler.append({"osm_id": str(ft.get("id")), "ad": ad,
                               "tur": t.get("place") or ("admin10" if t.get("admin_level") == "10" else t.get("boundary")),
                               "lat": sum(p[1] for p in pts) / len(pts), "lng": sum(p[0] for p in pts) / len(pts)})
    mahalleler = list({m["osm_id"]: m for m in mahalleler}.values())
    print(f"OSM mahalle/yerleşim nesnesi: {len(mahalleler)}")
    if not dry:
        for i in range(0, len(mahalleler), 1000):
            requests.post(f"{base}/rest/v1/osm_mahalleler?on_conflict=osm_id",
                          headers={**h, "Prefer": "resolution=merge-duplicates,return=minimal"},
                          json=mahalleler[i:i + 1000], timeout=120).raise_for_status()
    dizin = defaultdict(list)
    for m in mahalleler:
        dizin[mah_anahtar(m["ad"])].append(m)

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

    by_ilce, by_il = defaultdict(list), defaultdict(list)
    for v in fetch_all(base, h, "/rest/v1/institutions?select=location_id,lat,lng&lat=not.is.null"):
        il, ilce = yer(v["location_id"])
        if ilce:
            by_ilce[ilce].append((v["lat"], v["lng"]))
        if il:
            by_il[il].append((v["lat"], v["lng"]))
    med = lambda pts: (statistics.median(p[0] for p in pts), statistics.median(p[1] for p in pts))
    ilce_med = {k: med(v) for k, v in by_ilce.items() if len(v) >= 3}
    il_med = {k: med(v) for k, v in by_il.items() if len(v) >= 3}

    hedef = [k for k in fetch_all(base, h, "/rest/v1/institutions?select=id,address,location_id,website&lat=is.null")
             if "meb.k12.tr" not in (k.get("website") or "")]
    sayac = Counter()
    yazilacak = []
    for k in hedef:
        mah = adres_mahalle(k.get("address") or "")
        if not mah:
            sayac["adreste_mahalle_yok"] += 1
            continue
        il, ilce = yer(k["location_id"])
        merkez, sinir = (ilce_med.get(ilce), 15) if ilce in ilce_med else (il_med.get(il), 30)
        if not merkez:
            sayac["konum_referansi_yok"] += 1
            continue
        adaylar = [m for m in dizin.get(mah_anahtar(mah), []) if km((m["lat"], m["lng"]), merkez) <= sinir]
        kumeler = []
        for m in sorted(adaylar, key=lambda x: km((x["lat"], x["lng"]), merkez)):
            if not any(km((m["lat"], m["lng"]), (c["lat"], c["lng"])) < 0.5 for c in kumeler):
                kumeler.append(m)
        if not kumeler:
            sayac["mahalle_bulunamadi"] += 1
        elif len(kumeler) > 1:
            sayac["birden_cok_mahalle"] += 1
        else:
            sayac["yazilacak"] += 1
            yazilacak.append((k["id"], kumeler[0]))
    print(f"Hedef: {len(hedef)}; {dict(sayac)}")
    if not dry:
        for kid, m in yazilacak:
            requests.patch(f"{base}/rest/v1/institutions?id=eq.{kid}&lat=is.null", headers=h,
                           json={"lat": m["lat"], "lng": m["lng"], "konum_kaynagi": "mahalle_merkezi", "konum_guven": "dusuk"},
                           timeout=20).raise_for_status()
    ozet = {"hedef": len(hedef), "dry_run": dry, **sayac}
    requests.post(f"{base}/rest/v1/scrape_progress?on_conflict=key",
                  headers={**h, "Prefer": "resolution=merge-duplicates,return=minimal"},
                  json={"key": "mahalle_merkezi_son_ozet", "value": json.dumps(ozet, ensure_ascii=False)}, timeout=20)
    print("MAHALLE_OZETI " + json.dumps(ozet, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
