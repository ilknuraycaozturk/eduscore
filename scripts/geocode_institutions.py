"""Koordinatı olmayan kurumların konumunu LocationIQ ile tamamlar.

- Her çalıştırmada en fazla --limit kurum işlenir (ücretsiz plan günlük
  kotası için pay bırakılır). Saniyede en fazla 1 istek atılır.
- Sorgu: "<okul adı>, <ilçe>, <il>, Türkiye" (yalnızca Türkiye içinde arar).
- Sonuç, kurumun kendi iliyle doğrulanır: dönen adreste il adı geçmiyorsa
  koordinat YAZILMAZ ('il_uyusmuyor'). Böylece Ağustos'taki "her okul
  Ankara'da" hatası gibi yanlış konumlar veritabanına girmez.
- Her deneme public.geocode_attempts tablosuna yazılır; başarısız olanlar
  --retry-days gün geçmeden yeniden denenmez.

Ortam değişkenleri: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, LOCATIONIQ_API_KEY
"""
import argparse
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone

import requests

from eduscor_data_utils import normalize_turkish

LOCATIONIQ_URL = "https://us1.locationiq.com/v1/search"
# ÜCRETSİZ PLAN SINIRI ASLA AŞILMAZ: LocationIQ Free = 5.000 istek/gün, 2 istek/sn.
# Son 24 saatte yapılmış TÜM denemeler sayılır (deneme modu dahil); elle
# başlatılan ek çalıştırmalar da bu tavanı geçemez. Kayan 24 saatlik pencere,
# LocationIQ'nun günü hangi saat diliminde sıfırladığından bağımsız olarak
# herhangi bir takvim gününde 4.500'ü aşmamayı garanti eder. Saniyede ~1 istek.
GUNLUK_TAVAN = 4500


def fetch_all(base: str, headers: dict, path: str, page: int = 1000) -> list[dict]:
    rows, offset = [], 0
    sep = "&" if "?" in path else "?"
    while True:
        r = requests.get(f"{base}{path}{sep}limit={page}&offset={offset}", headers=headers, timeout=60)
        r.raise_for_status()
        chunk = r.json()
        rows.extend(chunk)
        if len(chunk) < page:
            return rows
        offset += page


def clean_name(name: str) -> str:
    parts = [p.strip() for p in name.split(" - ")]
    return parts[-1] if len(parts) >= 2 else name.strip()


def _tokens(text: str) -> set[str]:
    import re
    t = normalize_turkish(text)
    return {w for w in re.split(r"[^a-z0-9]+", t) if w and w not in {"ozel", "t", "c"}}


OKUL_TURLERI = {"school", "kindergarten", "college"}


