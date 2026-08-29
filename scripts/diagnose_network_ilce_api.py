"""
diagnose_network_ilce_api.py
==============================
TEŞHİS: discover_ilceler() sadece DOM'daki <select> elemanını arıyordu ve
"BULUNAMADI" sonucu verdi. Ama dropdown görsel olarak kalkmış olsa bile,
MEB'in sayfası arka planda hâlâ bir "ilçe listesi" API/AJAX isteği yapıyor
olabilir (örn. il seçilince JS ile çekilen bir endpoint). Bu script,
sayfa yüklenirken yapılan TÜM ağ isteklerini yakalayıp, "ilce"/"ILCE"
geçen herhangi bir istek olup olmadığını raporlar.
"""

import json
import os
import sys
import urllib.request

from playwright.sync_api import sync_playwright

MEB_URL = "https://www.meb.gov.tr/baglantilar/okullar/index.php"


def log_to_supabase(key: str, message: str) -> None:
    url = os.environ.get("SUPABASE_URL")
    api_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not api_key:
        print("UYARI: SUPABASE_URL/SUPABASE_SERVICE_ROLE_KEY yok, sadece konsola yazılıyor.")
        return
    try:
        payload = json.dumps({"key": key, "value": message[:5000]}).encode("utf-8")
        req = urllib.request.Request(
            f"{url}/rest/v1/scrape_progress?on_conflict=key",
            data=payload,
            method="POST",
            headers={
                "apikey": api_key,
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "Prefer": "resolution=merge-duplicates,return=minimal",
            },
        )
        resp = urllib.request.urlopen(req, timeout=10)
        print(f"Supabase'e yazıldı (http {resp.status}).")
    except Exception as e:
        print(f"Supabase'e yazılamadı: {type(e).__name__}: {e}")


all_requests = []
ilce_related = []


def on_request(request):
    try:
        all_requests.append(request.url)
        lower = request.url.lower()
        if "ilce" in lower or "ilçe" in lower:
            ilce_related.append(f"{request.method} {request.url}")
    except Exception:
        pass


try:
    print(f"Sayfaya gidiliyor: {MEB_URL}?ILKODU=6")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.on("request", on_request)
        try:
            page.goto(f"{MEB_URL}?ILKODU=6", wait_until="networkidle", timeout=20000)
        except Exception as e:
            print(f"goto hatası (yine de devam): {e}")

        il_dropdown_info = "kontrol edilemedi"
        try:
            il_select = page.query_selector("select#ILKODU") or page.query_selector("select[name='ILKODU']")
            if il_select:
                options = page.query_selector_all("select#ILKODU option, select[name='ILKODU'] option")
                il_dropdown_info = f"BULUNDU, {len(options)} secenek"
            else:
                il_dropdown_info = "bulunamadi"
        except Exception as e:
            il_dropdown_info = f"hata: {e}"
        print(f"Il dropdown durumu: {il_dropdown_info}")

        browser.close()

    print(f"\nToplam yakalanan istek sayisi: {len(all_requests)}")
    print(f"'ilce' gecen istek sayisi: {len(ilce_related)}")
    for r in ilce_related:
        print("  ", r)

    if ilce_related:
        sonuc = f"BULUNDU: {len(ilce_related)} ilce-iliskili istek -> {ilce_related[:5]}"
    else:
        sonuc = f"BULUNAMADI: Hicbir 'ilce' iceren network istegi yok. Toplam {len(all_requests)} istek. Il dropdown: {il_dropdown_info}"

    log_to_supabase("meb_debug_network_ilce_api", sonuc)

    unique_paths = list(dict.fromkeys(all_requests))[:30]
    log_to_supabase("meb_debug_all_requests_sample", " || ".join(unique_paths))

except Exception as e:
    import traceback
    hata_detay = f"GENEL_HATA: {type(e).__name__}: {str(e)[:300]}\n{traceback.format_exc()[:1000]}"
    print(hata_detay)
    log_to_supabase("meb_debug_network_ilce_api", hata_detay)
    sys.exit(0)  # workflow'u "failure" yapmadan bitir, hata zaten Supabase'e yazildi
