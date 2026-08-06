"""
tabanpuanlari.net sitesinden il bazında LGS taban puanı verisini çeker.

ÖNEMLİ NOTLAR:
1. Bu site sanal kaydırma (virtual scrolling) kullanıyor - DOM'da her an
   sadece görünen satırlar render ediliyor. Sayfayı adım adım kaydırıp,
   her adımda görünen satırları program_id'ye göre tekilleştirerek topluyoruz.
2. Sütun sırası/isimleri site tarafında değişebiliyor - bu yüzden hücreleri
   SABİT POZİSYONA göre değil, BAŞLIK METNİNE göre eşleştiriyoruz.
3. --tumu ile tüm 81 il tek çalıştırmada sırayla çekilebilir.

Kullanım:
    python scrape_tabanpuanlari.py --il ankara --output data/tabanpuan_raw.json
    python scrape_tabanpuanlari.py --tumu --output data/tabanpuan_raw.json
"""
import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE_URL = "https://tabanpuanlari.net/lgs"

DIL_KEYWORDS = ["İngilizce", "Almanca", "Fransızca", "Arapça", "Çince", "Rusça", "Japonca"]

TUM_ILLER = [
    "Adana", "Adıyaman", "Afyonkarahisar", "Ağrı", "Aksaray", "Amasya", "Ankara",
    "Antalya", "Ardahan", "Artvin", "Aydın", "Balıkesir", "Bartın", "Batman",
    "Bayburt", "Bilecik", "Bingöl", "Bitlis", "Bolu", "Burdur", "Bursa",
    "Çanakkale", "Çankırı", "Çorum", "Denizli", "Diyarbakır", "Düzce", "Edirne",
    "Elazığ", "Erzincan", "Erzurum", "Eskişehir", "Gaziantep", "Giresun",
    "Gümüşhane", "Hakkari", "Hatay", "Iğdır", "Isparta", "İstanbul", "İzmir",
    "Kahramanmaraş", "Karabük", "Karaman", "Kars", "Kastamonu", "Kayseri",
    "Kırıkkale", "Kırklareli", "Kırşehir", "Kilis", "Kocaeli", "Konya",
    "Kütahya", "Malatya", "Manisa", "Mardin", "Mersin", "Muğla", "Muş",
    "Nevşehir", "Niğde", "Ordu", "Osmaniye", "Rize", "Sakarya", "Samsun",
    "Siirt", "Sinop", "Sivas", "Şanlıurfa", "Şırnak", "Tekirdağ", "Tokat",
    "Trabzon", "Tunceli", "Uşak", "Van", "Yalova", "Yozgat", "Zonguldak",
]


def turkish_slug(il_adi: str) -> str:
    """'Şanlıurfa' -> 'sanliurfa', 'Kırıkkale' -> 'kirikkale' gibi URL-güvenli
    hale çevirir (tabanpuanlari.net URL'lerinin beklediği format)."""
    trans = str.maketrans({
        "İ": "i", "I": "i", "ı": "i", "Ğ": "g", "ğ": "g", "Ü": "u", "ü": "u",
        "Ş": "s", "ş": "s", "Ö": "o", "ö": "o", "Ç": "c", "ç": "c",
    })
    return il_adi.translate(trans).lower().strip()


def parse_ozellikler(text: str) -> dict:
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    result = {"cinsiyet": None, "dil": None, "sure": None, "pansiyon": None}
    for line in lines:
        if line in ("Kız/Erkek", "Kız", "Erkek"):
            result["cinsiyet"] = line
        elif line in DIL_KEYWORDS:
            result["dil"] = line
        elif re.match(r"^\d+\s*yıl$", line):
            result["sure"] = line
        elif "Pansiyon Var" in line:
            result["pansiyon"] = True
        elif "Pansiyon Yok" in line:
            result["pansiyon"] = False
    return result