def dogrula(res: dict, okul_adi: str, il: str, ilce: str | None) -> str:
    """Yalnızca BİNA düzeyinde, adı okulla örtüşen ve aynı il/ilçede olan sonucu
    kabul eder. 23.10.2026 deneme çalışmasında gevşek kabulün komşu ilçedeki
    başka okulları, köy merkezlerini ve yolları 'bulunmuş' saydığı görüldü."""
    shown = normalize_turkish(res.get("display_name", ""))
    if normalize_turkish(il) not in shown:
        return "il_uyusmuyor"
    if res.get("class") not in ("amenity", "building") or res.get("type") not in OKUL_TURLERI:
        return "belirsiz"
    if ilce and normalize_turkish(ilce) != "merkez" and normalize_turkish(ilce) not in shown:
        return "belirsiz"
    ad_sonuc = _tokens(res.get("display_name", "").split(",")[0])
    ad_okul = _tokens(okul_adi)
    if not ad_okul or len(ad_okul & ad_sonuc) / len(ad_okul) < 0.8:
        return "belirsiz"
    return "ok"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=4500)
    ap.add_argument("--retry-days", type=int, default=30)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    base = os.environ.get("SUPABASE_URL")
    skey = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    lkey = os.environ.get("LOCATIONIQ_API_KEY")
    if not base or not skey:
        print("HATA: SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY gerekli.")
        return 1
    if not lkey:
        print("LOCATIONIQ_API_KEY tanımlı değil; konum tamamlama atlandı.")
        return 0
    h = {"apikey": skey, "Authorization": f"Bearer {skey}", "Content-Type": "application/json"}

    locs = {l["id"]: l for l in fetch_all(base, h, "/rest/v1/locations?select=id,parent_id,level,name")}

    def place(loc_id):
        il = ilce = None
        loc = locs.get(loc_id)
        while loc:
            if loc["level"] == "district" and ilce is None:
                ilce = loc["name"]
            if loc["level"] == "province":
                il = loc["name"]
                break
            loc = locs.get(loc.get("parent_id"))
        return il, ilce

    cutoff = (datetime.now(timezone.utc) - timedelta(days=args.retry_days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    recent_fail = {a["institution_id"] for a in fetch_all(
        base, h, f"/rest/v1/geocode_attempts?select=institution_id&status=neq.ok&attempted_at=gte.{cutoff}")}
    todo = [r for r in fetch_all(base, h, "/rest/v1/institutions?select=id,name,location_id&lat=is.null&order=id")
            if r["id"] not in recent_fail]
    gun_basi = (datetime.now(timezone.utc) - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%SZ")  # URL içinde "+" boşluğa dönüşmesin
    r_cnt = requests.get(f"{base}/rest/v1/geocode_request_log?select=id&provider=eq.locationiq&requested_at=gte.{gun_basi}",
                         headers={**h, "Prefer": "count=exact", "Range": "0-0"}, timeout=30)
    r_cnt.raise_for_status()
    bugun = int(r_cnt.headers.get("Content-Range", "*/0").split("/")[-1] or 0)
    kalan = max(0, GUNLUK_TAVAN - bugun)
    args.limit = min(args.limit, kalan)
    print(f"Son 24 saatte yapılan istek: {bugun}; tavan {GUNLUK_TAVAN}; bu çalıştırmada en fazla {args.limit}.")
    print(f"Koordinatsız ve sırada bekleyen: {len(todo)} kurum.")
    if args.limit == 0:
        print("Günlük tavana ulaşıldı; yarın devam edilecek.")
        return 0

    stats = {"ok": 0, "bulunamadi": 0, "il_uyusmuyor": 0, "belirsiz": 0, "hata": 0}
    for n, r in enumerate(todo[: args.limit], 1):
        il, ilce = place(r.get("location_id"))
        if not il:
            continue
        ilce_q = None if (ilce and normalize_turkish(ilce) == "merkez") else ilce  # OSM'de "Merkez" ilçe adı yok
        q = ", ".join(x for x in [clean_name(r["name"]), ilce_q, il, "Türkiye"] if x)
        status, res = "hata", {}
        # İstek ATILMADAN ÖNCE kayda geçer: iş yarıda kesilse bile sayım eksik kalmaz.
        requests.post(f"{base}/rest/v1/geocode_request_log", headers={**h, "Prefer": "return=minimal"},
                      json={"provider": "locationiq"}, timeout=20).raise_for_status()
        try:
            resp = requests.get(LOCATIONIQ_URL, params={"key": lkey, "q": q, "format": "json",
                                                        "countrycodes": "tr", "limit": 1}, timeout=20)
            if resp.status_code == 404:
                status = "bulunamadi"
            elif resp.status_code == 429:
                print("Kota/hız sınırına ulaşıldı; çalıştırma durduruluyor.")
                break
            else:
                resp.raise_for_status()
                res = resp.json()[0]
                shown = normalize_turkish(res.get("display_name", ""))
                status = dogrula(res, clean_name(r["name"]), il, ilce)
        except Exception as e:
            print(f"  hata ({r['id']}): {str(e)[:120]}")
        stats[status] += 1

        lat = float(res["lat"]) if status == "ok" else None
        lng = float(res["lon"]) if status == "ok" else None
        # Deneme modunda da deneme kaydı yazılır; yalnızca kurum koordinatı yazılmaz.
        if True:
            attempt = {"institution_id": r["id"], "attempted_at": datetime.now(timezone.utc).isoformat(),
                       "status": status, "provider": "locationiq", "query": q,
                       "result_display_name": res.get("display_name"), "result_class": res.get("class"),
                       "result_type": res.get("type"), "lat": lat, "lng": lng}
            requests.post(f"{base}/rest/v1/geocode_attempts?on_conflict=institution_id",
                          headers={**h, "Prefer": "resolution=merge-duplicates,return=minimal"},
                          json=attempt, timeout=20).raise_for_status()
            if status == "ok" and not args.dry_run:
                requests.patch(f"{base}/rest/v1/institutions?id=eq.{r['id']}", headers=h,
                               json={"lat": lat, "lng": lng, "konum_kaynagi": "locationiq", "konum_guven": "orta"}, timeout=20).raise_for_status()
        if n % 200 == 0:
            print(f"  {n} işlendi: {stats}")
        time.sleep(1.05)

    print("KONUM_OZETI " + json.dumps(stats, ensure_ascii=False))
    if not args.dry_run:
        requests.post(f"{base}/rest/v1/scrape_progress?on_conflict=key",
                      headers={**h, "Prefer": "resolution=merge-duplicates,return=minimal"},
                      json={"key": "geocode_son_ozet",
                            "value": json.dumps({**stats, "tarih": datetime.now(timezone.utc).isoformat()})},
                      timeout=20)
    return 0


if __name__ == "__main__":
    sys.exit(main())
