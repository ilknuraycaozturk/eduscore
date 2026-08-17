"""
scrape_and_load_yks_sinavizcisi.py
====================================
EduScor — sinavizcisi.com'dan lise bazında YKS/üniversite yerleştirme
başarı verisini (2022-2025, 4 yıllık) çeker ve doğrudan Supabase'e
'universite_yerlestirme' kriterine yazar.

ÖNEMLİ - PARTİ (BATCH) MANTIĞI: MEB script'inde öğrendiğimiz gibi, binlerce
kurumu tek seferde işlemeye çalışmak GitHub Actions'ın 6 saatlik zaman
aşımına takılır. Bu yüzden her çalıştırma en fazla --max-batch (varsayılan
150) kurumu işler, zaten işlenmiş (skoru olan) kurumları hızlıca atlar.
Workflow'u art arda birkaç kez çalıştırarak tüm liseleri kapsayabiliriz.

Kullanım:
    export SUPABASE_URL="..."
    export SUPABASE_SERVICE_ROLE_KEY="..."
    python scrape_and_load_yks_sinavizcisi.py --max-batch 150 --dry-run
"""
import argparse
import os
import random
import re
import sys
import time

import requests
from playwright.sync_api import sync_playwright

BASE_URL = "https://sinavizcisi.com"

LISE_TYPE_SLUGS = [
    "lise", "fen-lisesi", "sosyal-bilimler-lisesi", "anadolu-lisesi",
    "anadolu-imam-hatip-lisesi", "mesleki-teknik-anadolu-lisesi",
]


def turkish_lower(s: str) -> str:
    return s.replace("İ", "i").replace("I", "ı").lower()


def bare_name(full_name: str) -> str:
    """'ANKARA - ÇANKAYA - Ankara Fen Lisesi' -> 'Ankara Fen Lisesi'"""
    parts = full_name.split(" - ", 2)
    return parts[2] if len(parts) == 3 else full_name


def fetch_all_paginated(base_url: str, headers: dict, path: str, page_size: int = 1000) -> list[dict]:
    all_rows, offset = [], 0
    sep = "&" if "?" in path else "?"
    while True:
        resp = requests.get(f"{base_url}{path}{sep}limit={page_size}&offset={offset}", headers=headers)
        resp.raise_for_status()
        page = resp.json()
        all_rows.extend(page)
        if len(page) < page_size:
            break
        offset += page_size
    return all_rows


def search_and_find_url(page, okul_adi: str, is_public: bool, timeout_ms: int = 15000) -> tuple[str | None, int | None]:
    page.goto(f"{BASE_URL}/", wait_until="networkidle", timeout=timeout_ms)
    page.wait_for_timeout(800)

    search_input = page.query_selector("input[placeholder*='Lise ara' i]")
    if not search_input:
        return None, None

    search_input.click()
    search_input.fill(okul_adi)
    page.wait_for_timeout(1200)

    lise_links = page.query_selector_all("a[href*='/lise/']")
    candidates = []
    for link in lise_links:
        href = link.get_attribute("href") or ""
        text = link.inner_text().strip()
        candidates.append((href, text))

    if not candidates:
        return None, None

    # Devlet okulu arıyorsak 'ÖZEL' geçen sonuçları ele - MEV Koleji, Sınav
    # Koleji gibi özel okullar aynı isimle çıkabiliyor ve yanlış eşleşmeye
    # yol açabiliyor.
    if is_public:
        non_ozel = [c for c in candidates if "ÖZEL" not in c[1].upper()]
        if non_ozel:
            candidates = non_ozel

    # Arama sonucu kartında "... • Lise • 537 öğrenci" gibi bir metin de
    # geçiyor - bunu ekstra bir sayfa ziyareti yapmadan (bedavaya) yakalayıp
    # kaydediyoruz.
    ogrenci_sayisi = None
    m = re.search(r"(\d+)\s*öğrenci", candidates[0][1])
    if m:
        ogrenci_sayisi = int(m.group(1))

    return candidates[0][0], ogrenci_sayisi


