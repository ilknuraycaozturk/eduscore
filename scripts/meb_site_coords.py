"""Koordinatı olmayan kurumların konumunu okulun kendi MEB sitesinden okur.

MEB okul siteleri (*.meb.k12.tr) iletişim sayfasında (/tema/iletisim.php)
okulun kendi girdiği harita konumunu barındırır. Bu betik o sayfayı indirir,
koordinatı ayıklar, doğrular ve yazar. Sayfanın HTML'i saklanmaz.

Kurallar:
- Saniyede en fazla 1 sayfa (sitelere yük bindirmemek için), çalıştırma
  başına en fazla --limit kurum. Açıklayıcı User-Agent.
- Doğrulama: Türkiye sınırları içinde olmalı; Ankara dışı bir okul için
  Ankara şehir merkezine (25 km) düşen koordinat ve aynı ilçedeki diğer okulların ortancasından
  60 km'den uzak koordinat 'belirsiz' sayılır; 3'ten fazla kurumda aynen
  tekrar eden koordinat (şablon varsayılanı) 'belirsiz' sayılır.
- Her deneme geocode_attempts tablosuna provider='meb_okul_sitesi' ile yazılır;
  başarısız olanlar --retry-days gün geçmeden yeniden denenmez.

Ortam değişkenleri: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
"""
import argparse
import json
import math
import os
import re
import statistics
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

import requests

USER_AGENT = "EduScor-Crawler/1.0 (+destek@eduscor.com; egitim karsilastirma platformu)"
COORD_RE = re.compile(r"(?:[?&;]q|ll|center)=\s*([34]\d\.\d{3,})\s*,\s*([2-4]\d\.\d{3,})", re.I)
PROVIDER = "meb_okul_sitesi"
ANKARA_MERKEZ = (39.925, 32.855)


def fetch_all(base: str, h: dict, path: str, page: int = 1000) -> list[dict]:
    rows, offset = [], 0
    sep = "&" if "?" in path else "?"
    while True:
        r = requests.get(f"{base}{path}{sep}limit={page}&offset={offset}", headers=h, timeout=60)
        r.raise_for_status()
        chunk = r.json()
        rows.extend(chunk)
        if len(chunk) < page:
            return rows
        offset += page


def km(a, b) -> float:
    return math.hypot((a[0] - b[0]) * 111, (a[1] - b[1]) * 85)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=4500)
    ap.add_argument("--retry-days", type=int, default=30)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    base, skey = os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not base or not skey:
        print("HATA: SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY gerekli.")
        return 1
    h = {"apikey": skey, "Authorization": f"Bearer {skey}", "Content-Type": "application/json"}

    locs = {l["id"]: l for l in fetch_all(base, h, "/rest/v1/locations?select=id,parent_id,level,name")}

    def il_of(loc_id):
        loc = locs.get(loc_id)
        while loc:
            if loc["level"] == "province":
                return loc["name"]
            loc = locs.get(loc.get("parent_id"))
        return None

    # Mevcut koordinatlar: ilçe ortancası ve şablon tekrarı kontrolü için
    var = fetch_all(base, h, "/rest/v1/institutions?select=location_id,lat,lng&lat=not.is.null")
    by_loc = defaultdict(list)
    tekrar = Counter()
    for r in var:
        by_loc[r["location_id"]].append((r["lat"], r["lng"]))
        tekrar[(round(r["lat"], 4), round(r["lng"], 4))] += 1
    ortanca = {k: (statistics.median(p[0] for p in v), statistics.median(p[1] for p in v))
               for k, v in by_loc.items() if len(v) >= 3}

    cutoff = (datetime.now(timezone.utc) - timedelta(days=args.retry_days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    son_deneme = {a["institution_id"] for a in fetch_all(
        base, h, f"/rest/v1/geocode_attempts?select=institution_id&provider=eq.{PROVIDER}&attempted_at=gte.{cutoff}")}
    todo = [r for r in fetch_all(base, h, "/rest/v1/institutions?select=id,website,location_id"
                                          "&lat=is.null&website=ilike.*meb.k12.tr*&order=id")
            if r["id"] not in son_deneme]
    print(f"Sırada bekleyen: {len(todo)} kurum; bu çalıştırmada en fazla {args.limit}.")

    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT
    stats = Counter()
    for n, r in enumerate(todo[: args.limit], 1):
        site = re.sub(r"(https?://[^/]+).*", r"\1", r["website"].strip()).replace("http://", "https://")
        url = f"{site}/tema/iletisim.php"
        durum, lat, lng = "hata", None, None
        try:
            resp = session.get(url, timeout=15)
            if resp.status_code != 200:
                durum = "bulunamadi"
            else:
                m = COORD_RE.search(resp.text)
                if not m:
                    durum = "bulunamadi"
                else:
                    lat, lng = float(m.group(1)), float(m.group(2))
                    il = il_of(r.get("location_id"))
                    o = ortanca.get(r.get("location_id"))
                    if not (35.8 <= lat <= 42.2 and 25.6 <= lng <= 44.9):
                        durum = "il_uyusmuyor"
                    elif il and il != "Ankara" and km((lat, lng), ANKARA_MERKEZ) < 25:
                        durum = "belirsiz"  # Ankara dışı okul için Ankara şehir merkezi (olası varsayılan/yanlış giriş)
                    elif o and km((lat, lng), o) > 60:
                        durum = "belirsiz"
                    elif tekrar[(round(lat, 4), round(lng, 4))] >= 3:
                        durum = "belirsiz"
                    else:
                        durum = "ok"
        except Exception as e:
            print(f"  hata {url}: {str(e)[:100]}")
        stats[durum] += 1
        # Aday koordinat 'belirsiz'/'il_uyusmuyor' olsa da deneme kaydında saklanır
        # (izlenebilir kanıt); kurum kaydına yalnızca 'ok' olan yazılır.
        if durum == "ok":
            tekrar[(round(lat, 4), round(lng, 4))] += 1

        if not args.dry_run:
            requests.post(f"{base}/rest/v1/geocode_attempts?on_conflict=institution_id",
                          headers={**h, "Prefer": "resolution=merge-duplicates,return=minimal"},
                          json={"institution_id": r["id"], "attempted_at": datetime.now(timezone.utc).isoformat(),
                                "status": durum, "provider": PROVIDER, "query": url, "lat": lat, "lng": lng},
                          timeout=20).raise_for_status()
            if durum == "ok":
                requests.patch(f"{base}/rest/v1/institutions?id=eq.{r['id']}&lat=is.null", headers=h,
                               json={"lat": lat, "lng": lng, "konum_kaynagi": "meb_okul_sitesi", "konum_guven": "yuksek"}, timeout=20).raise_for_status()
        if n % 250 == 0:
            print(f"  {n} işlendi: {dict(stats)}")
        time.sleep(1.0)

    print("SITE_KONUM_OZETI " + json.dumps(dict(stats), ensure_ascii=False))
    if not args.dry_run:
        requests.post(f"{base}/rest/v1/scrape_progress?on_conflict=key",
                      headers={**h, "Prefer": "resolution=merge-duplicates,return=minimal"},
                      json={"key": "meb_site_koordinat_son_ozet",
                            "value": json.dumps({**stats, "sirada_kalan": max(0, len(todo) - args.limit),
                                                 "tarih": datetime.now(timezone.utc).isoformat()})},
                      timeout=20)
    return 0


if __name__ == "__main__":
    sys.exit(main())