def parse_number(text: str) -> float | None:
    text = (text or "").strip().replace(".", "").replace(",", ".")
    if not text or text == "-":
        return None
    try:
        return float(text)
    except ValueError:
        return None


def parse_int(text: str) -> int | None:
    text = (text or "").strip()
    if not text or text == "-":
        return None
    try:
        return int(text)
    except ValueError:
        return None


def detect_columns(header_cells: list[str]) -> dict:
    mapping = {}
    puan_idx, yuzdelik_idx, kontenjan_idx = [], [], []
    for i, text in enumerate(header_cells):
        t = text.strip()
        if "Puan" in t or "OBP" in t:
            puan_idx.append(i)
        elif "Yüzdelik" in t:
            yuzdelik_idx.append(i)
        elif "Kontenjan" in t:
            kontenjan_idx.append(i)
        elif "LİSE" in t.upper() or "LISE" in t.upper():
            mapping["lise"] = i
        elif "ÖZELLİK" in t.upper():
            mapping["ozellikler"] = i

    def assign_year(idx_list, key_prefix):
        for idx in idx_list:
            label = header_cells[idx]
            year = "2026" if "2026" in label else ("2025" if "2025" in label else None)
            if year:
                mapping[f"{key_prefix}_{year}"] = idx

    assign_year(puan_idx, "puan")
    assign_year(yuzdelik_idx, "yuzdelik")
    assign_year(kontenjan_idx, "kontenjan")

    for idx_list, key_prefix in [(puan_idx, "puan"), (yuzdelik_idx, "yuzdelik"), (kontenjan_idx, "kontenjan")]:
        assigned = [mapping.get(f"{key_prefix}_2026"), mapping.get(f"{key_prefix}_2025")]
        remaining = [i for i in idx_list if i not in assigned]
        if f"{key_prefix}_2026" not in mapping and remaining:
            mapping[f"{key_prefix}_2026"] = remaining.pop(0)
        if f"{key_prefix}_2025" not in mapping and remaining:
            mapping[f"{key_prefix}_2025"] = remaining.pop(0)

    return mapping


def extract_row(row, col_map: dict, il_adi: str) -> dict | None:
    cells = row.query_selector_all("td")
    if len(cells) < 5:
        return None

    lise_idx = col_map.get("lise", 0)
    lise_cell_lines = [l.strip() for l in cells[lise_idx].inner_text().strip().split("\n") if l.strip()]
    okul_adi = lise_cell_lines[0] if lise_cell_lines else None
    program_adi = lise_cell_lines[1] if len(lise_cell_lines) > 1 else None
    if not okul_adi:
        return None

    link_el = cells[lise_idx].query_selector("a[href*='/programs/']")
    program_id = None
    if link_el:
        href = link_el.get_attribute("href") or ""
        m = re.search(r"/programs/(\d+)", href)
        if m:
            program_id = m.group(1)

    ozellikler_idx = col_map.get("ozellikler")
    ozellikler = parse_ozellikler(cells[ozellikler_idx].inner_text()) if ozellikler_idx is not None and ozellikler_idx < len(cells) else {}

    def cell_num(key):
        idx = col_map.get(key)
        if idx is None or idx >= len(cells):
            return None
        return parse_number(cells[idx].inner_text())

    def cell_int(key):
        idx = col_map.get(key)
        if idx is None or idx >= len(cells):
            return None
        return parse_int(cells[idx].inner_text())

    return {
        "il_adi": il_adi,
        "okul_adi": okul_adi,
        "program_adi": program_adi,
        "program_id": program_id,
        "lgs_puani_2026": cell_num("puan_2026"),
        "yuzdelik_2026": cell_num("yuzdelik_2026"),
        "lgs_puani_2025": cell_num("puan_2025"),
        "yuzdelik_2025": cell_num("yuzdelik_2025"),
        "kontenjan_2026": cell_int("kontenjan_2026"),
        "kontenjan_2025": cell_int("kontenjan_2025"),
        "cinsiyet": ozellikler.get("cinsiyet"),
        "dil": ozellikler.get("dil"),
        "sure": ozellikler.get("sure"),
        "pansiyon_var": ozellikler.get("pansiyon"),
    }


