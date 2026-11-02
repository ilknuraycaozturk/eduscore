"""Koordinatı olmayan kurumların konumunu okulun kendi MEB sitesinden okur.

MEB okul siteleri (*.meb.k12.tr) iletişim sayfasında (/tema/iletisim.php)
okulun kendi girdiği harita konumunu barındırır. Bu betik o sayfayı indirir,
koordinatı ayıklar, doğrular ve yazar. Sayfanın HTML'i saklanmaz.

Kurallar:
- Aynı anda en fazla --paralel (varsayılan 4) istek; çalıştırma başına en fazla
  --limit kurum ve --max-dakika süre. Açıklayıcı User-Agent.
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
import threading
import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

import html as _html

import requests

from check_websites import OG_RE, TITLE_RE, degerlendir

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
    ap.add_argument("--paralel", type=int, default=4, help="Aynı anda en fazla kaç siteye istek")
    ap.add_argument("--max-dakika", type=float, default=100, help="Bu süreden sonra yeni site alınmaz")
    args = ap.parse_args()
    t0 = time.monotonic()

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

    def ilce_of(loc_id):
        loc = locs.get(loc_id)
        while loc:
            if loc["level"] == "district":
                return loc["name"]
            if loc["level"] == "province":
                return None
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
    todo = [r for r in fetch_all(base, h, "/rest/v1/institutions?select=id,name,website,location_id"
                                          "&lat=is.null&website=ilike.*meb.k12.tr*&order=id")
            if r["id"] not in son_deneme]
    print(f"Sırada bekleyen: {len(todo)} kurum; bu çalıştırmada en fazla {args.limit}.")

    stats = Counter()
    kilit = threading.Lock()
    yerel = threading.local()

    def oturum():
        if not hasattr(yerel, "s"):
            yerel.s = requests.Session()
            yerel.s.headers["User-Agent"] = USER_AGENT
        return yerel.s

    def isle(r):
        site = re.sub(r"(https?://[^/]+).*", r"\1", r["website"].strip()).replace("http://", "https://")
        url = f"{site}/tema/iletisim.php"
        durum, lat, lng = "hata", None, None
        site_durum, baslik, oran, kod = "erisilemedi", "", None, None
        try:
            t_ist = time.monotonic()
            try:
                resp = oturum().get(url, timeout=15)
            finally:
                sureler.append(time.monotonic() - t_ist)
            kod = resp.status_code
            if resp.status_code == 200:
                # Aynı ziyarette site doğrulaması: sayfa başlığı ("İL / İLÇE - Okul Adı") okulla örtüşüyor mu?
                t = resp.text[:200000]
                parcalar = [_html.unescape(x.strip()) for x in TITLE_RE.findall(t)[:1] + OG_RE.findall(t)[:1]]
                baslik = " | ".join(x for x in parcalar if x)[:500]
                site_durum, oran = degerlendir(r["name"], il_of(r.get("location_id")), ilce_of(r.get("location_id")), baslik)
            if resp.status_code != 200:
                durum = "bulunamadi"
            elif site_durum == "eslesmiyor":
                durum = "belirsiz"  # site başka bir okula ait: koordinatı da o okulun
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
                    else:
                        durum = "ok"
        except Exception as e:
            print(f"  hata {url}: {str(e)[:100]}")
        with kilit:
            if durum == "ok":
                anahtar = (round(lat, 4), round(lng, 4))
                if tekrar[anahtar] >= 3:
                    durum = "belirsiz"  # şablon varsayılanı
                else:
                    tekrar[anahtar] += 1
            stats[durum] += 1
            stats["site_" + site_durum] += 1
        # Aday koordinat 'belirsiz'/'il_uyusmuyor' olsa da deneme kaydında saklanır
        # (izlenebilir kanıt); kurum kaydına yalnızca 'ok' olan yazılır.
        if not args.dry_run:
            requests.post(f"{base}/rest/v1/website_dogrulama?on_conflict=institution_id",
                          headers={**h, "Prefer": "resolution=merge-duplicates,return=minimal"},
                          json={"institution_id": r["id"], "url": r["website"], "durum": site_durum,
                                "sayfa_basligi": baslik or None, "ortusme": oran, "http_kodu": kod, "son_url": url,
                                "kontrol_tarihi": datetime.now(timezone.utc).isoformat()}, timeout=20).raise_for_status()
            requests.post(f"{base}/rest/v1/geocode_attempts?on_conflict=institution_id",
                          headers={**h, "Prefer": "resolution=merge-duplicates,return=minimal"},
                          json={"institution_id": r["id"], "attempted_at": datetime.now(timezone.utc).isoformat(),
                                "status": durum, "provider": PROVIDER, "query": url, "lat": lat, "lng": lng},
                          timeout=20).raise_for_status()
            if durum == "ok":
                requests.patch(f"{base}/rest/v1/institutions?id=eq.{r['id']}&lat=is.null", headers=h,
                               json={"lat": lat, "lng": lng, "konum_kaynagi": "meb_okul_sitesi", "konum_guven": "yuksek"}, timeout=20).raise_for_status()

    hazirlik_sn = round(time.monotonic() - t0)
    sureler = []
    # Süre bütçesi: iş akışının zaman sınırına takılmadan bitip özeti yazabilmek için
    # bütçe dolunca yeni site alınmaz, sürmekte olanlar tamamlanır.
    bitis = time.monotonic() + args.max_dakika * 60
    islenen = 0
    sira = iter(todo[: args.limit])
    with ThreadPoolExecutor(max_workers=args.paralel) as havuz:
        bekleyen = set()
        while True:
            while len(bekleyen) < args.paralel * 2 and time.monotonic() < bitis:
                r = next(sira, None)
                if r is None:
                    break
                bekleyen.add(havuz.submit(isle, r))
            if not bekleyen:
                break
            bitti, bekleyen = wait(bekleyen, return_when=FIRST_COMPLETED)
            for f in bitti:
                try:
                    f.result()
                except Exception as e:
                    print(f"  yazma hatası: {str(e)[:120]}")
                    stats["yazma_hatasi"] += 1
                islenen += 1
                if islenen % 250 == 0:
                    print(f"  {islenen} işlendi: {dict(stats)}")

    stats["islenen"] = islenen
    stats["hazirlik_sn"] = hazirlik_sn
    stats["toplam_sn"] = round(time.monotonic() - t0)
    if sureler:
        sureler.sort()
        stats["istek_ort_sn"] = round(sum(sureler) / len(sureler), 2)
        stats["istek_medyan_sn"] = round(sureler[len(sureler) // 2], 2)
        stats["istek_15sn_ustu"] = sum(1 for x in sureler if x >= 14.9)
    print("SITE_KONUM_OZETI " + json.dumps(dict(stats), ensure_ascii=False))
    if True:  # deneme (dry-run) çalıştırmasında da özet yazılır; yalnızca anahtar farklı
        requests.post(f"{base}/rest/v1/scrape_progress?on_conflict=key",
                      headers={**h, "Prefer": "resolution=merge-duplicates,return=minimal"},
                      json={"key": "meb_site_koordinat_deneme_ozet" if args.dry_run else "meb_site_koordinat_son_ozet",
                            "value": json.dumps({**stats, "sirada_kalan": max(0, len(todo) - islenen),
                                                 "tarih": datetime.now(timezone.utc).isoformat()})},
                      timeout=20)
    return 0


if __name__ == "__main__":
    sys.exit(main())
