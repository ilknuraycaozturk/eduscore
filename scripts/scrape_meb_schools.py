"""
scrape_meb_schools.py
======================
EduScor — Aksiyon 1.1: MEB Resmi Veri Çekimi (Seeding)

MEB'in "Okullar ve Diğer Kurumlar" sayfası (www.meb.gov.tr/baglantilar/okullar/)
tablo verisini AJAX ile sonradan yüklüyor; düz HTTP fetch bu yüzden çalışmıyor.
Bu script Playwright (headless Chromium) kullanarak sayfayı gerçekten render eder,
tablo dolduktan sonra satırları okur.

Kullanım:
    python scrape_meb_schools.py --il-kodu 6 --ilce-kodu 27 --output data/etimesgut_raw.json

İl/ilçe kodları için: https://www.meb.gov.tr/baglantilar/okullar/index.php
(il kodu plaka koduyla aynıdır; Ankara = 6)

NOT: Bu script meb.gov.tr'ye canlı erişim gerektirir. Geliştirme sandbox'ında
(Claude'un çalıştığı ortamda) bu domain'e ağ erişimi yok — bu yüzden test
GitHub Actions üzerinde ya da yerel makinenizde yapılmalıdır.
"""

import argparse
import json
import sys
import time
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("Playwright kurulu değil. Kurulum için: pip install playwright && playwright install chromium")
    sys.exit(1)


MEB_URL = "https://www.meb.gov.tr/baglantilar/okullar/index.php"


def scrape_okullar(il_kodu: str, ilce_kodu: str | None = None, timeout_ms: int = 20000) -> list[dict]:
    """MEB okullar tablosunu render edip satırları döndürür."""
    url = f"{MEB_URL}?ILKODU={il_kodu}"
    if ilce_kodu:
        url += f"&ILCEKODU={ilce_kodu}"

    results: list[dict] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, wait_until="networkidle", timeout=timeout_ms)

        # Tablo AJAX ile dolduğu için satırların görünmesini bekle
        try:
            page.wait_for_selector("table tr td", timeout=timeout_ms)
        except Exception:
            print(f"UYARI: {url} için tablo satırı bulunamadı (boş sonuç ya da sayfa yapısı değişmiş olabilir).")
            browser.close()
            return results

        # Sayfa sayısı için güvenli bir üst sınır (sonsuz döngüye girmeyi önler)
        max_pages = 200
        page_num = 1

        while page_num <= max_pages:
            _scrape_current_page(page, il_kodu, ilce_kodu, results)
            print(f"  Sayfa {page_num}: toplam {len(results)} kayıt (kümülatif).")

            next_clicked = _go_to_next_page(page, timeout_ms)
            if not next_clicked:
                break
            page_num += 1

        browser.close()

    return results


def _scrape_current_page(page, il_kodu: str, ilce_kodu, results: list[dict]) -> None:
    """Şu an ekranda görünen tablo satırlarını okuyup 'results' listesine ekler."""
    rows = page.query_selector_all("table tr")
    for row in rows:
        cells = row.query_selector_all("td")
        if len(cells) < 2:
            continue  # başlık satırı ya da boş satır

        name = cells[0].inner_text().strip()
        info = cells[1].inner_text().strip() if len(cells) > 1 else ""
        if not info or info == name:
            info = None

        row_html = row.inner_html()
        lat, lng = _extract_coords(row_html)

        if not name:
            continue

        results.append({
            "raw_name": name,
            "raw_info": info,
            "lat": lat,
            "lng": lng,
            "il_kodu": il_kodu,
            "ilce_kodu": ilce_kodu,
        })


