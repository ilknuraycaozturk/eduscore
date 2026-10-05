"""
dbtakip.com OZEL lise kapsam teshisi (veritabanina YAZMAZ).

Soru: dbtakip, TOZOK listesindeki (tozok_msp_ozel_okullar) 9 ildeki ozel okullarin
kacini, puan bilgisiyle birlikte listeliyor?

Ilk teshis (diagnose_dbtakip.py, 05.10.2026) sayfada name="type" filtresinde
ozel-anadolu-lisesi / ozel-fen-lisesi / ozel-lise seceneklerinin oldugunu gosterdi.
Bu betik her il x tur icin listeyi acar, sayfalamayi izler ve okul satirlarini toplar.

Cikti: her satir "il|tur|okul_adi|satir_metni" (satir metni puan iceriyorsa gorunur).
"""
import json
import re
import sys

from playwright.sync_api import sync_playwright

ILLER = ["i-stanbul", "ankara", "i-zmir", "mersin", "konya", "bursa", "antalya", "adana", "bitlis"]
TURLER = ["ozel-anadolu-lisesi", "ozel-fen-lisesi", "ozel-lise"]
BASE = "https://dbtakip.com/liseler/{il}?type={tur}&page={p}"

# Sayfadaki okul satirlarini bul: icinde "Özel"/"ÖZEL" gecen ve bir detay sayfasina
# giden baglantilar. Her baglantinin en yakin satir/kart kapsayicisinin metni alinir.
JS_ROWS = r"""
() => {
  const out = [];
  const seen = new Set();
  for (const a of document.querySelectorAll('a[href]')) {
    const name = (a.innerText || '').trim().replace(/\s+/g, ' ');
    if (!/özel|ÖZEL|Özel/.test(name) || name.length < 8 || name.length > 160) continue;
    const href = a.getAttribute('href');
    if (seen.has(href)) continue;
    seen.add(href);
    const row = a.closest('tr, li, .card, [class*="item"], [class*="row"]') || a.parentElement;
    const text = (row ? row.innerText : name).trim().replace(/\s+/g, ' ').slice(0, 160);
    out.push({ name, href, text });
  }
  const pages = [...document.querySelectorAll('a[href*="page="]')]
    .map(a => parseInt((a.getAttribute('href').match(/page=(\d+)/) || [])[1] || '0', 10));
  return { rows: out, maxPage: pages.length ? Math.max(...pages) : 1, title: document.title };
}
"""


def main():
    lines, ozet = [], []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        for il in ILLER:
            for tur in TURLER:
                toplam, sayfa, max_page, status = 0, 1, 1, "?"
                while sayfa <= max_page and sayfa <= 20:
                    url = BASE.format(il=il, tur=tur, p=sayfa)
                    try:
                        resp = page.goto(url, wait_until="networkidle", timeout=45000)
                        page.wait_for_timeout(1200)
                        r = page.evaluate(JS_ROWS)
                    except Exception as e:  # tek bir sayfa hatasi tum olcumu durdurmasin
                        ozet.append(f"{il}|{tur}|HATA sayfa {sayfa}: {str(e)[:80]}")
                        break
                    if sayfa == 1:
                        max_page = max(1, r["maxPage"])
                        status = resp.status if resp else "?"
                    for row in r["rows"]:
                        lines.append(f"{il}|{tur}|{row['name']}|{row['text']}")
                    toplam += len(r["rows"])
                    sayfa += 1
                ozet.append(f"{il}|{tur}|okul={toplam}|sayfa={max_page}|http={status}")
        browser.close()
    print("=== OZET (il|tur|okul sayisi|sayfa|http) ===")
    print("\n".join(ozet))
    print(f"=== TOPLAM SATIR: {len(lines)} ===")
    print("=== SATIRLAR ===")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
