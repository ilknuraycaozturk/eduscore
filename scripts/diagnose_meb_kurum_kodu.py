"""
diagnose_meb_kurum_kodu.py
============================
TEK SEFERLİK TANI SCRIPT'İ - production pipeline'ının parçası DEĞİL.

AMAÇ: scrape_meb_schools.py, MEB'in okul tablosunda SADECE ilk 2 hücreyi
(isim + bilgi) okuyor. Tabloda kurum kodu içeren gizli bir 3. veya 4. sütun
olup olmadığını kontrol etmek için gerçek sayfanın TAM HTML yapısını
konsola yazdırır. HİÇBİR ŞEY KAYDETMEZ, sadece keşif amaçlıdır.
"""
from playwright.sync_api import sync_playwright

MEB_URL = "https://www.meb.gov.tr/baglantilar/okullar/index.php"


def main():
    url = f"{MEB_URL}?ILKODU=6&ILCEKODU=27"  # Ankara / Etimesgut
    print(f"Çekiliyor: {url}\n")

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(url, wait_until="networkidle", timeout=30000)

        rows = page.query_selector_all("table tr")
        print(f"Toplam satır sayısı: {len(rows)}\n")

        print("=== İlk 5 satırın TAM hücre yapısı ===")
        for i, row in enumerate(rows[:5]):
            cells = row.query_selector_all("td")
            print(f"\n--- Satır {i} ({len(cells)} hücre) ---")
            for j, cell in enumerate(cells):
                text = cell.inner_text().strip()
                links = cell.query_selector_all("a")
                link_info = ""
                for link_el in links:
                    href = link_el.get_attribute("href")
                    link_info += f" [LINK: {href}]"
                print(f"  Hücre {j}: {text!r:60s}{link_info}")

        # Başlık satırı varsa (th etiketleri) onu da göster
        headers = page.query_selector_all("table th")
        if headers:
            print("\n=== Tablo başlıkları (th) ===")
            for h in headers:
                print(f"  {h.inner_text().strip()!r}")

        browser.close()


if __name__ == "__main__":
    main()