def _go_to_next_page(page, timeout_ms: int) -> bool:
    """'Sonraki sayfa' kontrolünü bulup tıklar. Bulunamazsa/tıklanamazsa False döner.
    NOT: MEB sayfasının tam pagination yapısı bu ortamdan doğrudan görülemediği
    için burada birkaç YAYGIN desen deneniyor (DataTables tarzı 'next' butonu,
    numaralı sayfa linkleri, '>' / 'Sonraki' metinli linkler). Gerçek yapı
    farklıysa, GitHub Actions loglarına bakıp seçicileri güncellememiz gerekebilir.
    """
    candidate_selectors = [
        "a.paginate_button.next:not(.disabled)",
        "li.paginate_button.next:not(.disabled) a",
        "a[rel='next']",
        "a:has-text('Sonraki')",
        "a:has-text('İleri')",
        "button:has-text('Sonraki')",
    ]

    for selector in candidate_selectors:
        try:
            el = page.query_selector(selector)
            if el and el.is_visible() and el.is_enabled():
                # Tıklamadan önceki ilk satırın metnini al; tıkladıktan sonra
                # değişip değişmediğine bakarak tablo gerçekten güncellendi mi
                # kontrol edeceğiz (AJAX yüklenmesini beklemek için).
                first_row_before = page.query_selector("table tr td")
                before_text = first_row_before.inner_text() if first_row_before else ""

                el.click()
                page.wait_for_timeout(500)
                try:
                    page.wait_for_function(
                        """(oldText) => {
                            const cell = document.querySelector('table tr td');
                            return cell && cell.innerText !== oldText;
                        }""",
                        arg=before_text,
                        timeout=timeout_ms,
                    )
                except Exception:
                    pass  # tablo değişmediyse muhtemelen son sayfadaydık

                return True
        except Exception:
            continue

    return False


def _extract_coords(text: str) -> tuple[float | None, float | None]:
    """href/onclick içinden basit bir regex ile lat,lng çıkarmayı dener."""
    import re
    match = re.search(r"(-?\d{1,3}\.\d+)\s*,\s*(-?\d{1,3}\.\d+)", text)
    if match:
        return float(match.group(1)), float(match.group(2))
    return None, None


def discover_ilceler(il_kodu: str, timeout_ms: int = 20000) -> list[dict]:
    """Verilen il için MEB sayfasındaki ilçe seçim kutusunu (select) bulup
    tüm ilçe kodu/adı çiftlerini döndürür.

    ÖNEMLİ TEKNİK DETAY: Sayfa sadece ?ILKODU=X ile açıldığında ilçe kutusu
    DOM'da hiç oluşmuyor - MEB'in JS'i ilçe listesini yalnızca il seçim
    kutusunun (name='ILADI') 'onChange' olayı GERÇEKTEN tetiklendiğinde AJAX
    ile getiriyor. URL parametresiyle önceden seçili gelmesi bu olayı
    tetiklemiyor. Bu yüzden Playwright ile il kutusunu bilerek tekrar
    seçiyoruz (aynı değeri seçsek de onChange olayını tetikler) - bunu
    canlı ortamda gözlemleyip düzelttik.
    """
    url = f"{MEB_URL}?ILKODU={il_kodu}"
    ilceler: list[dict] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, wait_until="networkidle", timeout=timeout_ms)
        page.wait_for_timeout(1000)

        # İl seçim kutusunu bul ve değerini "tekrar seç" - bu onChange'i tetikler
        il_select = page.query_selector("select[name='ILADI']") or page.query_selector("select#ILADI")
        if not il_select:
            print("HATA: İl seçim kutusu (ILADI) bulunamadı.")
            browser.close()
            return ilceler

        before_count = len(page.query_selector_all("select"))
        try:
            il_select.select_option(value=str(il_kodu))
        except Exception as e:
            print(f"UYARI: İl kutusu seçilirken hata: {e} (value ile olmadıysa label ile deneniyor)")

        # onChange sonrası AJAX'in ilçe kutusunu DOM'a eklemesini/doldurmasını bekle
        try:
            page.wait_for_function(
                "(before) => document.querySelectorAll('select').length > before",
                arg=before_count, timeout=timeout_ms,
            )
        except Exception:
            print("UYARI: Yeni bir <select> DOM'a eklenmedi (belki zaten vardı, devam ediliyor).")
        page.wait_for_timeout(1500)

        all_selects = page.query_selector_all("select")
        print(f"Sayfada {len(all_selects)} adet <select> bulundu (il kutusu tetiklendikten sonra)...")

        ilce_select = None
        for sel in all_selects:
            name_attr = (sel.get_attribute("name") or "").upper()
            id_attr = (sel.get_attribute("id") or "").upper()
            print(f"  <select> name='{name_attr}' id='{id_attr}'")
            if sel == il_select:
                continue
            if "ILCE" in name_attr or "ILCE" in id_attr or "ILÇE" in name_attr:
                ilce_select = sel
                break

        # Hiçbiri 'ILCE' içermiyorsa, il kutusu dışındaki İLK yeni/farklı select'i dene
        if not ilce_select:
            for sel in all_selects:
                if sel != il_select:
                    name_attr = (sel.get_attribute("name") or "")
                    if "LENGTH" not in name_attr.upper():  # sayfalama uzunluk kutusunu ele
                        ilce_select = sel
                        print(f"Not: 'ILCE' içeren isim bulunamadı, en olası aday deneniyor: name='{name_attr}'")
                        break

        if not ilce_select:
            print("UYARI: İlçe seçim kutusu bulunamadı. Sayfa yapısı beklenenden farklı olabilir.")
            browser.close()
            return ilceler

        options = ilce_select.query_selector_all("option")
        for opt in options:
            value = (opt.get_attribute("value") or "").strip()
            label = opt.inner_text().strip()
            if value and value != "0":
                ilceler.append({"kod": value, "ad": label})

        browser.close()

    print(f"{len(ilceler)} ilçe bulundu: {[i['ad'] for i in ilceler]}")
    return ilceler