def scrape_il(page, il_adi: str, il_slug: str, timeout_ms: int = 30000) -> list[dict]:
    url = f"{BASE_URL}/{il_slug}"
    collected: dict[str, dict] = {}

    print(f"Sayfa açılıyor: {url}")
    page.goto(url, wait_until="networkidle", timeout=timeout_ms)
    page.wait_for_timeout(1500)

    tables = page.query_selector_all("table")
    target_table = None
    max_rows = 0
    for t in tables:
        rows = t.query_selector_all("tr")
        if len(rows) > max_rows:
            max_rows = len(rows)
            target_table = t

    if not target_table:
        print(f"  UYARI: {il_adi} için tablo bulunamadı, atlanıyor.")
        return []

    all_rows = target_table.query_selector_all("tr")
    header_row = all_rows[0] if all_rows else None
    if not header_row:
        print(f"  UYARI: {il_adi} için başlık satırı bulunamadı, atlanıyor.")
        return []
    header_cells = [c.inner_text().strip() for c in header_row.query_selector_all("th, td")]
    col_map = detect_columns(header_cells)

    scroll_container = target_table.evaluate_handle(
        """(table) => {
            let el = table;
            while (el && el !== document.body) {
                const style = window.getComputedStyle(el);
                if ((style.overflowY === 'auto' || style.overflowY === 'scroll') && el.scrollHeight > el.clientHeight) {
                    return el;
                }
                el = el.parentElement;
            }
            return window;
        }"""
    )

    max_scrolls = 400
    stable_count = 0
    prev_total = 0

    for i in range(max_scrolls):
        rows = target_table.query_selector_all("tr")
        for row in rows:
            data = extract_row(row, col_map, il_adi)
            if not data:
                continue
            key = data["program_id"] or f"{data['okul_adi']}|{data['program_adi']}"
            collected[key] = data

        if len(collected) == prev_total:
            stable_count += 1
        else:
            stable_count = 0
        prev_total = len(collected)

        if stable_count >= 6:
            break

        scroll_container.evaluate(
            """(el) => {
                if (el === window) { window.scrollBy(0, 500); }
                else { el.scrollTop += 500; }
            }"""
        )
        page.wait_for_timeout(120)

    print(f"  {il_adi}: {len(collected)} program bulundu.")
    return list(collected.values())


def main():
    parser = argparse.ArgumentParser(description="tabanpuanlari.net'ten LGS verisi çeker.")
    parser.add_argument("--il", help="Tek bir il adı (örn. Ankara)")
    parser.add_argument("--tumu", action="store_true", help="Tüm 81 ili sırayla çeker")
    parser.add_argument("--output", default="data/tabanpuan_raw.json")
    args = parser.parse_args()

    if not args.il and not args.tumu:
        print("HATA: --il ya da --tumu belirtilmeli.")
        sys.exit(1)

    iller = TUM_ILLER if args.tumu else [args.il]
    all_results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        for idx, il_adi in enumerate(iller, 1):
            il_slug = turkish_slug(il_adi)
            print(f"\n=== [{idx}/{len(iller)}] {il_adi} ({il_slug}) ===")
            try:
                results = scrape_il(page, il_adi, il_slug)
                all_results.extend(results)
            except Exception as e:
                print(f"  HATA: {il_adi} çekilemedi -> {e}")
            # Ara kayıt: çok il varsa yarıda kesilirse veri kaybolmasın
            out_path = Path(args.output)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(json.dumps(all_results, ensure_ascii=False, indent=2), encoding="utf-8")
        browser.close()

    print(f"\nTOPLAM {len(all_results)} program kaydı ({len(iller)} il) -> {args.output}")


if __name__ == "__main__":
    main()
