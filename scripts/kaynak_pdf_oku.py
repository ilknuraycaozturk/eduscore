"""Resmî istatistik PDF'ini indirir, sayfaları metne çevirir (pdftotext -layout) ve
deseni içeren sayfaları kaynak_pdf_sayfalari tablosuna yazar (referans tabloları elle
okunup data/reference altına işlenmek üzere). Salt okunur kaynak; okul verisine dokunmaz.

Kullanım: python scripts/kaynak_pdf_oku.py --url URL --kaynak ad --desen "Okul öncesi|Anaokulu"
Ortam: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
"""
import argparse
import os
import re
import subprocess
import sys
import tempfile

import requests


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True)
    ap.add_argument("--kaynak", required=True)
    ap.add_argument("--desen", required=True, help="Bu düzenli ifadeyi içeren sayfalar yazılır")
    ap.add_argument("--en-fazla", type=int, default=80)
    args = ap.parse_args()
    base, key = os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    h = {"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json",
         "Prefer": "resolution=merge-duplicates,return=minimal"}

    with tempfile.TemporaryDirectory() as d:
        pdf = os.path.join(d, "k.pdf")
        r = requests.get(args.url, timeout=120, headers={"User-Agent": "EduScor/1.0 (+destek@eduscor.com)"})
        r.raise_for_status()
        open(pdf, "wb").write(r.content)
        print(f"indirildi: {len(r.content)} bayt")
        metin = subprocess.run(["pdftotext", "-layout", pdf, "-"], capture_output=True, text=True, check=True).stdout
    sayfalar = metin.split("\f")
    desen = re.compile(args.desen, re.I)
    secilen = [(i + 1, s) for i, s in enumerate(sayfalar) if desen.search(s)][: args.en_fazla]
    print(f"{len(sayfalar)} sayfa; desene uyan {len(secilen)}")
    satirlar = [{"kaynak": args.kaynak, "sayfa": n, "metin": s} for n, s in secilen]
    satirlar.append({"kaynak": args.kaynak, "sayfa": 0, "metin": f"toplam_sayfa={len(sayfalar)} url={args.url}"})
    requests.post(f"{base}/rest/v1/kaynak_pdf_sayfalari?on_conflict=kaynak,sayfa", headers=h,
                  json=satirlar, timeout=60).raise_for_status()
    return 0


if __name__ == "__main__":
    sys.exit(main())
