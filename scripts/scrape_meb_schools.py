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
import os
import re
import sys
import time
import urllib.request
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("Playwright kurulu değil. Kurulum için: pip install playwright && playwright install chromium")
    sys.exit(1)


MEB_URL = "https://www.meb.gov.tr/baglantilar/okullar/index.php"


def _log_progress_to_supabase(message: str, key: str = "meb_debug_live") -> None:
    """TEŞHİS AMAÇLI: SUPABASE_URL/SUPABASE_SERVICE_ROLE_KEY ortam değişkenleri
    varsa, scrape_progress tablosuna 'meb_debug_live' anahtarıyla anlık durumu
    yazar. GitHub Actions log indirme bazı ortamlarda ağ kısıtına takıldığı için
    (blob storage host'una erişilemiyor), ilerlemeyi doğrudan Supabase'den
    sorgulayarak görebilmek için eklendi. Hata olursa sessizce geçilir -
    ana scraping akışını asla bozmamalı.

    EK TEŞHİS: Supabase'e yazma BAŞARISIZ olursa, hatanın kendisini de
    data/debug_log.txt dosyasına (append) yazıyoruz - bu dosya workflow'da
    artifact olarak yükleniyor, böylece Supabase'e neden ulaşılamadığını
    (env eksik mi, ağ hatası mı, HTTP hata kodu mu) görebiliriz.
    """
    def _write_local_debug(text: str) -> None:
        try:
            Path("data").mkdir(parents=True, exist_ok=True)
            with open("data/debug_log.txt", "a", encoding="utf-8") as f:
                f.write(text + "\n")
        except Exception:
            pass

    _write_local_debug(f"[{key}] {message}")

    url = os.environ.get("SUPABASE_URL")
    key_val = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key_val:
        _write_local_debug(f"SUPABASE_LOG_ATLANDI: url_var={bool(url)} key_var={bool(key_val)}")
        return
    try:
        payload = json.dumps({"key": key, "value": message}).encode("utf-8")
        req = urllib.request.Request(
            f"{url}/rest/v1/scrape_progress?on_conflict=key",
            data=payload,
            method="POST",
            headers={
                "apikey": key_val,
                "Authorization": f"Bearer {key_val}",
                "Content-Type": "application/json",
                "Prefer": "resolution=merge-duplicates,return=minimal",
            },
        )
        resp = urllib.request.urlopen(req, timeout=5)
        _write_local_debug(f"SUPABASE_LOG_BASARILI: http_status={resp.status}")
    except Exception as e:
        _write_local_debug(f"SUPABASE_LOG_HATASI: {type(e).__name__}: {str(e)[:300]}")


