"""
scrape_lgs_taban_puanlari.py
=============================
EduScor — Lise Modülü: MEB'in resmi "Taban/Tavan Puanlar ve Yüzdelik
Dilimler" PDF kılavuzundan (LGS ile öğrenci alan liseler) belirli bir
ilin (varsayılan: Ankara) tüm liselerinin akademik başarı verisini çeker.

Birincil kaynak: MEB'in kendi web sitesinde her yıl yayınladığı resmi PDF.
Örnek (2022): https://www.meb.gov.tr/meb_iys_dosyalar/2022_07/25103752_2022_ilk_yerlestirme_taban_tavan_yerlesme_bilgileri.pdf

ÖNEMLİ: MEB bu PDF'i her yıl YENİ ve TAHMİN EDİLEMEYEN bir dosya adıyla
yayınlıyor (rastgele sayısal önek + yıl). Bu yüzden --pdf-url parametresi
ZORUNLU ve elle güncellenmesi gerekiyor. Güncel yılın linkini bulmak için:
  1. meb.gov.tr'de "taban puanlar" ya da "yerleştirme sonuçları" araması yapın
  2. Ya da meb.gov.tr/liselerin-bos-kontenjanlari... haberini takip edin

Kullanım:
    python scrape_lgs_taban_puanlari.py \
        --pdf-url "https://www.meb.gov.tr/meb_iys_dosyalar/.../XXXX_taban_tavan_....pdf" \
        --il ANKARA \
        --output data/ankara_lgs_taban_puanlari.json
"""

import argparse
import json
import re
import sys
from pathlib import Path

import requests

try:
    import pdfplumber
except ImportError:
    print("pdfplumber kurulu değil. Kurulum: pip install pdfplumber")
    sys.exit(1)

# MEB'in PDF'teki bilinen okul TÜRÜ değerleri -> bizim institution_types.slug
TUR_MAP = {
    "Fen Lisesi": "fen-lisesi",
    "Sosyal Bilimler Lisesi": "sosyal-bilimler-lisesi",
    "Hazırlık Sınıfı Bulunmayan Sosyal Bilimler Lisesi": "sosyal-bilimler-lisesi",
    "Anadolu Lisesi": "anadolu-lisesi",
    "Hazırlık Sınıfı Bulunan Anadolu Lisesi": "anadolu-lisesi",
    "Anadolu İmam Hatip Lisesi": "anadolu-imam-hatip-lisesi",
    "Hazırlık Sınıfı Bulunan Anadolu İmam Hatip Lisesi": "anadolu-imam-hatip-lisesi",
    "Anadolu Teknik Programı": "mesleki-teknik-anadolu-lisesi",
    "Anadolu Meslek Programı": "mesleki-teknik-anadolu-lisesi",
}

# Bir satırın başlangıcı: TERCİH KODU (4-6 haneli sayı) + İL (büyük harf) + İLÇE (büyük harf)
LINE_RE = re.compile(
    r"^(?P<kod>\d{4,6})\s+"
    r"(?P<il>[A-ZÇĞİÖŞÜ]+(?:\s[A-ZÇĞİÖŞÜ]+)*?)\s+"
    r"(?P<ilce>[A-ZÇĞİÖŞÜ]+(?:\s[A-ZÇĞİÖŞÜ]+)*?)\s+"
    r"(?P<rest>.+)$"
)

# Satırın sonundaki 4 sayısal alan: TABAN_PUAN TABAN_YÜZDE TAVAN_PUAN TAVAN_YÜZDE
NUMS_RE = re.compile(
    r"(?P<taban_puan>\d+(?:,\d+)?)\s+(?P<taban_yuzde>\d+(?:,\d+)?)\s+"
    r"(?P<tavan_puan>\d+(?:,\d+)?)\s+(?P<tavan_yuzde>\d+(?:,\d+)?)\s*$"
)


def download_pdf(url: str, dest: str) -> None:
    print(f"PDF indiriliyor: {url}")
    resp = requests.get(url, timeout=60, headers={"User-Agent": "Mozilla/5.0 (EduScor-Pilot/1.0)"})
    resp.raise_for_status()
    Path(dest).write_bytes(resp.content)
    print(f"İndirildi -> {dest} ({len(resp.content) / 1024:.0f} KB)")


LANGUAGES = ["İngilizce", "Almanca", "Fransızca", "Çince", "İspanyolca", "Japonca", "Rusça", "Arapça", "İtalyanca"]


