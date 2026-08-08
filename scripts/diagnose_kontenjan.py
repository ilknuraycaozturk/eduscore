"""
diagnose_kontenjan.py
=======================
PDF'in gerçek satır yapısını görmek için teşhis script'i - kontenjan
sütununun tam olarak nerede olduğunu bulmak amacıyla.
"""
import re
import sys
from pathlib import Path

import requests

try:
    import pdfplumber
except ImportError:
    print("pdfplumber kurulu değil.")
    sys.exit(1)

PDF_URL = "https://www.meb.gov.tr/meb_iys_dosyalar/2022_07/25103752_2022_ilk_yerlestirme_taban_tavan_yerlesme_bilgileri.pdf"

LINE_RE = re.compile(
    r"^(?P<kod>\d{4,6})\s+"
    r"(?P<il>[A-ZÇĞİÖŞÜ]+(?:\s[A-ZÇĞİÖŞÜ]+)*?)\s+"
    r"(?P<ilce>[A-ZÇĞİÖŞÜ]+(?:\s[A-ZÇĞİÖŞÜ]+)*?)\s+"
    r"(?P<rest>.+)$"
)

resp = requests.get(PDF_URL, timeout=60, headers={"User-Agent": "Mozilla/5.0 (EduScor-Pilot/1.0)"})
resp.raise_for_status()
Path("data/lgs.pdf").parent.mkdir(parents=True, exist_ok=True)
Path("data/lgs.pdf").write_bytes(resp.content)
print(f"PDF indirildi ({len(resp.content) / 1024:.0f} KB)")

found = 0
with pdfplumber.open("data/lgs.pdf") as pdf:
    for page in pdf.pages:
        text = page.extract_text() or ""
        for raw_line in text.split("\n"):
            line = raw_line.strip()
            if not line or "TERCİH" in line or "TABAN PUAN" in line or "Yılı Merkezi" in line:
                continue
            m = LINE_RE.match(line)
            if not m:
                continue
            if "ANKARA" in m.group("il") and "Fen Lisesi" in m.group("rest") and found < 5:
                print(f"\n--- HAM SATIR ---\n{line}")
                print(f"--- REST GRUBU ---\n{m.group('rest')}")
                found += 1
        if found >= 5:
            break

print(f"\nTOPLAM {found} örnek satır gösterildi.")
