"""
diagnose_discover_ilceler.py
==============================
TEŞHİS: MEB sitesinde Ankara (il_kodu=6) için ilçe seçim kutusu (dropdown)
GERÇEKTEN kaldırıldı mı, yoksa hâlâ DOM'da var mı? scrape_meb_schools.py
içindeki discover_ilceler() fonksiyonunu doğrudan çağırıp sonucu hem
konsola hem Supabase'e (scrape_progress.meb_debug_ilce_discovery) yazar.
"""

import json
import os
import sys
import urllib.request

sys.path.insert(0, "scripts")
from scrape_meb_schools import discover_ilceler  # noqa: E402


def log_to_supabase(message: str) -> None:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        print("UYARI: SUPABASE_URL/SUPABASE_SERVICE_ROLE_KEY yok, sadece konsola yazılıyor.")
        return
    try:
        payload = json.dumps({"key": "meb_debug_ilce_discovery", "value": message[:5000]}).encode("utf-8")
        req = urllib.request.Request(
            f"{url}/rest/v1/scrape_progress?on_conflict=key",
            data=payload,
            method="POST",
            headers={
                "apikey": key,
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
                "Prefer": "resolution=merge-duplicates,return=minimal",
            },
        )
        resp = urllib.request.urlopen(req, timeout=10)
        print(f"Supabase'e yazıldı (http {resp.status}).")
    except Exception as e:
        print(f"Supabase'e yazılamadı: {type(e).__name__}: {e}")


print("discover_ilceler(il_kodu='6') çağrılıyor (Ankara)...")
ilceler = discover_ilceler("6")

if ilceler:
    sonuc = f"BULUNDU: {len(ilceler)} ilçe -> {[i['ad'] for i in ilceler]}"
else:
    sonuc = "BULUNAMADI: ilçe seçim kutusu DOM'da yok (0 ilçe döndü)."

print(sonuc)
log_to_supabase(sonuc)