def extract_tur(rest: str) -> tuple[str | None, str, int]:
    """'rest' metninden okul TÜRÜ'nü bulur, geri kalanını (okul adı) ve
    türün bittiği indeksi döndürür (kalan kısımda ALAN/YABANCI DİLİ olabilir).
    Okul adları çoğunlukla kendi türleriyle bitiyor (örn. '... Anadolu Lisesi'),
    ve TÜR sütunu bunu ayrıca tekrarlıyor - bu yüzden İLK değil SON eşleşmeyi
    almak gerekiyor (aksi halde okul adının kendi soneki 'tür' sanılıp isim kesilir).
    """
    # En sağdaki (rightmost) bitiş konumuna sahip eşleşmeyi tercih et;
    # bitiş konumu eşitse (örn. 'Anadolu Lisesi' hem tek başına hem de
    # 'Hazırlık Sınıfı Bulunan Anadolu Lisesi' içinde aynı yerde bitebilir)
    # daha UZUN/spesifik olanı (daha erken başlayanı) tercih et.
    best_end, best_start, best_tur = -1, None, None
    for tur_text in TUR_MAP:
        idx = rest.rfind(tur_text)
        if idx == -1:
            continue
        end = idx + len(tur_text)
        if end > best_end or (end == best_end and (best_start is None or idx < best_start)):
            best_end, best_start, best_tur = end, idx, tur_text
    if best_tur is None:
        return None, rest, -1
    okul_adi = rest[:best_start].strip()
    return best_tur, okul_adi, best_end


def extract_yabanci_dil(trailing_text: str) -> str | None:
    """TÜR'den sonraki (ALAN + YABANCI DİLİ içerebilen) metinden dil adını bulur."""
    for lang in LANGUAGES:
        if lang in trailing_text:
            return lang
    return None


def parse_pdf(pdf_path: str, il_filter: str | None) -> list[dict]:
    results: list[dict] = []
    skipped_no_match = 0
    all_iller_seen: set[str] = set()  # teşhis amaçlı - filtre uygulanmadan ÖNCE

    with pdfplumber.open(pdf_path) as pdf:
        print(f"PDF {len(pdf.pages)} sayfa, işleniyor...")
        for page_num, page in enumerate(pdf.pages, 1):
            text = page.extract_text() or ""
            for raw_line in text.split("\n"):
                line = raw_line.strip()
                if not line or "TERCİH" in line or "TABAN PUAN" in line or "Yılı Merkezi" in line:
                    continue  # başlık/sayfa başlığı satırları

                m = LINE_RE.match(line)
                if not m:
                    continue

                il = m.group("il").strip()
                all_iller_seen.add(il)  # ÖNEMLİ: filtre uygulanmadan önce, teşhis için
                if il_filter and il != il_filter.upper():
                    continue

                ilce = m.group("ilce").strip()
                rest = m.group("rest").strip()

                nums_match = NUMS_RE.search(rest)
                if not nums_match:
                    skipped_no_match += 1
                    continue

                rest_before_nums = rest[: nums_match.start()].strip()
                tur, okul_adi_ham, tur_end_idx = extract_tur(rest_before_nums)
                if not tur:
                    skipped_no_match += 1
                    continue

                trailing_text = rest_before_nums[tur_end_idx:].strip()
                yabanci_dil = extract_yabanci_dil(trailing_text)
                hazirlik_var = "Hazırlık Sınıfı Bulunan" in tur

                results.append({
                    "il": il,
                    "ilce": ilce,
                    "okul_adi": okul_adi_ham.strip(),
                    "tur_ham": tur,
                    "institution_type_slug": TUR_MAP[tur],
                    "yabanci_dil": yabanci_dil,
                    "hazirlik_var": hazirlik_var,
                    "taban_puan": float(nums_match.group("taban_puan").replace(",", ".")),
                    "taban_yuzde": float(nums_match.group("taban_yuzde").replace(",", ".")),
                    "tavan_puan": float(nums_match.group("tavan_puan").replace(",", ".")),
                    "tavan_yuzde": float(nums_match.group("tavan_yuzde").replace(",", ".")),
                })

            if page_num % 20 == 0:
                etiket = il_filter if il_filter else "TÜM TÜRKİYE"
                print(f"  ...{page_num} sayfa işlendi, şu ana kadar {len(results)} {etiket} kaydı bulundu")

    etiket = il_filter if il_filter else "TÜM TÜRKİYE"
    print(f"Toplam {len(results)} kayıt bulundu ({etiket}), {skipped_no_match} satır ayrıştırılamadı (atlandı).")
    print(f"--- TEŞHİS: PDF'de (filtre uygulanmadan önce) görülen TÜM il isimleri ({len(all_iller_seen)} adet) ---")
    print(sorted(all_iller_seen))
    return results


def main():
    parser = argparse.ArgumentParser(description="MEB resmi LGS taban puan PDF'ini indirip il bazında ayrıştırır.")
    parser.add_argument("--pdf-url", required=True, help="MEB'in o yılki resmi PDF URL'i (elle bulunmalı, bkz. dosya başlığı)")
    parser.add_argument("--il", default="ANKARA", help="Belirli bir il (örn. ANKARA). Boş bırakılırsa (--il '') TÜM TÜRKİYE alınır.")
    parser.add_argument("--output", default="data/lgs_taban_puanlari.json")
    parser.add_argument("--pdf-cache", default="data/_lgs_kaynak.pdf")
    args = parser.parse_args()

    il_filter = args.il.strip() if args.il and args.il.strip() else None

    Path(args.pdf_cache).parent.mkdir(parents=True, exist_ok=True)
    download_pdf(args.pdf_url, args.pdf_cache)

    results = parse_pdf(args.pdf_cache, il_filter)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Kaydedildi -> {out_path}")


if __name__ == "__main__":
    main()
