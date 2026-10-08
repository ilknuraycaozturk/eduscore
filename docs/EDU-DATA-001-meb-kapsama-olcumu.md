# EDU-DATA-001 — MEB okul verisi kapsama ölçümü (kabul ölçüsü)

*Tarih: 08.10.2026 · Durum: başlangıç ölçümü (baseline)*

## Amaç

"Tarama bitti" demenin ölçüsü: bizdeki okul sayısını MEB'in resmi istatistiğiyle il ve kademe bazında karşılaştırmak. İş akışlarının yeşil bitmesi verinin tam olduğunu göstermez.

## Referans

- Kaynak: MEB Strateji Geliştirme Başkanlığı, *Millî Eğitim İstatistikleri – Örgün Eğitim 2024/'25* (https://sgb.meb.gov.tr/istatistik_k/2425.pdf).
- İl (İBBS 3. düzey) bazında okul sayıları: Tablo 2.5.a (ilkokul), 2.5.b (ortaokul), 2.11 (ortaöğretim). Dosya: `data/reference/meb_2024_25_il_okul_sayilari.csv`.
- Doğrulama: üç tablonun il toplamları Türkiye toplamıyla birebir tutuyor (25.099 / 18.878 / 12.423). Ortaöğretimde Tokat satırı PDF'ten okunamadı; değeri (109) Türkiye toplamından çıkarılarak bulundu.
- Okul öncesi il tablosu (2.2) ana sınıfı olan okulları da saydığı için (39.570) bizim "anaokulu" türüyle karşılaştırılamaz; okul öncesi yalnızca ülke düzeyinde izlenir (bağımsız okul öncesi: 17.640).

## Kabul ölçüsü

1. Her ilde ilkokul, ortaokul ve ortaöğretim sayısı MEB referansının en az %95'i.
2. Scraper'ın her sorgusunda MEB sayfasının bildirdiği toplam ("N kayıttan") ile çekilen satır sayısı eşit; değilse çalıştırma başarısız sayılır.

## Başlangıç ölçümü (08.10.2026)

| Kademe | MEB | Bizde | Kapsama |
|---|---|---|---|
| İlkokul | 25.099 | 2.240 | %8,9 |
| Ortaokul | 18.878 | 1.815 | %9,6 |
| Ortaöğretim | 12.423 | 8.586 | %69,1 |
| **Toplam** | **56.400** | **12.641** | **%22,4** |

- 81 ilin hiçbiri %95 ölçüsünü karşılamıyor. En yüksek: Bayburt %83, Ankara %68.
- 37 ilde hiç ilkokul ve ortaokul kaydı yok (ör. Şanlıurfa 0 / 1.334, Van 0 / 884); İstanbul'da 1.656 ilkokuldan yalnızca 3'ü var. Liseler başka kaynaklardan geldiği için bu illerde yalnızca lise var.
- Ortaöğretim sayısı kopya kayıtlar içerebilir; gerçek kapsama daha düşük olabilir.

## Bulunan nedenler

- Toplu (`--il-kodu-listesi`) ve aylık otomatik tarama, MEB'in sunucu tarafında kırptığı "tüm il" sorgusunu kullanıyor (kodun kendi yorumu: Ankara'da 2.533 kurum yerine 181 kayıt). İlçe ilçe sorgu yalnızca tek il (`--all-ilceler`) yolunda var.
- Aylık parti ilerlemesi (`meb_next_il_kodu`) 18.08.2026'dan beri 37'de takılı.
- İlçe ilçe taranan Ankara'da bile ilkokul/ortaokulun ~%43'ü eksik; kayıp tarama mı yükleme (tür eşleştirme, kopya eleme) adımında mı henüz bilinmiyor.
