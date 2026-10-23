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


COVERAGE: list[dict] = []
COVERAGE_PATH = Path("data/meb_coverage.json")


def scrape_okullar(il_kodu: str, ilce_kodu: str | None = None, timeout_ms: int = 20000) -> list[dict]:
    """MEB okullar tablosunu render edip satırları döndürür ve her sorgu için
    MEB'in bildirdiği toplam ('N kayıttan') ile çekilen satır sayısını
    data/meb_coverage.json dosyasına kaydeder (kapsama kontrolü için)."""
    # Geçici hatalarda (sayfa yüklenemedi, sayı uyuşmadı) 3 denemeye kadar tekrar
    # dene; her denemede bekleme ve zaman aşımı artar. Son denemenin sonucu kaydedilir.
    for deneme in range(1, 4):
        meta: dict = {"beklenen": None, "durum": "ok"}
        results = _scrape_okullar_raw(il_kodu, ilce_kodu, timeout_ms * deneme, meta)
        tamam = (meta["durum"] == "ok" and meta["beklenen"] == len(results)) or \
                (meta["durum"] == "tablo_bos" and meta["beklenen"] == 0)
        if tamam or deneme == 3:
            break
        print(f"  Yeniden deneniyor ({deneme + 1}/3): il={il_kodu} ilce={ilce_kodu} "
              f"durum={meta['durum']} beklenen={meta['beklenen']} cekilen={len(results)}")
        time.sleep(10 * deneme)
    meta["deneme"] = deneme
    COVERAGE.append({"il_kodu": str(il_kodu), "ilce_kodu": str(ilce_kodu) if ilce_kodu else None,
                     "beklenen": meta["beklenen"], "cekilen": len(results), "durum": meta["durum"],
                     "deneme": meta.get("deneme", 1)})
    try:
        COVERAGE_PATH.parent.mkdir(parents=True, exist_ok=True)
        COVERAGE_PATH.write_text(json.dumps(COVERAGE, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        print(f"UYARI: Kapsama dosyası yazılamadı: {e}")
    return results


def _parse_toplam_kayit(info_metni: str) -> int | None:
    """'151 kayıttan 1 - 100 arasındaki kayıtlar gösteriliyor' -> 151.
    'Kayıt yok' / '0 kayıttan' -> 0. Tanınmazsa None."""
    m = re.search(r"([\d.]+)\s*kay[ıi]ttan", info_metni, re.IGNORECASE)
    if m:
        return int(m.group(1).replace(".", ""))
    if re.search(r"kay[ıi]t\s+yok|bulunamad", info_metni, re.IGNORECASE):
        return 0
    return None


def _scrape_okullar_raw(il_kodu: str, ilce_kodu: str | None, timeout_ms: int, meta: dict) -> list[dict]:
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
            meta["durum"] = "sayfa_yuklenemedi"
            browser.close()
            return results

        # Tablo AJAX ile dolduğu için satırların görünmesini bekle
        try:
            page.wait_for_selector("table tr td", timeout=timeout_ms)
        except Exception:
            print(f"UYARI: {url} için tablo satırı bulunamadı (boş sonuç ya da sayfa yapısı değişmiş olabilir).")
            meta["durum"] = "tablo_bos"
            try:
                info_el = page.query_selector("[id*='_INFO' i]") or page.query_selector(".dataTables_info")
                if info_el:
                    meta["beklenen"] = _parse_toplam_kayit(info_el.inner_text().strip())
            except Exception:
                pass
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
                secili_deger = length_select.input_value()
                print(f"TEŞHİS: Sayfa boyutu kutusunun son değeri: '{secili_deger}'")
                _log_progress_to_supabase(
                    f"il={il_kodu} ilce={ilce_kodu} | length_select_degeri='{secili_deger}'",
                    key="meb_debug_length_select"
                )
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
                info_metni = info_el.inner_text().strip()
                meta["beklenen"] = _parse_toplam_kayit(info_metni)
                print(f"TEŞHİS: Toplam kayıt bilgi metni: '{info_metni}'")
                _log_progress_to_supabase(
                    f"il={il_kodu} ilce={ilce_kodu} | dataTables_info='{info_metni}'",
                    key="meb_debug_datatables_info"
                )
            else:
                print("TEŞHİS: Toplam kayıt bilgi metni bulunamadı.")
                _log_progress_to_supabase(
                    f"il={il_kodu} ilce={ilce_kodu} | dataTables_info=BULUNAMADI",
                    key="meb_debug_datatables_info"
                )
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
            meta["durum"] = "max_pages_asildi"
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

    NOT: Tanı scriptlerinde gözlemlenen gerçek DOM yapısı:
      metin='Sonraki' class='dt-paging-button next'
      metin='Son'     class='dt-paging-button last'
    Seçiciler bu gerçek yapıya göre güncellendi (23-24 Ağustos 2026).
    """
    candidate_selectors = [
        # Gerçek DOM'da gözlemlenen class (tanı script'i çıktısından):
        ".dt-paging-button.next:not(.disabled)",
        "[class*='dt-paging'][class*='next']:not([class*='disabled'])",
        # Fallback: metin tabanlı (en geniş kapsam)
        "a:has-text('Sonraki'):not(.disabled)",
        "button:has-text('Sonraki'):not([disabled])",
        # Eski DataTables stili (yedek olarak kalsın)
        "a.paginate_button.next:not(.disabled)",
        "li.paginate_button.next:not(.disabled) a",
        "a[rel='next']",
    ]

    for selector in candidate_selectors:
        try:
            el = page.query_selector(selector)
            if el and el.is_visible() and el.is_enabled():
                first_row_before = page.query_selector("table tr td")
                before_text = first_row_before.inner_text() if first_row_before else ""

                el.click()
                page.wait_for_timeout(800)
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

                print(f"TEŞHİS: Sonraki sayfa tıklandı, seçici: {selector!r}")
                return True
        except Exception:
            continue

    print("TEŞHİS: _go_to_next_page hiçbir aday seçiciyle eşleşen tıklanabilir eleman bulamadı.")

    # DETAYLI TEŞHİS: Bu anda DOM'daki TÜM olası sayfalama elemanlarının
    # gerçek durumunu (text/class/visible/enabled) yakala
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
    """Verilen il için ilçe kodu/adı listesini döndürür.

    ÖNEMLİ (GÜNCELLEME): MEB sitesi ilçe seçim kutusunu (dropdown) HEM DOM'dan
    HEM arka plan AJAX isteklerinden tamamen kaldırdı (canlı testlerle
    doğrulandı - ne DOM'da <select> var, ne network trafiğinde ilçe içeren
    bir istek var). Bu yüzden ilçe kodları artık MEB'ten DEĞİL, Supabase'deki
    'meb_il_ilce_kodlari' referans tablosundan okunuyor. Bu tablo, üçüncü
    taraf açık kaynaklı bir projeden (ensarkovankaya/meb-okullar, 2017,
    dropdown hâlâ varken toplanmış) alındı ve canlı MEB testiyle doğrulandı
    (Ankara=6, Etimesgut=27 - birebir eşleşiyor). İdari il/ilçe yapısı
    nadiren değiştiği için bu veri hâlâ geçerli kabul ediliyor.
    """
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        print("HATA: SUPABASE_URL/SUPABASE_SERVICE_ROLE_KEY yok, ilçe referans tablosu okunamıyor.")
        return []

    try:
        req = urllib.request.Request(
            f"{url}/rest/v1/meb_il_ilce_kodlari?il_kodu=eq.{il_kodu}&select=ilce_kodu,ilce_adi&order=ilce_kodu",
            headers={"apikey": key, "Authorization": f"Bearer {key}"},
        )
        with urllib.request.urlopen(req, timeout=timeout_ms / 1000) as resp:
            rows = json.loads(resp.read().decode("utf-8"))
        ilceler = [{"kod": str(r["ilce_kodu"]), "ad": r["ilce_adi"]} for r in rows]
        print(f"{len(ilceler)} ilçe bulundu (Supabase referans tablosundan): {[i['ad'] for i in ilceler]}")
        return ilceler
    except Exception as e:
        print(f"HATA: İlçe referans tablosu okunamadı: {type(e).__name__}: {e}")
        return []


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
            # ÖNEMLİ (Ekim 2026): "tüm il" sorgusu (?ILKODU=X, ilçesiz) MEB
            # sunucusunda kırpılıyor (bkz. --all-ilceler açıklaması). Toplu yol
            # da artık her ilçeyi AYRI sorguluyor; ilçe listesi referans
            # tablodan okunamazsa il atlanmaz, kapsama dosyasına hata yazılır.
            ilceler = discover_ilceler(il_kodu)
            if not ilceler:
                print(f"  HATA: İl {il_kodu} için ilçe listesi bulunamadı.")
                COVERAGE.append({"il_kodu": str(il_kodu), "ilce_kodu": None, "beklenen": None,
                                 "cekilen": 0, "durum": "ilce_listesi_yok"})
            il_toplam = 0
            for ilce in ilceler:
                try:
                    ilce_data = scrape_okullar(il_kodu, ilce["kod"])
                except Exception as e:
                    print(f"  HATA: İl {il_kodu} / {ilce['ad']} çekilemedi -> {e}")
                    COVERAGE.append({"il_kodu": str(il_kodu), "ilce_kodu": str(ilce["kod"]), "beklenen": None,
                                     "cekilen": 0, "durum": f"hata: {str(e)[:150]}"})
                    continue
                for row in ilce_data:
                    parts = [p.strip() for p in row["raw_name"].split(" - ", 2)]
                    if len(parts) >= 3:
                        row["il_ad"] = parts[0]
                        row["ilce_ad"] = parts[1]
                        row["raw_name"] = parts[2]
                    else:
                        row["il_ad"] = None
                        row["ilce_ad"] = ilce["ad"]
                all_data.extend(ilce_data)
                il_toplam += len(ilce_data)
                print(f"  {ilce['ad']}: {len(ilce_data)} kayıt")
            print(f"  İl {il_kodu}: {il_toplam} kayıt, {len(ilceler)} ilçe (toplam: {len(all_data)})")

            # ÖNEMLİ: Her il sonrası dosyayı YENİDEN YAZIYORUZ (ara kayıt) - iş
            # zaman aşımına uğrarsa bile şimdiye kadar çekilen veri dosyada
            # kalır ve bir sonraki adımda (artifact yükleme başarısız olsa
            # bile GitHub loglarından) kurtarılabilir.
            out_path = Path(args.output)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(json.dumps(all_data, ensure_ascii=False, indent=2), encoding="utf-8")
            COVERAGE_PATH.write_text(json.dumps(COVERAGE, ensure_ascii=False, indent=2), encoding="utf-8")

        print(f"\nTOPLAM {len(all_data)} kayıt ({len(il_kodlari)} il) -> {args.output}")
        return

    if args.all_ilceler:
        # ÖNEMLİ (Eylül 2026 güncellemesi): MEB'in "tüm il, ilçesiz" sorgusu
        # (?ILKODU=X) SUNUCU TARAFINDA kasıtlı/varsayılan olarak SINIRLI veri
        # döndürüyor (Ankara'da gerçek 2533 kurum varken sadece 181 kayıt -
        # DataTables'ın kendi "toplam kayıt" bilgisiyle doğrulandı, script
        # hatası değil). İlçe seçim kutusu da MEB'den kaldırıldığı için
        # ilçe kodları artık Supabase'deki 'meb_il_ilce_kodlari' referans
        # tablosundan okunuyor (bkz. discover_ilceler docstring'i) ve HER
        # İLÇE İÇİN AYRI sorgu yapılıyor - bu yöntem Etimesgut testinde
        # 145/145 (%100) doğru sonuç vermişti, sunucu tarafında hâlâ çalışıyor.
        ilceler = discover_ilceler(args.il_kodu)
        if not ilceler:
            print(f"HATA: İl {args.il_kodu} için ilçe listesi bulunamadı (referans tabloda kayıt yok olabilir).")
            return

        print(f"İl {args.il_kodu} için {len(ilceler)} ilçe bulundu, sırayla çekiliyor...")
        all_data = []
        for idx, ilce in enumerate(ilceler, 1):
            print(f"\n=== [{idx}/{len(ilceler)}] {ilce['ad']} (kod={ilce['kod']}) ===")
            try:
                ilce_data = scrape_okullar(args.il_kodu, ilce["kod"])
                for row in ilce_data:
                    row["ilce_ad"] = ilce["ad"]
                all_data.extend(ilce_data)
                print(f"  {ilce['ad']}: {len(ilce_data)} kayıt (toplam: {len(all_data)})")
            except Exception as e:
                print(f"  HATA: {ilce['ad']} çekilemedi -> {e}")

            # Her ilçe sonrası ara kayıt (iş yarıda kesilse bile veri kaybolmasın)
            out_path = Path(args.output)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(json.dumps(all_data, ensure_ascii=False, indent=2), encoding="utf-8")
            COVERAGE_PATH.write_text(json.dumps(COVERAGE, ensure_ascii=False, indent=2), encoding="utf-8")

        print(f"\nTOPLAM {len(all_data)} kayıt ({len(ilceler)} ilçe) -> {args.output}")
        return

    print(f"MEB verisi çekiliyor: il={args.il_kodu} ilçe={args.ilce_kodu}")
    data = scrape_okullar(args.il_kodu, args.ilce_kodu)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"{len(data)} kayıt bulundu -> {out_path}")


if __name__ == "__main__":
    main()
