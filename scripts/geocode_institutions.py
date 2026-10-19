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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=4800)
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

    cutoff = (datetime.now(timezone.utc) - timedelta(days=args.retry_days)).isoformat()
    recent_fail = {a["institution_id"] for a in fetch_all(
        base, h, f"/rest/v1/geocode_attempts?select=institution_id&status=neq.ok&attempted_at=gte.{cutoff}")}
    todo = [r for r in fetch_all(base, h, "/rest/v1/institutions?select=id,name,location_id&lat=is.null&order=id")
            if r["id"] not in recent_fail]
    print(f"Koordinatsız ve sırada bekleyen: {len(todo)} kurum; bu çalıştırmada en fazla {args.limit}.")

    stats = {"ok": 0, "bulunamadi": 0, "il_uyusmuyor": 0, "hata": 0}
    for n, r in enumerate(todo[: args.limit], 1):
        il, ilce = place(r.get("location_id"))
        if not il:
            continue
        q = ", ".join(x for x in [clean_name(r["name"]), ilce, il, "Türkiye"] if x)
        status, res = "hata", {}
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
                status = "ok" if normalize_turkish(il) in shown else "il_uyusmuyor"
        except Exception as e:
            print(f"  hata ({r['id']}): {str(e)[:120]}")
        stats[status] += 1

        lat = float(res["lat"]) if status == "ok" else None
        lng = float(res["lon"]) if status == "ok" else None
        if not args.dry_run:
            attempt = {"institution_id": r["id"], "attempted_at": datetime.now(timezone.utc).isoformat(),
                       "status": status, "provider": "locationiq", "query": q,
                       "result_display_name": res.get("display_name"), "result_class": res.get("class"),
                       "result_type": res.get("type"), "lat": lat, "lng": lng}
            requests.post(f"{base}/rest/v1/geocode_attempts?on_conflict=institution_id",
                          headers={**h, "Prefer": "resolution=merge-duplicates,return=minimal"},
                          json=attempt, timeout=20).raise_for_status()
            if status == "ok":
                requests.patch(f"{base}/rest/v1/institutions?id=eq.{r['id']}", headers=h,
                               json={"lat": lat, "lng": lng}, timeout=20).raise_for_status()
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
