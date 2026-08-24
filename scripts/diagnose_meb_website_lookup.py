"""
diagnose_meb_website_lookup.py
================================
TEK SEFERLİK TANI SCRIPT'İ - production pipeline'ının parçası DEĞİL.

AMAÇ: meb.k12.tr ana sayfasında "Herhangi bir okula ait web sitesi adresi
bulmak için tıklayınız" diye bir link/araç olduğunu web aramasından öğrendik,
ama tam URL'sini bulamadık (bizim ortamımızdan robots.txt engelliyor).
Bu script GitHub Actions'ın kısıtsız ağından sayfayı çekip o linki (ve
sayfadaki diğer ilgili linkleri) konsola yazdırır - HİÇBİR ŞEY KAYDETMEZ,
sadece keşif amaçlıdır.
"""
import requests
from bs4 import BeautifulSoup

USER_AGENT = "EduScor-Diagnostic/1.0 (+destek@eduscor.com; tek seferlik kesif, veri yazmiyor)"


def main():
    url = "https://www.meb.k12.tr/"
    print(f"Çekiliyor: {url}")
    resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=20)
    print(f"HTTP Durum: {resp.status_code}")
    print(f"İçerik uzunluğu: {len(resp.text)} karakter\n")

    soup = BeautifulSoup(resp.text, "html.parser")

    print("=== 'bul' / 'ara' / 'sitesi' geçen tüm linkler ===")
    for a in soup.find_all("a", href=True):
        text = a.get_text(strip=True)
        href = a["href"]
        if any(kw in text.lower() for kw in ["bul", "ara", "sitesi", "adres"]):
            print(f"  METIN: {text!r:60s} -> HREF: {href}")

    print("\n=== Tüm linkler (ilk 40) - yukarıda bulunamazsa manuel incelemek için ===")
    for a in soup.find_all("a", href=True)[:40]:
        print(f"  {a.get_text(strip=True)[:50]!r:52s} -> {a['href']}")

    print("\n=== Sayfada 'form' var mı (arama kutusu olabilir) ===")
    for form in soup.find_all("form"):
        print(f"  FORM action={form.get('action')!r} method={form.get('method')!r}")
        for inp in form.find_all(["input", "select"]):
            print(f"     input: name={inp.get('name')!r} type={inp.get('type')!r}")


if __name__ == "__main__":
    main()
