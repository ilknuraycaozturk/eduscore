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

    print("\n=== TEST 3: Arama mekanizmasını bul (form/script taraması) ===")
    homepage_html = resp.text
    # <form> etiketlerini bul
    import re
    forms = re.findall(r'<form[^>]*>', homepage_html)
    print(f"Bulunan <form> sayısı: {len(forms)}")
    for f in forms[:5]:
        print(f"  {f}")

    # 'ara' veya 'search' geçen input/script parçalarını bul
    search_hints = re.findall(r'.{80}(?:search|arama|/api/).{80}', homepage_html, re.IGNORECASE)
    print(f"\n'search/arama/api' geçen {len(search_hints)} parça bulundu (ilk 8):")
    for h in search_hints[:8]:
        print(f"  ...{h}...")

    print("\n=== TEST 4: Bilinen basit lise URL kalıbı (id olmadan arama) ===")
    for path in ["/lise-ara?q=fen", "/liseler?q=fen", "/liseler/ara?q=fen", "/api/liseler?q=fen", "/autocomplete?q=fen"]:
        try:
            r = session.get(BASE_URL + path, timeout=10)
            print(f"{path} -> {r.status_code} ({len(r.text)} karakter)")
            if r.status_code == 200 and len(r.text) < 5000:
                print(f"    İçerik: {r.text[:300]}")
        except Exception as e:
            print(f"{path} -> HATA: {e}")


    print("\n=== TEST 5: /liseler?q= endpoint'i gerçekten filtreleme yapıyor mu? ===")
    r1 = session.get(BASE_URL + "/liseler?q=Adana+Fen+Lisesi", timeout=15)
    print(f"'Adana Fen Lisesi' araması -> {r1.status_code}, {len(r1.text)} karakter")
    if "adana-fen-lisesi" in r1.text.lower() or "adana fen lisesi" in r1.text.lower():
        print("✅ Sonuçlarda 'Adana Fen Lisesi' geçiyor - GERÇEK FİLTRELEME ÇALIŞIYOR")
    else:
        print("⚠️ Sonuçlarda okul adı bulunamadı")

    # Sonuç linklerini regex ile çıkar
    import re
    links = re.findall(r'href="(/lise/[a-z0-9\-]+--\d+/?[a-z0-9\-]*/?)"', r1.text, re.IGNORECASE)
    links = list(dict.fromkeys(links))  # tekrarları temizle, sırayı koru
    print(f"\nBulunan lise linkleri ({len(links)} adet, ilk 10):")
    for l in links[:10]:
        print(f"  {l}")

    print("\n=== TEST 6: Farklı bir okul adıyla tekrar dene ===")
    r2 = session.get(BASE_URL + "/liseler?q=Sungurlu+Fen+Lisesi", timeout=15)
    links2 = re.findall(r'href="(/lise/[a-z0-9\-]+--\d+/?[a-z0-9\-]*/?)"', r2.text, re.IGNORECASE)
    links2 = list(dict.fromkeys(links2))
    print(f"'Sungurlu Fen Lisesi' araması -> {len(links2)} link bulundu (ilk 5):")
    for l in links2[:5]:
        print(f"  {l}")


    print("\n=== TEST 7: /liseler sayfasının ham içeriğini incele ===")
    print(f"Tam URL denemesi: {r1.url}")
    # <a href kalıplarının TÜMÜNÜ (regex'i genişletiyoruz)
    all_hrefs = re.findall(r'href="([^"]+)"', r1.text)
    print(f"Toplam href sayısı: {len(all_hrefs)}")
    lise_like = [h for h in all_hrefs if 'lise' in h.lower()]
    print(f"'lise' içeren href sayısı: {len(lise_like)} (ilk 15):")
    for h in lise_like[:15]:
        print(f"  {h}")
    # fetch/axios/api çağrılarını script içinde ara
    api_calls = re.findall(r'(?:fetch|axios\.get|\.get\()\s*\(?["\']([^"\']+)["\']', r1.text)
    print(f"\nJS içinde bulunan fetch/api çağrıları ({len(api_calls)} adet):")
    for a in api_calls[:10]:
        print(f"  {a}")
    # Ortada 1000 karakterlik bir dilim göster (body içeriği görmek için)
    body_idx = r1.text.find('<body')
    print(f"\n<body> içeriğinden 1500 karakterlik örnek:\n{r1.text[body_idx:body_idx+1500]}")


if __name__ == "__main__":
    main()
