# EDU-SCORE-005 — Konum güveninin puanlamada kullanımı (tasarım önerisi)

*Tarih: 30.10.2026 · Durum: KARAR VERİLDİ (Ayca, 30.10.2026) — kod yazılmadı*

## Karar (30.10.2026, Ayca)

- **Toplu taşıma yakınlığı** (OSM'den, ücretsiz) ve **servis bilgisi** (yalnızca okulun kendi beyanı) **kurumsal puana girmez**.
- İkisi de yalnızca **eşleştirme/öneri** tarafında kullanılır (eduscor-match-decision): ailenin konumuna göre öneri yaparken ve aile kendi kişisel puanını oluştururken.
- Bu nedenle bu belgedeki "Öneri (B)" kurumsal puan için uygulanmayacak; konum güveni tablosu eşleştirme modülünde (uzaklık ve durak yakınlığının ± belirsizliği) kullanılmak üzere aynen geçerli.
- **Sonuç (onay bekliyor):** `konum_ulasim` (ağırlık 5) şu an her kurumun kanıt kapsamı paydasında (`criteria_available_v2`: lise 100, diğer 43) sayılıyor. Kurumsal olmayacağı için paydadan çıkarılması gerekir (lise 95, diğer 38); böylece hiçbir okul tamamlayamayacağı bir kriter yüzünden "eksik kanıtlı" görünmez. Genel skor (ağırlıklı ortalama) değişmez, çünkü bu kriterde hiç puan yok.

## Mevcut durum (ölçüm)

- `institutions.konum_kaynagi` / `konum_guven` dolu: okul sitesi = yüksek; OSM okul nesnesi ve LocationIQ okul adıyla = orta; LocationIQ adres (sokak düzeyi) ve mahalle merkezi = düşük; eski/bilinmeyen = düşük.
- "Konum, Ulaşım ve Çevre" kriterinde (`konum_ulasim`, ağırlık 5) **hiç puan yok** (0 kayıt).
- Genel skor (`eduscor_recompute_v2`): mevcut kriterlerin ağırlıklı ortalaması. Kriter satırlarındaki güven alanları (`trust_score_computed`) genel skora girmiyor; eksik kriter yalnızca kanıt kapsamını (`evidence_coverage_v2`) düşürüyor.

## Kavramsal ayrım

1. **Ham koordinat** kurumsal kalite göstergesi değildir; bir göstergeyi *hesaplamak* için girdidir.
2. **Koordinattan türetilen göstergeler** (ör. 500 m içindeki toplu taşıma durağı sayısı) kurumsal puana girebilir. Güvenilirlikleri koordinatın güveninden gelir.
3. **Kullanıcıya uzaklık** kurumsal puan değildir; eşleştirme modülünün işidir (eduscor-match-decision). Konum güveni orada "± yarıçap" olarak kullanılmalıdır.

## Karşılaştırılan seçenekler

| | A — Puana hiç katma | B — Güvene göre hesapla ya da hesaplama (öneri) | C — Belirsizliği aralık olarak yay |
|---|---|---|---|
| Ne yapar | Konum güveni yalnızca haritada ve eşleştirmede kullanılır | Koordinattan gösterge hesaplanır; güven düşükse gösterge geniş tamponla hesaplanır ve satırın güveni düşük yazılır; mahalle merkezinde hesaplanmaz | Gösterge, konum hatası kadar kaydırılmış noktalarda hesaplanır; puan [alt, üst] aralığı olarak verilir |
| Artı | Basit, yanlış konumun puanı bozma riski yok | Şeffaf; yanlış yerdeki okul için uydurma gösterge üretmez | Belirsizliği en doğru yansıtır |
| Eksi | Kriter boş kalır | Eşikler (tampon, güven değerleri) varsayım | Hesap yükü, arayüzde anlatması zor; genel skor tek sayı olduğu için şimdilik karşılığı yok |

## Öneri (B) — hipotez, doğrulanmadı

| konum_guven / kaynak | Tipik hata (varsayım) | Gösterge hesabı | Kriter satırı güveni (varsayım) |
|---|---|---|---|
| yüksek (okul sitesi) | < 100 m | 500 m tampon | 0,9 |
| orta (OSM / adla arama) | 100–300 m | 500 m tampon | 0,7 |
| düşük (sokak düzeyi) | 300–800 m | 800 m tampon | 0,4 |
| düşük (mahalle merkezi, eski/bilinmiyor) | > 800 m | **hesaplanmaz** (kriter eksik sayılır) | — |

- Genel skor formülü değişmez. Eksik kriter, puanı düşürmez, yalnızca kanıt kapsamını düşürür. Böylece konumu belirsiz okul cezalandırılmaz, ama "az kanıtla puanlandı" olarak görünür.
- Güven değerleri şimdilik yalnızca kriter satırına yazılır. Genel skorun güvene göre ağırlıklandırılması ayrı bir karar (tüm kriterleri etkiler, bu notun kapsamı dışında).

## Doğrulama planı (onaydan sonra)

1. Yüksek güvenli 200 okulun koordinatını her güven sınıfının tipik hatası kadar rastgele kaydır, göstergeyi yeniden hesapla.
2. Asıl ve kaydırılmış değerler arasında sıra korelasyonu (Spearman) ve okul başına mutlak fark ölç.
3. Bir sınıfta korelasyon < 0,8 ise o sınıf için gösterge hesaplanmaz (tablodaki eşikler ölçüme göre güncellenir).

## Açık sorular (karar gerekir)

- Hangi gösterge(ler)? Aday: toplu taşıma durağı yakınlığı (OSM, ücretsiz), servis bilgisi (okul beyanı). "Çevre güvenliği" için güvenilir açık veri bilinmiyor.
- Bu kriter kurumsal puana girmeli mi, yoksa yalnızca bilgi olarak mı gösterilmeli? (Ulaşım, ailenin konumuna göre değişen bir uygunluk konusu da olabilir.)