def scrape_okullar(il_kodu: str, ilce_kodu: str | None = None, timeout_ms: int = 20000) -> list[dict]:
    """MEB okullar tablosunu render edip satırları döndürür."""
    url = f"{MEB_URL}?ILKODU={il_kodu}"
    if ilce_kodu:
        url += f"&ILCEKODU={ilce_kodu}"

    results: list[dict] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            page.goto(url, wait_until="networkidle", timeout=timeout_ms)
        except Exception as e:
            _log_progress_to_supabase(f"il={il_kodu} ilce={ilce_kodu} | DURDU: goto_hatasi err={str(e)[:150]}")
            print(f"HATA: Sayfa yuklenemedi ({url}): {e}")
            browser.close()
            return results

        # Tablo AJAX ile dolduğu için satırların görünmesini bekle
        try:
            page.wait_for_selector("table tr td", timeout=timeout_ms)
        except Exception:
            print(f"UYARI: {url} için tablo satırı bulunamadı (boş sonuç ya da sayfa yapısı değişmiş olabilir).")
            browser.close()
            return results

        # Sayfa başına kayıt sayısını mümkünse büyütmeyi dene (100) - bu, tıklanacak
        # 'sonraki sayfa' sayısını ~4'e katına düşürüp scraping'i hızlandırır.
        # Bulunamazsa/başarısız olursa sessizce varsayılan (genelde 25) ile devam eder.
        try:
            length_select = page.query_selector("select[name*='LENGTH' i]") or page.query_selector("select[name*='length' i]")
            if length_select:
                for val in ("100", "-1"):
                    try:
                        length_select.select_option(value=val)
                        page.wait_for_timeout(1000)
                        break
                    except Exception:
                        continue
                print(f"TEŞHİS: Sayfa boyutu kutusunun son değeri: '{length_select.input_value()}'")
        except Exception as e:
            print(f"TEŞHİS: Sayfa boyutu kutusu ayarlanamadı: {e}")

        # TEŞHİS: DataTables genelde "X ile Y arası, toplam Z kayıt gösteriliyor"
        # gibi bir bilgi metni gösterir (genelde id='...INFO' ya da class
        # 'dataTables_info'). Bu, MEB'in kendisinin toplamda kaç kayıt
        # olduğunu düşündüğünü kesin olarak gösterir.
        try:
            info_el = (page.query_selector("[id*='_INFO' i]")
                       or page.query_selector(".dataTables_info")
                       or page.query_selector("[class*='dataTables_info' i]"))
            if info_el:
                print(f"TEŞHİS: Toplam kayıt bilgi metni: '{info_el.inner_text().strip()}'")
            else:
                print("TEŞHİS: Toplam kayıt bilgi metni bulunamadı.")
        except Exception as e:
            print(f"TEŞHİS: Toplam kayıt bilgisi okunamadı: {e}")

        # TEŞHİS: Sayfalama kontrollerinin gerçek yapısını logla - böylece
        # _go_to_next_page() doğru elemanı bulamıyorsa neden olduğunu görebiliriz.
        # ÖNEMLİ: 'nav a' kaldırıldı - bu sitenin ÜST MENÜSÜNÜ (Bakan, Mevzuat vb.)
        # yakalıyordu, gerçek sayfalama ile alakasızdı.
        try:
            pag_candidates = page.query_selector_all(
                "a.paginate_button, li.paginate_button, [class*='pagin' i] a, "
                "[class*='pagin' i] button, .dataTables_paginate a, .dataTables_paginate button"
            )
            print(f"TEŞHİS: Sayfalama alanında {len(pag_candidates)} olası eleman bulundu:")
            for el in pag_candidates[:15]:
                try:
                    txt = el.inner_text().strip()
                    cls = el.get_attribute("class") or ""
                    print(f"  metin='{txt}' class='{cls}'")
                except Exception:
                    pass
        except Exception as e:
            print(f"TEŞHİS: Sayfalama alanı taranamadı: {e}")

        # Sayfa sayısı için güvenli bir üst sınır (sonsuz döngüye girmeyi önler)
        max_pages = 200
        page_num = 1

        while page_num <= max_pages:
            _scrape_current_page(page, il_kodu, ilce_kodu, results)
            progress_msg = f"il={il_kodu} ilce={ilce_kodu} sayfa={page_num} kumulatif_kayit={len(results)}"
            print(f"  Sayfa {page_num}: toplam {len(results)} kayıt (kümülatif).")
            _log_progress_to_supabase(progress_msg)

            next_clicked = _go_to_next_page(page, timeout_ms)
            if not next_clicked:
                _log_progress_to_supabase(progress_msg + " | DURDU: sonraki_sayfa_bulunamadi")
                break
            page_num += 1

        if page_num > max_pages:
            _log_progress_to_supabase(f"il={il_kodu} ilce={ilce_kodu} | DURDU: max_pages({max_pages})_asildi kayit={len(results)}")

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

        # Okul adı genelde kendi resmi web sitesine (X.meb.k12.tr) link veriyor -
        # önceden bu hiç yakalanmıyordu, sadece metin alınıyordu.
        website = None
        for cell in cells[:2]:
            link_el = cell.query_selector("a")
            if link_el:
                href = link_el.get_attribute("href")
                if href and ("meb.k12.tr" in href or href.startswith("http")):
                    website = href
                    break

        # ÖNEMLİ (23-24 Ağustos 2026'da keşfedildi): "Bilgi" hücresindeki
        # (cells[1]) link, görünürde boş metin taşısa da href'inde
        # /meb_iys_dosyalar/{il}/{ilce}/{KURUM_KODU}/okulumuz_hakkinda.html
        # deseniyle GERÇEK MEB kurum kodunu içeriyor. Bu kod hem
        # kurum_kodu@meb.k12.tr e-posta kalıbını üretmek için hem de
        # kurumu MEBBİS ile eşleştirmek için kullanılabilir.
        meb_kurum_kodu = None
        if len(cells) > 1:
            info_link = cells[1].query_selector("a")
            if info_link:
                info_href = info_link.get_attribute("href") or ""
                m = re.search(r"/meb_iys_dosyalar/\d+/\d+/(\d+)/", info_href)
                if m:
                    meb_kurum_kodu = m.group(1)

        row_html = row.inner_html()
        lat, lng = _extract_coords(row_html)

        if not name:
            continue

        results.append({
            "raw_name": name,
            "raw_info": info,
            "website": website,
            "meb_kurum_kodu": meb_kurum_kodu,
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

    print("TEŞHİS: _go_to_next_page hiçbir aday seçiciyle eşleşen tıklanabilir eleman bulamadı.")

    # DETAYLI TEŞHİS: Bu anda DOM'daki TÜM olası sayfalama elemanlarının
    # gerçek durumunu (text/class/visible/enabled) yakala - böylece "Sonraki"
    # butonunun bu noktada tam olarak neden eşleşmediğini/tıklanamadığını
    # (disabled mı, DOM'dan tamamen mi kayboldu, farklı bir class mı aldı) görebiliriz.
    try:
        all_pag = page.query_selector_all(
            "a.paginate_button, li.paginate_button, [class*='pagin' i] a, "
            "[class*='pagin' i] button, .dataTables_paginate a, .dataTables_paginate button, "
            "[class*='dt-paging' i]"
        )
        detay = []
        for el in all_pag[:20]:
            try:
                detay.append(f"text='{el.inner_text().strip()}' class='{el.get_attribute('class') or ''}' "
                              f"visible={el.is_visible()} enabled={el.is_enabled()}")
            except Exception:
                pass
        detay_str = " || ".join(detay) if detay else "HICBIR_PAGINATION_ELEMANI_YOK"
        _log_progress_to_supabase(f"NEXT_PAGE_DETAY: {detay_str}"[:2000], key="meb_debug_next_page_detay")
    except Exception as e:
        _log_progress_to_supabase(f"NEXT_PAGE_DETAY_HATASI: {str(e)[:200]}")

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

        il_select_name = (il_select.get_attribute("name") or "").upper()
        il_select_id = (il_select.get_attribute("id") or "").upper()

        ilce_select = None
        for sel in all_selects:
            name_attr = (sel.get_attribute("name") or "").upper()
            id_attr = (sel.get_attribute("id") or "").upper()
            print(f"  <select> name='{name_attr}' id='{id_attr}'")
            # ÖNEMLİ: Playwright ElementHandle'ları Python '==' ile karşılaştırmak
            # DOM eşitliğini DEĞİL nesne referans eşitliğini kontrol eder - bu da
            # aynı elemana işaret etseler bile hep 'eşit değil' çıkmasına, ve il
            # kutusunun (ILADI) kendisinin yanlışlıkla ilçe kutusu sanılmasına
            # yol açıyordu. Bunun yerine name/id STRING'ini karşılaştırıyoruz.
            if name_attr == il_select_name and id_attr == il_select_id:
                continue
            if "ILCE" in name_attr or "ILCE" in id_attr or "ILÇE" in name_attr:
                ilce_select = sel
                break

        # Hiçbiri 'ILCE' içermiyorsa, il kutusu dışındaki İLK yeni/farklı select'i dene
        if not ilce_select:
            for sel in all_selects:
                name_attr = (sel.get_attribute("name") or "").upper()
                id_attr = (sel.get_attribute("id") or "").upper()
                if name_attr == il_select_name and id_attr == il_select_id:
                    continue
                if "LENGTH" not in name_attr:  # sayfalama uzunluk kutusunu ele
                    ilce_select = sel
                    print(f"Not: 'ILCE' içeren isim bulunamadı, en olası aday deneniyor: name='{name_attr}'")
                    break

        if not ilce_select:
            print("UYARI: İlçe seçim kutusu bulunamadı. Sayfa yapısı beklenenden farklı olabilir.")
            browser.close()
            return ilceler

        # GÜVENLİK KONTROLÜ: Yanlışlıkla il kutusunu tekrar seçmediğimizden emin
        # olalım - eğer bulunan kutunun name/id'si il kutusuyla AYNIYSA (yukarıdaki
        # karşılaştırma bir şekilde atlanmışsa) ya da seçenek sayısı 70-85 arası
        # gibi "81 il" sayısına çok yakınsa (gerçek bir ilin ilçe sayısı bu kadar
        # olamaz), dur ve hata ver - garbage veri toplamayı önle.
        ilce_name_check = (ilce_select.get_attribute("name") or "").upper()
        ilce_id_check = (ilce_select.get_attribute("id") or "").upper()
        if ilce_name_check == il_select_name and ilce_id_check == il_select_id:
            print("HATA: Bulunan 'ilçe' kutusu il kutusuyla birebir aynı (name/id eşleşiyor). "
                  "Sayfa yapısı beklenmedik - güvenlik için durduruluyor.")
            browser.close()
            return ilceler

        options_preview = ilce_select.query_selector_all("option")
        preview_count = len([o for o in options_preview if (o.get_attribute("value") or "").strip() not in ("", "0")])
        if preview_count >= 70:
            print(f"HATA: Bulunan kutuda {preview_count} seçenek var - bu bir İL listesi gibi görünüyor "
                  f"(Türkiye'de 81 il var), gerçek bir ilin ilçe listesi olamaz. Güvenlik için durduruluyor.")
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
    parser.add_argument("--il-kodu", default=None, help="İl plaka kodu (Ankara=6) - --il-kodu-listesi ile kullanılmaz")
    parser.add_argument("--il-kodu-listesi", default=None,
                         help="Virgülle ayrılmış il plaka kodları (örn. '1,2,3,4,5') - birden fazla ili tek "
                              "çalıştırmada, sırayla ve GÜVENLİ ŞEKİLDE (her il sonrası ara kayıt) çeker. "
                              "6 saatlik iş sınırını aşmamak için genelde 10-15 il/parti önerilir.")
    parser.add_argument("--ilce-kodu", default=None, help="İlçe kodu (opsiyonel, --all-ilceler ile birlikte kullanılmaz)")
    parser.add_argument("--all-ilceler", action="store_true",
                         help="Verilirse önce ildeki TÜM ilçeleri keşfedip her biri için ayrı ayrı veri çeker ve birleştirir.")
    parser.add_argument("--output", default="data/meb_raw.json", help="Çıktı JSON dosyası")
    args = parser.parse_args()

    if not args.il_kodu_listesi and not args.il_kodu:
        parser.error("--il-kodu belirtilmeli (ya da --il-kodu-listesi kullanılmalı).")

    if args.il_kodu_listesi:
        il_kodlari = [k.strip() for k in args.il_kodu_listesi.split(",") if k.strip()]
        all_data = []
        for idx, il_kodu in enumerate(il_kodlari, 1):
            print(f"\n=== [{idx}/{len(il_kodlari)}] İl kodu {il_kodu} ===")
            try:
                il_data = scrape_okullar(il_kodu, None)
                for row in il_data:
                    parts = [p.strip() for p in row["raw_name"].split(" - ", 2)]
                    if len(parts) >= 2:
                        row["il_ad"] = parts[0]
                        row["ilce_ad"] = parts[1]
                        row["raw_name"] = parts[2] if len(parts) > 2 else parts[1]
                    else:
                        row["il_ad"] = None
                        row["ilce_ad"] = None
                all_data.extend(il_data)
                print(f"  İl {il_kodu}: {len(il_data)} kayıt bulundu (toplam: {len(all_data)})")
            except Exception as e:
                print(f"  HATA: İl {il_kodu} çekilemedi -> {e}")

            # ÖNEMLİ: Her il sonrası dosyayı YENİDEN YAZIYORUZ (ara kayıt) - iş
            # zaman aşımına uğrarsa bile şimdiye kadar çekilen veri dosyada
            # kalır ve bir sonraki adımda (artifact yükleme başarısız olsa
            # bile GitHub loglarından) kurtarılabilir.
            out_path = Path(args.output)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(json.dumps(all_data, ensure_ascii=False, indent=2), encoding="utf-8")

        print(f"\nTOPLAM {len(all_data)} kayıt ({len(il_kodlari)} il) -> {args.output}")
        return

    if args.all_ilceler:
        # ÖNEMLİ (Ağustos 2026 güncellemesi): MEB sitesi yeniden tasarlandı ve
        # ilçe seçim kutusunu KALDIRDI - artık bir il için TÜM kurumlar tek bir
        # sayfalı tabloda listeleniyor (isim zaten "İL - İLÇE - Kurum Adı"
        # formatında). Bu yüzden ilçe döngüsüne hiç gerek yok; tek bir çağrı
        # tüm ili (sayfalayarak) çeker, ilçe adını da isimden çıkarıyoruz.
        print(f"Tüm il modu (ilçe filtresi yok - MEB artık desteklemiyor): il={args.il_kodu}")
        all_data = scrape_okullar(args.il_kodu, None)

        for row in all_data:
            parts = [p.strip() for p in row["raw_name"].split(" - ", 2)]
            if len(parts) >= 2:
                row["il_ad"] = parts[0]
                row["ilce_ad"] = parts[1]
                row["raw_name"] = parts[2] if len(parts) > 2 else parts[1]
            else:
                row["il_ad"] = None
                row["ilce_ad"] = None

        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(all_data, ensure_ascii=False, indent=2), encoding="utf-8")

        print(f"\nTOPLAM {len(all_data)} kayıt -> {out_path}")
        return

    print(f"MEB verisi çekiliyor: il={args.il_kodu} ilçe={args.ilce_kodu}")
    data = scrape_okullar(args.il_kodu, args.ilce_kodu)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"{len(data)} kayıt bulundu -> {out_path}")


if __name__ == "__main__":
    main()
