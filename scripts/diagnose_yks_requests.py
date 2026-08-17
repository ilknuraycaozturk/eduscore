"""
diagnose_yks_requests.py
==========================
sinavizcisi.com'a Playwright (tam tarayıcı) yerine basit 'requests'
kütüphanesiyle erişimi test eden teşhis script'i. Amaç: Cloudflare'in
bizi Playwright/headless-browser parmak izinden mi, yoksa sadece IP
itibarından mı engellediğini anlamak.
"""
import requests

BASE_URL = "https://sinavizcisi.com"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
}


def main():
    session = requests.Session()
    session.headers.update(HEADERS)

    print("=== TEST 1: Ana sayfa ===")
    resp = session.get(BASE_URL + "/", timeout=20)
    print(f"Durum kodu: {resp.status_code}")
    print(f"İçerik uzunluğu: {len(resp.text)} karakter")
    print(f"İlk 500 karakter:\n{resp.text[:500]}")
    if "cloudflare" in resp.text.lower() or "cf-browser-verification" in resp.text.lower() or "checking your browser" in resp.text.lower():
        print("⚠️ CLOUDFLARE CHALLENGE SAYFASI TESPİT EDİLDİ")
    else:
        print("✅ Cloudflare challenge sayfası görünmüyor")

    print("\n=== TEST 2: Bilinen bir okul sayfası (arama sonuçlarından) ===")
    test_url = f"{BASE_URL}/lise/adana-fen-lisesi--11911190/universite-yerlesmeleri-2025/"
    resp2 = session.get(test_url, timeout=20)
    print(f"URL: {test_url}")
    print(f"Durum kodu: {resp2.status_code}")
    print(f"İçerik uzunluğu: {len(resp2.text)} karakter")
    if resp2.status_code == 200 and "yerleş" in resp2.text.lower():
        print("✅ Okul sayfası BAŞARIYLA çekildi, veri içeriyor gibi görünüyor")
    else:
        print("⚠️ Beklenmeyen sonuç")
    print(f"İlk 800 karakter:\n{resp2.text[:800]}")

    print("\n=== TEST 3: Arama endpoint'i denemesi ===")
    for path in ["/arama?q=fen+lisesi", "/search?q=fen+lisesi", "/api/search?q=fen"]:
        try:
            r = session.get(BASE_URL + path, timeout=10)
            print(f"{path} -> {r.status_code} ({len(r.text)} karakter)")
        except Exception as e:
            print(f"{path} -> HATA: {e}")


if __name__ == "__main__":
    main()
