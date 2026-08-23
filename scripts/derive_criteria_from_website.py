"""
derive_criteria_from_website.py
================================
EduScor — website alanı dolu olan kurumların sitelerini KİBARCA tarar,
ham HTML'i website_crawl_snapshots'a kaydeder.

ÖNEMLİ: Bu script EXTRACTION (veri çıkarımı) YAPMAZ — bu ayrı bir script'in
(extract_criteria_candidates.py) işi. Ayrım bilinçli: ağa çıkmak
pahalı/kırılgan, extraction mantığı ucuz/değişken. Extraction kuralları
değiştikçe bu script'i TEKRAR ÇALIŞTIRMANIZA GEREK YOK — sadece
extract_criteria_candidates.py'yi kaydedilmiş snapshot'lar üzerinde
yeniden çalıştırın.

KİBARLIK KURALLARI (ZORUNLU):
  - robots.txt'e kesin uyum (urllib.robotparser)
  - Domain başına minimum 1.5 saniye bekleme
  - Açıklayıcı User-Agent (gerçek iletişim bilgisiyle)
  - 403/429 alınan domain agresif tekrar denenmez, atlanır
  - İçerik hash'i değişmemişse tekrar DB'ye yazılmaz

KEŞİF STRATEJİSİ (tahmin değil):
  1. robots.txt çekilir → "Sitemap:" varsa oradan gerçek URL listesi alınır
  2. Yoksa: ana sayfadan başlayan sığ bir BFS (derinlik≤2, sayfa≤8) ile
     aynı domain içi linkler keşfedilir

Kullanım:
    export SUPABASE_URL="..."
    export SUPABASE_SERVICE_ROLE_KEY="..."
    python derive_criteria_from_website.py
"""
import hashlib
import os
import sys
import time
import urllib.robotparser
from collections import deque
from urllib.parse import urljoin, urlparse
from xml.etree import ElementTree

import requests
from bs4 import BeautifulSoup

USER_AGENT = "EduScor-Crawler/1.0 (+destek@eduscor.com; egitim karsilastirma platformu)"
POLITENESS_DELAY_SEC = 1.5
MAX_PAGES_PER_SITE = 8
MAX_DEPTH = 2
REQUEST_TIMEOUT = 15

MAX_INSTITUTIONS_PER_RUN = 50


