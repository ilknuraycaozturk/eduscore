"""
sinavizcisi.com sitesinden okul bazında YKS/üniversite yerleştirme başarı
verisi çeker (İlk Senede Yerleşme Başarısı %, Toplam Yerleşen sayısı vb.).

BU BİR TEŞHİS SCRIPT'İDİR. Sitenin arama kutusunun (autocomplete) gerçek
DOM yapısını göremediğimiz için, ilk aşamada birkaç örnek okul adı ile
deneyip sonucu loglayacağız - bulunan yapıya göre asıl script'i yazacağız.

Kullanım:
    python scrape_yks_sinavizcisi.py --isimler "Ankara Fen Lisesi" "Ankara Lisesi"
"""
import argparse
import json
import re
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE_URL = "https://sinavizcisi.com"


def search_and_find_url(page, okul_adi: str, timeout_ms: int = 15000) -> str | None:
    """Arama kutusuna okul adını yazar, açılan otomatik tamamlama sonuçlarını
    loglar ve ilk sonucun linkini döndürür (bulabilirse)."""
    page.goto(f"{BASE_URL}/", wait_until="networkidle", timeout=timeout_ms)
    page.wait_for_timeout(1000)

    # TEŞHİS: Sayfadaki tüm <input> elemanlarını logla - arama kutusunu bulmak için
    inputs = page.query_selector_all("input")
    print(f"  TEŞHİS: Sayfada {len(inputs)} <input> bulundu:")
    search_input = None
    for inp in inputs:
        placeholder = inp.get_attribute("placeholder") or ""
        itype = inp.get_attribute("type") or ""
        name = inp.get_attribute("name") or ""
        print(f"    placeholder='{placeholder}' type='{itype}' name='{name}'")
        if not search_input and ("ara" in placeholder.lower() or "search" in placeholder.lower() or "lise" in placeholder.lower()):
            search_input = inp

    if not search_input and inputs:
        search_input = inputs[0]  # en olası aday olarak ilkini dene

    if not search_input:
        print("  HATA: Hiçbir arama kutusu bulunamadı.")
        return None

    search_input.click()
    search_input.fill(okul_adi)
    page.wait_for_timeout(1500)  # autocomplete sonuçlarının yüklenmesini bekle

    # TEŞHİS: Aramadan sonra sayfada beliren linkleri (özellikle /lise/ içerenleri) logla
    lise_links = page.query_selector_all("a[href*='/lise/']")
    print(f"  TEŞHİS: '{okul_adi}' araması sonrası {len(lise_links)} '/lise/' linki bulundu:")
    for link in lise_links[:10]:
        href = link.get_attribute("href") or ""
        text = link.inner_text().strip()[:80]
        print(f"    href='{href}' metin='{text}'")

    if lise_links:
        return lise_links[0].get_attribute("href")
    return None


def extract_stats(page, url: str, timeout_ms: int = 15000) -> dict:
    """Bir okulun ana sayfasına gidip başlıktaki özet istatistikleri çeker."""
    full_url = url if url.startswith("http") else f"{BASE_URL}{url}"
    page.goto(full_url, wait_until="networkidle", timeout=timeout_ms)
    page.wait_for_timeout(1000)

    body_text = page.inner_text("body")

    # "807 Toplam Yerleşen", "28.7% İlk Senede Yerleşme Başarısı" gibi kalıpları ara
    toplam_match = re.search(r"(\d+)\s*Toplam Yerleşen", body_text)
    ilk_sene_match = re.search(r"([\d.,]+)%\s*İlk Senede Yerleşme Başarısı", body_text)
    uni_match = re.search(r"(\d+)\s*Farklı Üniversite", body_text)

    result = {
        "toplam_yerlesen": int(toplam_match.group(1)) if toplam_match else None,
        "ilk_sene_basari_yuzde": float(ilk_sene_match.group(1).replace(",", ".")) if ilk_sene_match else None,
        "farkli_universite": int(uni_match.group(1)) if uni_match else None,
        "url": full_url,
    }
    print(f"  TEŞHİS: Çıkarılan istatistikler: {result}")
    if not any([toplam_match, ilk_sene_match, uni_match]):
        print(f"  UYARI: Hiçbir istatistik bulunamadı. Sayfa metninin ilk 1000 karakteri:")
        print(f"    {body_text[:1000]}")

    return result


def main():
    parser = argparse.ArgumentParser(description="sinavizcisi.com'dan YKS verisi çeker (teşhis modu).")
    parser.add_argument("--isimler", nargs="+", required=True, help="Denenecek okul adları")
    parser.add_argument("--output", default="data/yks_teshis.json")
    args = parser.parse_args()

    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        for okul_adi in args.isimler:
            print(f"\n=== '{okul_adi}' aranıyor ===")
            try:
                url = search_and_find_url(page, okul_adi)
                if url:
                    stats = extract_stats(page, url)
                    stats["okul_adi"] = okul_adi
                    results.append(stats)
                else:
                    print(f"  '{okul_adi}' için URL bulunamadı.")
            except Exception as e:
                print(f"  HATA: {e}")

        browser.close()

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nTOPLAM {len(results)} sonuç -> {out_path}")


if __name__ == "__main__":
    main()
