# EduScor — Açık İş Listesi (Backlog)

*Son güncelleme: 06.10.2026*

Unutulmaması gereken, henüz başlanmamış ya da yarım kalmış işler. Biten iş `[x]` ile işaretlenir ve tarihi yazılır; liste silinmez.

## Puanlama (Scoring Model)

- [x] **Resmi siteden alınan LGS kapanış puanlarını kriter skoruna çevirme kuralı** *(tamamlandı: 06.10.2026)*. Tasarım ve sonuç: `docs/EDU-SCORE-003-lgs-puan-skor-donusumu.md`. Robert, Saint Benoit, Saint Michel ve Sainte Pulcherie'ye uygulandı.
- [x] **Genel skoru (`success_score_v2`) otomatik güncel tutmak** *(tamamlandı: 06.10.2026)*. Veritabanı tetikleyicisi kuruldu (`docs/sql/EDU-SCORE-004-v2-otomatik-guncelleme.sql`). Kriter puanı eklenince, değişince ya da silinince okulun genel skoru ve kanıt kapsamı kendiliğinden yeniden hesaplanıyor. Eski kalan ~75 okul ve hiç hesaplanmamış 35 okul bir kez düzeltildi.

## Veri (Data Engine)

- [ ] **Koç ve İtalyan Lisesi 2026 kapanış puanı** *(eklendi: 06.10.2026)*: Koç'un sitesinde yalnızca 1. ön kayıt taban puanı (474) var. İtalyan Lisesi'nin sitesinde ise puan yok, yalnızca basında geçen 1. dönem taban puanı (465) var. İkisi de kapanış puanı olmadığı için kaydedilmedi. Okullar kapanış puanı yayımlarsa eklenecek.
- [ ] **dbtakip scraper'ını resmen kapatmak**: Teşhis tamamlandı. Detay sayfalarında yalnızca 14 özel lisede 2024 puanı var. Teşhis betikleri saklanacak.

- [x] **TOZOK kopyalarının silinmesi** *(tamamlandı: 06.10.2026)*. 5 okulun (İtalyan, Notre Dame de Sion, Saint Benoit, Saint Michel, Sainte Pulcherie) TOZOK kopyaları, verileri asıl kayıtlara aktarıldıktan sonra silindi.
- [ ] **Diğer TOZOK kopyalarını taramak** *(eklendi: 06.10.2026)*: 79 TOZOK kaydının bir kısmı MEB biçimli kayıtların kopyası olabilir; isim biçimi farklı olduğu için önceki temizlikte yakalanmadılar. Saint Joseph ayrıca kontrol edilmeli: TOZOK kaydının telefonu 0216 (Anadolu yakası), eski kayıt ise Şişli diyor.

## Arayüz / i18n

- [x] `tercih-sihirbazi.html` ve `explorer.html` sayfalarının tam İngilizce desteği *(tamamlandı: 06.10.2026)*. Aynı işte tercih sihirbazında bir hata da düzeltildi: giriş yapmış kullanıcının "Bana Göre Sırala" tercihleri, ROC geçişinden beri tanımsız bir değişken yüzünden kaydedilemiyordu.

## Hesaplar / Güvenlik (kullanıcı tarafı)

- [ ] Kullanılmayan Google OAuth istemcisini (`eduscor-web`) silmek. "Web client 1" kalacak.
- [ ] Sohbete yapıştırılmış GitHub token'ını GitHub'dan silmek.
- [ ] AdSense incelemesi: Google'ın yanıtı bekleniyor.