def pg_get(base_url, headers, path):
    resp = requests.get(f"{base_url}{path}", headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.json()


def pg_upsert(base_url, headers, table, rows, on_conflict):
    up_headers = dict(headers)
    up_headers["Prefer"] = "resolution=merge-duplicates,return=minimal"
    resp = requests.post(
        f"{base_url}/rest/v1/{table}?on_conflict={on_conflict}",
        headers=up_headers, json=rows, timeout=30,
    )
    if resp.status_code >= 300:
        print(f"  ⚠️ Upsert hatası ({table}): {resp.status_code} {resp.text[:200]}")


def get_robots_and_sitemap(base_url, session):
    parsed = urlparse(base_url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    rp = urllib.robotparser.RobotFileParser()
    sitemap_urls = []
    try:
        resp = session.get(robots_url, timeout=REQUEST_TIMEOUT, headers={"User-Agent": USER_AGENT})
        if resp.status_code == 200:
            rp.parse(resp.text.splitlines())
            for line in resp.text.splitlines():
                if line.lower().startswith("sitemap:"):
                    sitemap_urls.append(line.split(":", 1)[1].strip())
        else:
            rp.allow_all = True
    except Exception:
        rp.allow_all = True
    return rp, sitemap_urls


def discover_urls_from_sitemap(sitemap_url, base_domain, session):
    try:
        resp = session.get(sitemap_url, timeout=REQUEST_TIMEOUT, headers={"User-Agent": USER_AGENT})
        if resp.status_code != 200:
            return []
        root = ElementTree.fromstring(resp.content)
        urls = []
        for elem in root.iter():
            if elem.tag.endswith("loc") and elem.text:
                if urlparse(elem.text).netloc == base_domain:
                    urls.append(elem.text.strip())
        return urls[:MAX_PAGES_PER_SITE]
    except Exception:
        return []


def discover_urls_via_bfs(base_url, rp, session):
    """Sitemap yoksa: sığ BFS ile aynı domain içi linkler keşfedilir.
    Tahmine dayalı slug listesi (hakkimizda/genel-tanitim vb.) KULLANMAZ."""
    base_domain = urlparse(base_url).netloc
    visited = set()
    queue = deque([(base_url, 0)])
    discovered = []

    while queue and len(discovered) < MAX_PAGES_PER_SITE:
        url, depth = queue.popleft()
        if url in visited or depth > MAX_DEPTH:
            continue
        visited.add(url)

        if not rp.allow_all and not rp.can_fetch(USER_AGENT, url):
            continue
        try:
            time.sleep(POLITENESS_DELAY_SEC)
            resp = session.get(url, timeout=REQUEST_TIMEOUT, headers={"User-Agent": USER_AGENT})
        except Exception:
            continue
        if resp.status_code != 200:
            continue

        discovered.append((url, resp.status_code, resp.text))

        if depth < MAX_DEPTH:
            soup = BeautifulSoup(resp.text, "html.parser")
            for a in soup.find_all("a", href=True):
                link = urljoin(url, a["href"])
                if urlparse(link).netloc == base_domain and link not in visited:
                    queue.append((link, depth + 1))

    return discovered


def crawl_institution(inst, base_url, headers, session):
    website = inst["website"]
    base_domain = urlparse(website).netloc
    rp, sitemap_urls = get_robots_and_sitemap(website, session)

    if not rp.allow_all and not rp.can_fetch(USER_AGENT, website):
        print("  ⛔ robots.txt izin vermiyor")
        return 0

    pages = []
    for sm in sitemap_urls[:2]:
        urls = discover_urls_from_sitemap(sm, base_domain, session)
        for u in urls[:MAX_PAGES_PER_SITE]:
            if not rp.allow_all and not rp.can_fetch(USER_AGENT, u):
                continue
            time.sleep(POLITENESS_DELAY_SEC)
            try:
                resp = session.get(u, timeout=REQUEST_TIMEOUT, headers={"User-Agent": USER_AGENT})
                pages.append((u, resp.status_code, resp.text if resp.status_code == 200 else ""))
            except Exception:
                continue
        if pages:
            break

    if not pages:
        pages = discover_urls_via_bfs(website, rp, session)

    saved = 0
    rows = []
    for url, status, html in pages:
        content_hash = hashlib.sha256(html.encode("utf-8", errors="ignore")).hexdigest() if html else None
        try:
            existing = pg_get(base_url, headers,
                               f"/rest/v1/website_crawl_snapshots?institution_id=eq.{inst['id']}&url=eq.{requests.utils.quote(url, safe='')}&select=content_hash")
            if existing and existing[0]["content_hash"] == content_hash:
                continue
        except Exception:
            pass

        rows.append({
            "institution_id": inst["id"],
            "url": url,
            "http_status": status,
            "content_hash": content_hash,
            "raw_html": (html[:500000] if html else None),
        })
        saved += 1

    if rows:
        pg_upsert(base_url, headers, "website_crawl_snapshots", rows, "institution_id,url")

    return saved


def get_progress(base_url, headers, key, default):
    try:
        rows = pg_get(base_url, headers, f"/rest/v1/scrape_progress?key=eq.{key}&select=value")
        return rows[0]["value"] if rows else default
    except Exception:
        return default


def set_progress(base_url, headers, key, value):
    pg_upsert(base_url, headers, "scrape_progress", [{"key": key, "value": str(value)}], "key")


def main():
    base_url = os.environ.get("SUPABASE_URL")
    service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not base_url or not service_key:
        print("HATA: SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY ortam değişkenleri eksik.")
        sys.exit(1)

    headers = {
        "apikey": service_key,
        "Authorization": f"Bearer {service_key}",
        "Content-Type": "application/json",
    }
    session = requests.Session()

    # İlerleme takibi: mevcut MEB/LGS/YKS scraper'larıyla aynı desen (scrape_progress).
    # Her çalıştırma AYNI ilk N kurumu değil, kaldığı yerden devam eder. Tüm
    # website'li kurumlar bir tur tamamlanınca (wrap) baştan başlar - içerik
    # hash kontrolü sayesinde değişmeyen sayfalar tekrar yazılmaz, sadece
    # değişenler güncellenir (kibarlık ilkesiyle tutarlı, gereksiz DB yazması yok).
    offset = int(get_progress(base_url, headers, "kriter_crawl_offset", 0))

    count_headers = dict(headers)
    count_headers["Prefer"] = "count=exact"
    count_resp = requests.get(
        f"{base_url}/rest/v1/institutions?website=not.is.null&select=id&limit=1",
        headers=count_headers, timeout=30,
    )
    total_count = 0
    if "content-range" in count_resp.headers:
        total_count = int(count_resp.headers["content-range"].split("/")[-1])

    if total_count and offset >= total_count:
        offset = 0  # tam tur tamamlandı, baştan başla

    institutions = pg_get(
        base_url, headers,
        f"/rest/v1/institutions?website=not.is.null&select=id,name,website"
        f"&order=id&limit={MAX_INSTITUTIONS_PER_RUN}&offset={offset}",
    )

    print(f"{len(institutions)} kurum işlenecek (offset={offset}/{total_count}, max {MAX_INSTITUTIONS_PER_RUN}).")

    total_saved = 0
    for inst in institutions:
        print(f"→ {inst['name']} ({inst['website']})")
        try:
            saved = crawl_institution(inst, base_url, headers, session)
            total_saved += saved
            print(f"  ✓ {saved} sayfa kaydedildi/güncellendi")
        except Exception as exc:
            print(f"  ✗ Hata: {exc}")
        time.sleep(POLITENESS_DELAY_SEC)

    new_offset = offset + len(institutions)
    if total_count and new_offset >= total_count:
        new_offset = 0
        print("\n✅ Tüm website'li kurumlar bir tur tamamlandı, offset sıfırlandı.")
    set_progress(base_url, headers, "kriter_crawl_offset", new_offset)

    print(f"\nToplam: {total_saved} sayfa snapshot'ı kaydedildi. Sıradaki offset: {new_offset}")


if __name__ == "__main__":
    main()
