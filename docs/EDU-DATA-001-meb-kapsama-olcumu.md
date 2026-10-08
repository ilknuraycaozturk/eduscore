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

## İkinci ölçüm (08.10.2026, düzeltilmiş tarama sonrası)

Düzeltmeler (commit `fd937b8`, `f463246`): toplu tarama ilçe ilçe; kopya eşleştirmesi yalnızca aynı il/ilçe içinde ve ad birebir; coğrafi kodlama kaydın kendi iliyle; bütçe dolunca kurumlar koordinatsız ekleniyor. 81 il, 6 paralel çalıştırma + Tunceli denemesi.

| Kademe | MEB | Bizde | Kapsama |
|---|---|---|---|
| İlkokul | 25.099 | 22.920 | %91,3 |
| Ortaokul | 18.878 | 15.768 | %83,5 |
| Ortaöğretim | 12.423 | 15.193 | %122,3 |

- **MEB okul listesi yalnızca resmi okulları veriyor.** Resmi ilkokulda (Tablo 2.5.a "Resmi" sütunu, 22.980) kapsama **%98,5**; 81 ilin 73'ü %95–105 aralığında. Eksik kalan ~2.100 ilkokul büyük ölçüde özel okul; özel okullar için ayrı kaynak gerekiyor.
- %95 altında kalan iller (resmi ilkokul): Hakkari %84, Sinop %84, Trabzon %89, Artvin %90, Edirne %91, Ordu %94, Bilecik %94, Gümüşhane %94. Olası nedenler: 2017 ilçe referansında olmayan yeni ilçeler (ör. Hakkari–Derecik, 2018) ve kapsama kontrolünün kırmızı verdiği iki parti (il kodları 6,24,31,32,36,41,54,55,57,60,64,68,69,78 ve 7,10,17,19,25,29,37,38,42,43,49,53,61,77).
- Ortaokul ve ortaöğretim için il bazında resmi/özel ayrımı bu tablolarda yok; ortaöğretimdeki fazlalığın (~2.770) nedeni henüz belirlenmedi (birebir aynı adlı kopya yalnızca 45).
- Koordinatsız kurum: 54.173. Ankara dışında olup koordinatı Ankara'da görünen eski kayıt: 4.261.
