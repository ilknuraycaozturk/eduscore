# EDU-SCORE-003: LGS Kapanış Puanının Akademik Başarı Skoruna Dönüştürülmesi

*Durum: UYGULANDI (06.10.2026, proje sahibi onayıyla) · Tarih: 06.10.2026 · Sorumlu modüller: eduscor-scoring-model (dönüşüm), eduscor-trust-uncertainty (güven ve kapsam kuralları)*

## 1. Sorun

`akademik_basari` skoru bugün **100 − taban yüzdelik dilim** formülüyle hesaplanıyor. Yüzdelik dilim, MEB yerleştirme verisinden (tabanpuanlari.net üzerinden ya da MEB PDF'inden) geliyor.

Kendi sınavıyla ya da kendi kayıt takvimiyle öğrenci alan bazı özel liseler ise yüzdelik dilim değil, yalnızca **LGS puanı** yayımlıyor. Bu puan son kayıt olan öğrencinin puanı, yani kapanış puanı. Bu okulların puanı `institutions.lgs_taban_puani` alanında ham değer olarak duruyor ama skora girmiyor. Bu yüzden okul sayfasında genel skor görünmüyor.

Bugün bu alanda 12 okul var:

| Güven | Okul sayısı | Okullar |
|---|---|---|
| `yuksek_birincil_kaynak` (okulun resmi sitesi, 2026) | 4 | Robert, Saint Benoit, Saint Michel, Sainte Pulcherie |
| `dusuk_dogrulanmamis_ucuncu_taraf` (dbtakip vb., yılı belirsiz) | 8 | Alman, Üsküdar Amerikan, Saint Joseph, İELEV, Hisar, Notre Dame de Sion, İzmir Amerikan, Saint Joseph İzmir |

## 2. Önerilen yöntem: aynı yılın verisinden ampirik puan→yüzdelik eşlemesi

Veritabanında, tabanpuanlari.net'ten gelen **2.455 okul kaydında hem ortalama taban puanı hem ortalama yüzdelik dilim** var. Bunlar aynı yılın (2026) MEB yerleştirme verisi. Bu çiftler puanla yüzdelik arasındaki ilişkiyi doğrudan gösteriyor. Örnek: 430 puan ≈ %5,4; 411 puan ≈ %8,2; 481 puan ≈ %0,6.

**Kural:**

1. Okulun kapanış puanı X olsun. Aynı yılın çiftlerinden puanı **X ± 5** aralığında olanlar alınır.
2. Bu komşulara yerel doğrusal regresyon uygulanır. X'teki tahmini yüzdelik dilim (ŷ) hesaplanır.
3. Skor = **100 − ŷ**. Bu, mevcut skorlarla aynı ölçek.

**Doğruluk testi (birini dışarıda bırakma, 1.238 çift, puan ≥ 300):**

| Puan aralığı | Ortalama komşu sayısı | Medyan hata (yüzdelik puanı) | %90 hata | En büyük hata |
|---|---|---|---|---|
| 300–350 | 50 | 0,029 | 0,299 | 6,97 (aykırı tek kayıt) |
| 350–400 | 86 | 0,027 | 0,062 | 1,16 |
| 400–450 | 86 | 0,021 | 0,040 | 1,11 |
| 450–500 | 39 | 0,012 | 0,020 | 0,065 |

Pratikte tahmin edilen yüzdelik dilimin hatası çoğunlukla 0,1 puanın altında. Bu, skorda 0,1 puandan az bir fark demek.

**Dört yüksek güvenli okul için ön hesap (henüz YAZILMADI):**

| Okul | 2026 kapanış puanı | Komşu | Tahmini yüzdelik | Skor |
|---|---|---|---|---|
| Robert | 481,1675 (kız; erkek 488,85) | 20 | %0,60 | 99,40 |
| Saint Benoit | 430,0076 | 88 | %5,47 | 94,53 |
| Sainte Pulcherie | 411,8072 | 98 | %8,14 | 91,86 |
| Saint Michel | 411,1671 | 97 | %8,24 | 91,76 |

**Tutarlılık kontrolü:** Saint Michel kendi sitesinde 2025 için 415 puan ↔ %7,9 yayımlamış. Eşlememiz 415 için 2026 verisiyle ≈ %7,5 veriyor. Aradaki ~0,4'lük fark yıllar arası dağılım kaymasıyla uyumlu. Bu da 4. maddedeki "aynı yıl" kuralının neden gerekli olduğunu gösteriyor.

## 3. Ne zaman dönüştürülür, ne zaman dönüştürülmez (kapsam kuralları)

Dönüşüm **yalnızca** şu koşulların hepsi sağlanınca yapılır:

1. Güven seviyesi `yuksek_birincil_kaynak` (okulun resmi sitesi ya da resmi belge). Üçüncü taraf ve doğrulanmamış puanlar ham veri olarak kalır, skora girmez. *(Trust modülü kuralı: doğrulanmamış veri doğrulanmış gibi kullanılmaz.)*
2. Puan bir **kapanış (son kayıt)** puanı olmalı. Okulun ilan ettiği başvuru eşiği bu koşulu sağlamaz. Bu yüzden Koç'un 474'lük ön kayıt eşiği dönüştürülmez.
3. Puan ile referans eşleme **aynı LGS yılına** ait olmalı.
4. X ± 5 aralığında **en az 15 komşu** bulunmalı. Bu kural, verinin seyrek olduğu uçlarda (çok yüksek ve çok düşük puanlar) tahmin yapılmasını engeller. Bugünkü 4 okulun hepsi bu koşulu sağlıyor (en az 20 komşu).
5. Okul kız ve erkek için ayrı puan yayımlıyorsa **düşük olan** (taban) kullanılır ve notta belirtilir. Bu, Robert için zaten uygulanan kuraldır.

## 4. Kayıt biçimi (izlenebilirlik)

- `institution_criteria_scores` tablosuna `akademik_basari` satırı yazılır, `score = 100 − ŷ`.
- `raw_indicators` (jsonb) alanına şunlar yazılır: `{ lgs_kapanis_puani, lgs_yili, yontem: "yerel_dogrusal_pm5", komsu_sayisi, tahmini_yuzdelik, referans: "tabanpuanlari.net 2026 MEB yerleştirme çiftleri" }`.
- `source_note` için yeni bir sabit şablon önerisi: *"Kaynak: okulun resmi sitesi (…), 2026 kapanış puanı X. Yüzdelik dilim, aynı yılın N okulluk MEB yerleştirme verisinden tahmin edildi (%ŷ). Resmi yüzdelik değil, tahmindir."* Okul detay sayfasındaki İngilizce not çevirisine bu şablon da eklenir.
- Ardından yalnızca etkilenen okulların `success_score_v2` ve `evidence_coverage_v2` alanları yeniden hesaplanır. Arayüz bu alanları okuyor, kendisi hesaplamıyor (EDU-GOV-001).

## 5. Değerlendirilen alternatifler

| Seçenek | Neden seçilmedi |
|---|---|
| MEB'in resmi puan→yüzdelik tablosu | Ideal kaynak olurdu, ama yayımlanıp yayımlanmadığını doğrulamadık. Bulunursa bu yöntemin yerini alır. |
| Puanı 0–100'e doğrusal ölçeklemek (puan / 5) | Mevcut yüzdelik tabanlı skorlarla aynı ölçekte olmaz. 430 puan 86 olurdu, oysa bu puan yüzdelik olarak %5'e, yani ~95'e karşılık geliyor. |
| Dönüştürmeyip yalnızca ham puanı göstermek | Bugünkü durum. Bu okullar genel skordan ve sıralamalardan sistematik olarak dışarıda kalıyor. |

## 6. Bilinen sınırlar ve riskler

- **Tahmin, ölçüm değil:** Yüzdelik dilim resmi değil, tahmini. Notta ve detay sayfasında bu açıkça yazılır.
- **Ortalama etkisi:** Referans çiftler okul düzeyinde ortalama (birden çok programlı okullarda programların ortalaması). Puan–yüzdelik ilişkisi bu aralıkta neredeyse doğrusal olduğu için etkisi küçük, ama sıfır değil.
- **Tavan sıkışması:** En seçkin okullar 99,x civarında toplanıyor. Bu, mevcut ölçeğin de özelliği, yeni bir sorun değil.
- **Goodhart riski:** Okulların kendi yayımladığı puanlar artık skoru etkiliyor. Bu yüzden yalnızca kapanış puanı kabul ediliyor (madde 3.2) ve kaynak bağlantısı kaydediliyor (doğrulanabilirlik).
- **Yıllık bakım:** Her yeni LGS yılında eşleme o yılın verisiyle yeniden kurulmalı. Eski yılın puanları yeni yılın eşlemesiyle dönüştürülmez.

## 7. Uygulama adımları

1. Dönüşümü SQL ile 4 yüksek güvenli okula uygula. Sonuçları yukarıdaki ön hesapla karşılaştır.
2. Yeni `source_note` şablonunu okul detay sayfasının İngilizce çevirisine ekle.
3. 4 okulun `success_score_v2` / `evidence_coverage_v2` değerlerini yeniden hesapla. Okul detay sayfasında kontrol et.
4. Bu belgeyi "UYGULANDI" olarak güncelle ve iş listesindeki maddeyi kapat.

## 8. Uygulama sonucu (06.10.2026)

**Ön koşul olarak kopya kayıtlar birleştirildi.** Saint Benoit, Saint Michel, Sainte Pulcherie, İtalyan ve Notre Dame de Sion veritabanında ikişer kez vardı. 17 Ağustos'taki MEB biçimli kayıtlar ("İSTANBUL - BEYOĞLU - Özel …") korundu. Bu kayıtlarda ilçe, tür ("Yabancı Özel Lise") ve üniversite skoru vardı. 16 Eylül'deki TOZOK kopyalarından web sitesi, telefon, TOZOK işareti ve LGS puanı alanları bu kayıtlara kopyalandı. Kopyaların silinmesi henüz yapılmadı (bkz. iş listesi).

Dört okula `akademik_basari` satırı yazıldı (`trust_model_version = 'EDU-SCORE-003'`). Değerler ön hesapla birebir aynı çıktı:

| Okul | Tahmini yüzdelik | Akademik skor | Genel skor (v2) | Kanıt kapsamı |
|---|---|---|---|---|
| Robert | %0,60 | 99,40 | 99,6 | %42 (2 kriter) |
| Saint Benoit | %5,47 | 94,53 | 95,7 | %42 (2 kriter) |
| Sainte Pulcherie | %8,14 | 91,86 | 94,6 | %42 (2 kriter) |
| Saint Michel | %8,24 | 91,76 | 91,8 | %42 (2 kriter) |

Okul detay sayfasındaki İngilizce kaynak notu çevirisine yeni şablon eklendi.

**Yan bulgu:** `success_score_v2` için otomatik yeniden hesaplama yok. Günlük veri yüklemeleri yeni kriter satırı eklediğinde genel skor eski kalıyor. Bugün ~75 okulda saklanan değerin güncel kriter satırlarıyla uyuşmadığı görüldü. İş listesine eklendi.