def extract_stats(http_session: requests.Session, url: str, timeout_s: int = 15) -> dict:
    """ÖNEMLİ (Aksiyon 1.6 sonrası): Bu fonksiyon artık Playwright yerine basit
    'requests' kullanıyor - yaptığımız teşhis, okul detay sayfalarının
    Cloudflare/JS engellemesi olmadan düz HTTP isteğiyle çekilebildiğini
    gösterdi. Sadece ARAMA adımı (search_and_find_url) hâlâ Playwright
    gerektiriyor çünkü o sayfa sonuçları JavaScript ile dolduruyor."""
    from bs4 import BeautifulSoup

    full_url = url if url.startswith("http") else f"{BASE_URL}{url}"
    if not full_url.rstrip("/").endswith("universite-yerlesmeleri"):
        full_url = full_url.rstrip("/") + "/universite-yerlesmeleri/"

    try:
        resp = http_session.get(full_url, timeout=timeout_s)
        resp.raise_for_status()
    except Exception:
        return {"toplam_yerlesen": None, "ilk_sene_basari_yuzde": None, "farkli_universite": None, "url": full_url}

    soup = BeautifulSoup(resp.text, "html.parser")
    body_text = soup.get_text(" ", strip=True)

    toplam_match = re.search(r"(\d+)\s*Toplam Yerleşen", body_text)
    ilk_sene_match = re.search(r"([\d.,]+)%\s*İlk Senede Yerleşme Başarısı", body_text)
    uni_match = re.search(r"(\d+)\s*Farklı Üniversite", body_text)

    return {
        "toplam_yerlesen": int(toplam_match.group(1)) if toplam_match else None,
        "ilk_sene_basari_yuzde": float(ilk_sene_match.group(1).replace(",", ".")) if ilk_sene_match else None,
        "farkli_universite": int(uni_match.group(1)) if uni_match else None,
        "url": full_url,
    }