def main():
    parser = argparse.ArgumentParser(description="MEB okul listesini çeker (Playwright).")
    parser.add_argument("--il-kodu", required=True, help="İl plaka kodu (Ankara=6)")
    parser.add_argument("--ilce-kodu", default=None, help="İlçe kodu (opsiyonel, --all-ilceler ile birlikte kullanılmaz)")
    parser.add_argument("--all-ilceler", action="store_true",
                         help="Verilirse önce ildeki TÜM ilçeleri keşfedip her biri için ayrı ayrı veri çeker ve birleştirir.")
    parser.add_argument("--output", default="data/meb_raw.json", help="Çıktı JSON dosyası")
    args = parser.parse_args()

    if args.all_ilceler:
        print(f"Tüm ilçeler modu: il={args.il_kodu}")
        ilceler = discover_ilceler(args.il_kodu)
        if not ilceler:
            print("HATA: Hiç ilçe bulunamadı, çıkılıyor.")
            sys.exit(1)

        all_data: list[dict] = []
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        for i, ilce in enumerate(ilceler, 1):
            print(f"\n=== [{i}/{len(ilceler)}] İlçe: {ilce['ad']} (kod={ilce['kod']}) ===")
            data = scrape_okullar(args.il_kodu, ilce["kod"])
            for row in data:
                row["ilce_ad"] = ilce["ad"]  # ilçe adını da ekleyelim, sonraki adım için kolaylık
            all_data.extend(data)
            print(f"  Bu ilçede {len(data)} kayıt, toplamda şimdiye kadar {len(all_data)} kayıt.")

            # Ara kayıt: 25 ilçe saatler sürebileceği için, yarıda kesilirse
            # (timeout, hata vb.) o ana kadarki veri kaybolmasın diye her
            # ilçeden sonra dosyayı güncelliyoruz.
            out_path.write_text(json.dumps(all_data, ensure_ascii=False, indent=2), encoding="utf-8")

        print(f"\nTOPLAM {len(all_data)} kayıt ({len(ilceler)} ilçe) -> {out_path}")
        return

    print(f"MEB verisi çekiliyor: il={args.il_kodu} ilçe={args.ilce_kodu}")
    data = scrape_okullar(args.il_kodu, args.ilce_kodu)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"{len(data)} kayıt bulundu -> {out_path}")


if __name__ == "__main__":
    main()
