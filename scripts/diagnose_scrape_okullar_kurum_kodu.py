"""
diagnose_scrape_okullar_kurum_kodu.py
========================================
TEK SEFERLİK TANI SCRIPT'İ.

AMAÇ: scrape_meb_schools.py'nin GERÇEK scrape_okullar() fonksiyonunu
(production'da kullanılan aynı kod yolu) çağırıp, dönen sonuçlarda
meb_kurum_kodu alanının GERÇEKTEN dolu gelip gelmediğini kontrol eder.
Supabase'e HİÇBİR ŞEY YAZMAZ.
"""
import sys
sys.path.insert(0, "scripts")

from scrape_meb_schools import scrape_okullar

def main():
    print("scrape_okullar(il_kodu='6', ilce_kodu='27') çağrılıyor (Ankara/Etimesgut)...\n")
    results = scrape_okullar(il_kodu="6", ilce_kodu="27")
    print(f"Toplam {len(results)} kurum döndü.\n")

    print("=== İlk 10 kurumun meb_kurum_kodu durumu ===")
    dolu_sayisi = 0
    for r in results[:10]:
        kod = r.get("meb_kurum_kodu")
        if kod:
            dolu_sayisi += 1
        print(f"  {r.get('raw_name', '')[:50]!r:52s} -> meb_kurum_kodu={kod!r}, website={r.get('website')!r}")

    print(f"\nToplam sonuçta (tüm {len(results)}) meb_kurum_kodu dolu olan sayısı:")
    all_dolu = sum(1 for r in results if r.get("meb_kurum_kodu"))
    print(f"  {all_dolu} / {len(results)}")

    print("\n=== dict anahtarları (ilk kayıt) ===")
    if results:
        print(f"  {list(results[0].keys())}")

if __name__ == "__main__":
    main()