def main():
    parser = argparse.ArgumentParser(description="sinavizcisi.com'dan YKS verisi çeker ve Supabase'e yazar.")
    parser.add_argument("--max-batch", type=int, default=150,
                         help="Bu çalıştırmada işlenecek en fazla kurum sayısı (6 saatlik zaman aşımını önlemek için)")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    supabase_url = os.environ.get("SUPABASE_URL")
    service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not supabase_url or not service_key:
        print("HATA: SUPABASE_URL ve SUPABASE_SERVICE_ROLE_KEY gerekli.")
        sys.exit(1)

    headers = {
        "apikey": service_key,
        "Authorization": f"Bearer {service_key}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }

    # Lise türü ID'lerini bul
    resp = requests.get(
        f"{supabase_url}/rest/v1/institution_types?select=id,slug&slug=in.({','.join(LISE_TYPE_SLUGS)})",
        headers=headers,
    )
    resp.raise_for_status()
    type_ids = [r["id"] for r in resp.json()]

    resp = requests.get(
        f"{supabase_url}/rest/v1/scoring_criteria?select=id&key=eq.universite_yerlestirme",
        headers=headers,
    )
    resp.raise_for_status()
    criteria_rows = resp.json()
    if not criteria_rows:
        print("HATA: 'universite_yerlestirme' kriteri bulunamadı.")
        sys.exit(1)
    criteria_id = criteria_rows[0]["id"]

    # ÖNEMLİ: Zaten skoru OLAN kurumları hariç tutuyoruz - böylece her
    # çalıştırma otomatik olarak kaldığı yerden devam eder (aynı kayıtları
    # tekrar tekrar aramaya çalışmaz).
    resp = requests.get(
        f"{supabase_url}/rest/v1/institution_criteria_scores?select=institution_id&criteria_id=eq.{criteria_id}",
        headers=headers,
    )
    resp.raise_for_status()
    already_scored_ids = {r["institution_id"] for r in resp.json()}
    print(f"{len(already_scored_ids)} kurum zaten skorlanmış, atlanacak.")

    all_lise = fetch_all_paginated(
        supabase_url, headers,
        f"/rest/v1/institutions?select=id,name,is_public&institution_type_id=in.({','.join(type_ids)})",
    )
    todo = [i for i in all_lise if i["id"] not in already_scored_ids][: args.max_batch]
    print(f"Toplam {len(all_lise)} lise, {len(todo)} kurum bu çalıştırmada işlenecek.")

    if not todo:
        print("İşlenecek kurum kalmadı - hepsi zaten skorlanmış! 🎉")
        github_output = os.environ.get("GITHUB_OUTPUT")
        if github_output:
            with open(github_output, "a", encoding="utf-8") as f:
                f.write("kalan=0\n")
        return

    processed, matched, unmatched = 0, 0, []
    http_session = requests.Session()
    http_session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    })

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        for inst in todo:
            # ÖNEMLİ: Artık sadece ARAMA adımı Playwright kullanıyor (veri
            # çekme adımı hızlı 'requests' ile yapılıyor) - bu yüzden bekleme
            # süresini kısalttık, toplam yük azaldığı için sitenin bizi
            # sınırlama ihtimali de düştü.
            time.sleep(random.uniform(1.5, 3))

            name = bare_name(inst["name"])
            try:
                url, ogrenci_sayisi = search_and_find_url(page, name, inst.get("is_public", True))
                if not url:
                    unmatched.append(inst["name"])
                    processed += 1
                    continue

                stats = extract_stats(http_session, url)
                if stats["ilk_sene_basari_yuzde"] is None:
                    unmatched.append(inst["name"])
                    processed += 1
                    continue

                # Skor: doğrudan "ilk senede yerleşme başarısı" yüzdesini kullanıyoruz
                # (0-100 arası, zaten bir başarı yüzdesi - dönüştürmeye gerek yok).
                score = stats["ilk_sene_basari_yuzde"]
                source_note = (
                    f"Kaynak: sinavizcisi.com ({stats['url']}) - ÖSYM'nin resmi YKS yerleştirme "
                    f"sonuçlarından derlenmiştir. 2022-2025 (4 yıllık) toplam {stats['toplam_yerlesen']} "
                    f"mezun yerleşmiş, bunların %{score} ilk senesinde yerleşmiştir "
                    f"({stats['farkli_universite']} farklı üniversite). "
                    f"NOT: Bu, tek bir yıla değil son 4 yılın toplamına/ortalamasına dayanır."
                )

                if not args.dry_run:
                    if ogrenci_sayisi:
                        requests.patch(
                            f"{supabase_url}/rest/v1/institutions?id=eq.{inst['id']}",
                            headers=headers, json={"student_count": ogrenci_sayisi},
                        )
                    resp = requests.post(
                        f"{supabase_url}/rest/v1/institution_criteria_scores?on_conflict=institution_id,criteria_id",
                        headers={**headers, "Prefer": "resolution=merge-duplicates"},
                        json={
                            "institution_id": inst["id"],
                            "criteria_id": criteria_id,
                            "score": score,
                            "source_note": source_note,
                            "is_verified": False,
                        },
                    )
                    if resp.status_code not in (200, 201, 204):
                        print(f"UYARI: '{name}' yazılamadı -> {resp.status_code} {resp.text[:200]}")
                    else:
                        matched += 1
                else:
                    matched += 1
                    print(f"[DRY-RUN] {name} -> skor={score}, not={source_note[:100]}...")

            except Exception as e:
                print(f"UYARI: '{name}' işlenirken hata -> {e}")
                unmatched.append(inst["name"])

            processed += 1
            if processed % 20 == 0:
                print(f"  ...{processed}/{len(todo)} işlendi ({matched} eşleşti, {len(unmatched)} eşleşmedi)")

        browser.close()

    print(f"\nTamamlandı: {processed} kurum denendi, {matched} eşleşip skorlandı, {len(unmatched)} eşleşmedi.")
    if unmatched:
        print("--- Eşleşmeyen ilk 20 ---")
        for n in unmatched[:20]:
            print(f"  ? {n}")

    kalan = len(all_lise) - len(already_scored_ids) - matched
    if kalan > 0:
        print(f"\n⚠️ Tahmini {kalan} kurum daha kaldı. Workflow'u TEKRAR ÇALIŞTIRIN, kaldığı yerden devam edecek.")

    # GitHub Actions'ın kendi kendini yeniden tetikleyebilmesi için sonucu
    # $GITHUB_OUTPUT dosyasına da yazıyoruz (workflow YAML bunu okuyacak).
    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a", encoding="utf-8") as f:
            f.write(f"kalan={max(kalan, 0)}\n")



if __name__ == "__main__":
    main()
