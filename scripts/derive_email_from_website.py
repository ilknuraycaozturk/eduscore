"""
derive_email_from_website.py
================================
EduScor — website alanı zaten '{isim}.meb.k12.tr' formatında olan kurumların
KENDİ SİTELERİNE gidip, sayfadaki linklerden 6 haneli kurum kodunu
(meb_iys_dosyalar/{il}/{ilce}/{KOD}/... formatında) bulur ve
'{KOD}@meb.k12.tr' e-postasını otomatik olarak institutions.email alanına
yazar.

Kullanım:
    export SUPABASE_URL="..."
    export SUPABASE_SERVICE_ROLE_KEY="..."
    python derive_email_from_website.py --max-batch 100 --dry-run
"""
import argparse
import os
import re
import sys

import requests
from playwright.sync_api import sync_playwright


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


def find_kurum_kodu(page, website: str, timeout_ms: int = 15000) -> str | None:
    try:
        page.goto(website, wait_until="networkidle", timeout=timeout_ms)
        page.wait_for_timeout(500)
    except Exception:
        return None

    links = page.query_selector_all("a[href*='meb_iys_dosyalar']")
    for link in links:
        href = link.get_attribute("href") or ""
        m = re.search(r"meb_iys_dosyalar/\d+/\d+/(\d{5,7})/", href)
        if m:
            return m.group(1)
    return None


def main():
    parser = argparse.ArgumentParser(description="Web sitesinden kurum kodu türetir, e-posta yazar.")
    parser.add_argument("--max-batch", type=int, default=100)
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

    all_rows = fetch_all_paginated(
        supabase_url, headers,
        "/rest/v1/institutions?select=id,name,website&email=is.null&website=not.is.null",
    )
    todo = [r for r in all_rows if r.get("website") and "meb.k12.tr" in r["website"]][: args.max_batch]
    print(f"{len(all_rows)} e-postasız kurum var, {len(todo)} tanesi bu çalıştırmada denenecek.")

    if not todo:
        print("İşlenecek kurum kalmadı.")
        return

    bulundu, bulunamadi = 0, []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        for inst in todo:
            kod = find_kurum_kodu(page, inst["website"])
            if not kod:
                bulunamadi.append(inst["name"])
                continue

            email = f"{kod}@meb.k12.tr"
            if args.dry_run:
                print(f"[DRY-RUN] {inst['name']} -> {email}")
                bulundu += 1
                continue

            resp = requests.patch(
                f"{supabase_url}/rest/v1/institutions?id=eq.{inst['id']}",
                headers=headers, json={"email": email},
            )
            if resp.status_code in (200, 204):
                bulundu += 1
            else:
                print(f"UYARI: '{inst['name']}' yazılamadı -> {resp.status_code} {resp.text[:150]}")
                bulunamadi.append(inst["name"])

        browser.close()

    print(f"\nTamamlandı: {len(todo)} denendi, {bulundu} e-posta bulundu/yazıldı, {len(bulunamadi)} bulunamadı.")
    if bulunamadi:
        print("--- Bulunamayan ilk 10 ---")
        for n in bulunamadi[:10]:
            print(f"  ? {n}")


if __name__ == "__main__":
    main()
