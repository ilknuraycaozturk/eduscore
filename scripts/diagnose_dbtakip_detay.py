"""
dbtakip.com OZEL lise DETAY sayfasi teshisi (veritabanina YAZMAZ).

Soru: dbtakip'te listelenen ozel liselerin kacinin detay sayfasinda taban puani /
yuzdelik dilim bilgisi var? (diagnose_dbtakip_ozel.py, 05.10.2026: liste
satirlarinda puan yok, tur filtresi URL ile calismiyor, ilk surumde 20 sayfa siniri vardi.)

Cikti: her okul icin "il|okul_adi|href|puan_satirlari" (puan_satirlari bossa "-").
"""
import re

from playwright.sync_api import sync_playwright

ILLER = ["i-stanbul", "ankara", "i-zmir"]
LISTE = "https://dbtakip.com/liseler/{il}?page={p}"

JS_LIST = r"""
() => {
  const out = []; const seen = new Set();
  for (const a of document.querySelectorAll('a[href]')) {
    const name = (a.innerText || '').trim().replace(/\s+/g, ' ');
    if (!/özel|ÖZEL|Özel/.test(name) || name.length < 8 || name.length > 160) continue;
    const href = a.href;
    if (seen.has(href)) continue; seen.add(href);
    out.push({ name, href });
  }
  const pages = [...document.querySelectorAll('a[href*="page="]')]
    .map(a => parseInt((a.getAttribute('href').match(/page=(\d+)/) || [])[1] || '0', 10));
  return { rows: out, maxPage: pages.length ? Math.max(...pages) : 1 };
}
"""

PUAN_RE = re.compile(r"taban|yüzdelik|yuzdelik|kontenjan|puan", re.I)


def main():
    okullar = []  # (il, name, href)
    lines, ozet = [], []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        for il in ILLER:
            seen, sayfa, max_page = set(), 1, 1
            while sayfa <= max_page and sayfa <= 60:
                try:
                    page.goto(LISTE.format(il=il, p=sayfa), wait_until="networkidle", timeout=45000)
                    page.wait_for_timeout(800)
                    r = page.evaluate(JS_LIST)
                except Exception as e:
                    ozet.append(f"{il}|liste HATA sayfa {sayfa}: {str(e)[:60]}")
                    break
                max_page = max(max_page, r["maxPage"])
                for row in r["rows"]:
                    if row["href"] not in seen:
                        seen.add(row["href"])
                        okullar.append((il, row["name"], row["href"]))
                sayfa += 1
            ozet.append(f"{il}|liste sayfasi={max_page}|ozel okul={len(seen)}")

        puanli = 0
        for il, name, href in okullar:
            try:
                page.goto(href, wait_until="networkidle", timeout=45000)
                page.wait_for_timeout(600)
                text = page.evaluate("() => document.body.innerText")
            except Exception as e:
                lines.append(f"{il}|{name}|{href}|HATA {str(e)[:40]}")
                continue
            ilgili = []
            for ln in text.split("\n"):
                ln = re.sub(r"\s+", " ", ln).strip()
                if ln and len(ln) < 140 and PUAN_RE.search(ln) and re.search(r"\d", ln):
                    ilgili.append(ln[:90])
                if len(ilgili) >= 4:
                    break
            if ilgili:
                puanli += 1
            lines.append(f"{il}|{name}|{href.replace('https://dbtakip.com', '')}|{' ~ '.join(ilgili) or '-'}")
        ozet.append(f"TOPLAM ozel okul={len(okullar)} | detayinda sayili taban/puan satiri olan={puanli}")
        browser.close()
    print("=== OZET ===")
    print("\n".join(ozet))
    print("=== DETAYLAR ===")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
