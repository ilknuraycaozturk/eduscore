"""MEB taramasının kapsama kontrolü.

scrape_meb_schools.py her sorgu için MEB sayfasının bildirdiği toplamı
("N kayıttan") ve çekilen satır sayısını data/meb_coverage.json dosyasına
yazar. Bu betik o dosyayı okur; en az bir sorguda toplam okunamamışsa,
sayılar uyuşmuyorsa ya da ilçe listesi bulunamamışsa çıkış kodu 1 ile
biter. Böylece eksik tarama iş akışında kırmızı görünür, sessizce geçmez.

Kullanım: python check_meb_coverage.py data/meb_coverage.json [data/meb_load_summary.json]
"""
import json
import sys
from pathlib import Path


def main() -> int:
    path = Path(sys.argv[1] if len(sys.argv) > 1 else "data/meb_coverage.json")
    if not path.exists():
        print(f"HATA: Kapsama dosyası yok: {path}")
        return 1

    rows = json.loads(path.read_text(encoding="utf-8"))
    sorunlu = []
    toplam_beklenen = toplam_cekilen = 0
    for r in rows:
        beklenen, cekilen = r.get("beklenen"), r.get("cekilen", 0)
        toplam_cekilen += cekilen
        if isinstance(beklenen, int):
            toplam_beklenen += beklenen
        if beklenen is None or beklenen != cekilen or r.get("durum") not in ("ok", "tablo_bos"):
            # Tablo boş ve MEB de 0 diyorsa sorun değil
            if r.get("durum") == "tablo_bos" and beklenen == 0 and cekilen == 0:
                continue
            sorunlu.append(r)

    print(f"Sorgu sayısı: {len(rows)} | MEB'e göre toplam: {toplam_beklenen} | çekilen: {toplam_cekilen}")
    if len(sys.argv) > 2 and Path(sys.argv[2]).exists():
        ozet = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
        print("Yükleme özeti: " + json.dumps(ozet, ensure_ascii=False))

    if sorunlu:
        print(f"\nKAPSAMA HATASI: {len(sorunlu)} sorguda eksik/uyuşmayan sonuç:")
        for r in sorunlu[:200]:
            print(f"  il={r.get('il_kodu')} ilce={r.get('ilce_kodu')} beklenen={r.get('beklenen')} "
                  f"cekilen={r.get('cekilen')} durum={r.get('durum')}")
        return 1

    print("Kapsama tamam: tüm sorgularda çekilen satır sayısı MEB'in bildirdiği toplamla eşit.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
