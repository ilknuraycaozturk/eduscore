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

## Üçüncü ölçüm (23.10.2026)

- 2017 ilçe referansında olmayan iki ilçe eklendi ve tarandı: Hakkari–Derecik (MEB kodu 7, 48 kurum) ve Artvin–Kemalpaşa (kod 9, 11 kurum). Kodlar tarama sonucundaki okul adlarıyla ("HAKKARİ - DERECİK - …", "ARTVİN - KEMALPAŞA - …") doğrulandı.
- Tarayıcıya geçici sayfa hataları için 3 denemeye kadar yeniden deneme eklendi; düşük kalan 8 il yeniden tarandı, kapsama kontrolü yeşil (MEB'in bildirdiği toplam = çekilen).
- **Resmi ilkokul kapsaması: %98,7 (22.687 / 22.980); 81 ilin 77'si ≥ %95.**
- %95 altında kalan 4 il (Edirne %91, Ordu %94, Bilecik %94, Gümüşhane %94): MEB listesi bu illerde eksiksiz çekildi (toplamlar tutuyor). Kalan fark, MEB'in güncel okul listesi ile Haziran 2025 istatistiği arasındaki farktan geliyor olabilir (kapanan/birleşen okullar); doğrulanmadı, bilinen sınırlama olarak kaydedildi.

## Dördüncü ölçüm (23.10.2026, özel okullar eklendikten sonra)

Özel okullar ÖOKGM'nin resmî kurum listesinden (özel okul, 81 il) alındı. Yükleyici MEB yükleyicisiyle aynı kurallara getirildi: ilçe kendi ilinin altına açılıyor (önceden hepsi Ankara'nın altına açılıyordu), eşleştirme yalnızca aynı il/ilçe içinde ve ad birebir, ÖOKGM'nin bildirdiği toplam ("N adet kurum bulundu") ile çekilen sayı her ilde karşılaştırılıyor. 81 ilin hepsinde toplam = çekilen; yazma hatası 0, ili bulunamayan kayıt 0.

Kopya kontrolü (Ankara, İstanbul, İzmir): aynı ilde benzer adlı 50 çift incelendi. Hepsi ya özel okul ile aynı adı taşıyan farklı bir resmî okul ("Özel Üsküdar İlkokulu" / "Üsküdar İlkokulu") ya da farklı ilçedeki ayrı kampüsler. Aynı okulun ikinci kaydı bulunmadı.

Referans ayrımı (Tablo 2.4.b): ortaokul 18.878 = resmî 16.650 + özel 2.228. Resmî ortaokulların 898'i "İmam Hatip Lisesi bünyesinde İmam Hatip Ortaokulu"; bunlar MEB okul listesinde ayrı kurum olarak görünmüyor, bu yüzden listelenebilir resmî ortaokul 15.752.

| Kademe | MEB | Bizde | Kapsama |
|---|---|---|---|
| İlkokul (toplam) | 25.099 | 24.876 | %99,1 |
| – resmî | 22.980 | 22.695 | %98,8 |
| – özel | 2.119 | 2.181 | %102,9 |
| Ortaokul (toplam) | 18.878 | 17.738 | %94,0 |
| – resmî (listelenebilir) | 15.752 | 15.499 | %98,4 |
| – özel | 2.228 | 2.239 | %100,5 |
| Ortaöğretim | 12.423 | 13.221 | %106,4 |

- İlkokulda 81 ilin 77'si %95–105 aralığında; altında kalanlar Kırşehir %94, Edirne, Gümüşhane, Ordu (%94,5–95).
- Özel ilkokul/ortaokuldaki küçük fazlalık, ÖOKGM'nin güncel listesi ile Haziran 2025 istatistiği arasındaki tarih farkından gelebilir (doğrulanmadı).
- Özel/resmî ayrımı okul adındaki "Özel" sözcüğüne göre yapıldı; kayıtta ayrı bir alan yok.
- Ortaöğretimdeki fazlalığın nedeni hâlâ belirlenmedi (açık iş).
- Bu çalıştırmalarla 11.318 özel kurum eklendi (anaokulu ve lise dahil); 11.307'sinin koordinatı yok, yalnızca 106'sının MEB sitesi var. ÖOKGM adresleri kayıtta.

## Ortaöğretim fazlalığı ve birleştirme (23.10.2026)

Fazlalık (13.221 / 12.423) türlere göre incelendi (Tablo 2.6). Nedenler:

- **Kopya lise kayıtları (744).** Ağustos'ta LGS kaynağından gelen "İL - Ad" biçimli 580 kayıt ve Temmuz–Ağustos'tan kalan kurum kodsuz 164 kayıt, MEB listesinden gelen kayıtlarla aynı okul; eski adlarda yalnızca alan sözcüğü eksik ("Ahi Evran MTAL" / "Ahi Evran Ticaret MTAL"). Kural: aynı il (kodsuzlarda aynı ilçe) ve tür; eski adın tüm sözcükleri MEB adında var; MEB adındaki fazla sözcükler yalnızca ilçe adı ya da Ticaret, Turizm, Denizcilik, Sağlık, Tarım, Kız; tek aday. Birleştirildi: eski kayıt korundu, MEB adı, ilçesi, kurum kodu, sitesi ve e-postası aktarıldı, kopya silindi. Yedek: `_yedek_20261023_birlestirme`, `_yedek_20261023_birlestirme_bagli`, çift listesi `_birlestirme_20261023`.
- **Kriter puanı çakışmaları (291).** Aynı kriter iki kayıtta da vardı. Her kriterde güven puanı (`trust_score_computed`) yüksek olan, eşitse kaynak tarihi yeni olan tutuldu: 140 kriterde MEB kopyasındaki 2026 verisi (güven 0,88) eski kaydın 2022 verisinin (0,72) yerine geçti; seçim listesi `_birlestirme_20261023_kriter_secim`. Etkilenen 140 okulun genel skoru tetikleyiciyle yeniden hesaplandı.
- **Milletlerarası okullar (193 / 81).** Bizdeki tür ilkokul ve ortaokul kampüslerini de içeriyor; MEB yalnızca lise kısmını sayıyor. Kayıt hatası değil.
- **Çok Programlı Anadolu Lisesi (581).** Bizde "Anadolu Lisesi" türünde, MEB mesleki kategoride sayıyor; toplamı etkilemiyor.

Sonuç: **ortaöğretim 12.477 (%100,4)**. Kalan 96 "İL - Ad" biçimli lise kaydının 29'u belirsiz çift; 67'si MEB okul listesinde karşılığı olmayan, meb.k12.tr sitesi olan gerçek okullar (ör. Sinop–Durağan ve Trabzon–Şalpazarı'nda MEB listesi hiç lise döndürmüyor). MEB listesinin bazı ilçelerde lise vermemesi ayrıca ölçülecek.
