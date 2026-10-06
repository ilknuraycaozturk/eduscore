# EduScor — Açık İş Listesi (Backlog)

*Son güncelleme: 06.10.2026*

Unutulmaması gereken, henüz başlanmamış ya da yarım kalmış işler. Biten iş `[x]` ile işaretlenir ve tarihi yazılır; liste silinmez.

## Puanlama (Scoring Model)

- [ ] **Resmi siteden alınan LGS kapanış puanlarını kriter skoruna çevirme kuralı** *(eklendi: 06.10.2026)*
  - Durum: Robert, Saint Benoit (430,0076), Saint Michel (411,1671) ve Sainte Pulcherie (411,8072) için 2026 kapanış puanı `institutions.lgs_taban_puani` alanında, kaynak ve güven notuyla kayıtlı. Saint Benoit, Saint Michel ve Sainte Pulcherie'nin hiç kriter skoru yok, bu yüzden sayfalarında genel skor görünmüyor.
  - Yapılacak: Ham LGS puanını yüzdelik dilime (ve `akademik_basari` skoruna) çevirecek tek bir kural tasarlamak. Kural, ileride resmi siteden eklenecek bütün okullara aynı şekilde uygulanmalı, okul okul elle yapılmamalı.
  - Açık sorular: Puan→yüzdelik dönüşümü için hangi yılın MEB dağılım tablosu kullanılacak? Robert'taki kız/erkek ayrı puan nasıl ele alınacak? Güven seviyesi (birincil kaynak) skora nasıl yansıyacak?
  - Sorumlu modüller: eduscor-scoring-model (dönüşüm), eduscor-trust-uncertainty (güven notu).

## Veri (Data Engine)

- [ ] **Koç ve İtalyan Lisesi 2026 kapanış puanı** *(eklendi: 06.10.2026)*: Koç'un sitesinde yalnızca 1. ön kayıt taban puanı (474) var. İtalyan Lisesi'nin sitesinde ise puan yok, yalnızca basında geçen 1. dönem taban puanı (465) var. İkisi de kapanış puanı olmadığı için kaydedilmedi. Okullar kapanış puanı yayımlarsa eklenecek.
- [ ] **dbtakip scraper'ını resmen kapatmak**: Teşhis tamamlandı. Detay sayfalarında yalnızca 14 özel lisede 2024 puanı var. Teşhis betikleri saklanacak.

## Arayüz / i18n

- [x] `tercih-sihirbazi.html` ve `explorer.html` sayfalarının tam İngilizce desteği *(tamamlandı: 06.10.2026)*. Aynı işte tercih sihirbazında bir hata da düzeltildi: giriş yapmış kullanıcının "Bana Göre Sırala" tercihleri, ROC geçişinden beri tanımsız bir değişken yüzünden kaydedilemiyordu.

## Hesaplar / Güvenlik (kullanıcı tarafı)

- [ ] Kullanılmayan Google OAuth istemcisini (`eduscor-web`) silmek. "Web client 1" kalacak.
- [ ] Sohbete yapıştırılmış GitHub token'ını GitHub'dan silmek.
- [ ] AdSense incelemesi: Google'ın yanıtı bekleniyor.
