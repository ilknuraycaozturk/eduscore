# EduScor — Açık İş Listesi (Backlog)

*Son güncelleme: 06.10.2026*

Unutulmaması gereken, henüz başlanmamış ya da yarım kalmış işler. Biten iş `[x]` ile işaretlenir ve tarihi yazılır; liste silinmez.

## Puanlama (Scoring Model)

- [x] **Resmi siteden alınan LGS kapanış puanlarını kriter skoruna çevirme kuralı** *(tamamlandı: 06.10.2026)*. Tasarım ve sonuç: `docs/EDU-SCORE-003-lgs-puan-skor-donusumu.md`. Robert, Saint Benoit, Saint Michel ve Sainte Pulcherie'ye uygulandı.
- [ ] **Genel skoru (`success_score_v2`) otomatik güncel tutmak** *(eklendi: 06.10.2026)*: Günlük yüklemeler kriter satırı ekleyince genel skor ve kanıt kapsamı yeniden hesaplanmıyor. ~75 okulda eski değer duruyor. Seçenekler: her yükleme sonunda yeniden hesaplama adımı ya da veritabanı tetikleyicisi.

## Veri (Data Engine)

- [ ] **Koç ve İtalyan Lisesi 2026 kapanış puanı** *(eklendi: 06.10.2026)*: Koç'un sitesinde yalnızca 1. ön kayıt taban puanı (474) var. İtalyan Lisesi'nin sitesinde ise puan yok, yalnızca basında geçen 1. dönem taban puanı (465) var. İkisi de kapanış puanı olmadığı için kaydedilmedi. Okullar kapanış puanı yayımlarsa eklenecek.
- [ ] **dbtakip scraper'ını resmen kapatmak**: Teşhis tamamlandı. Detay sayfalarında yalnızca 14 özel lisede 2024 puanı var. Teşhis betikleri saklanacak.

- [ ] **TOZOK kopyalarının silinmesi** *(eklendi: 06.10.2026)*: 5 okulun 16 Eylül TOZOK kopyası (İtalyan, Notre Dame de Sion, Saint Benoit, Saint Michel, Sainte Pulcherie) asıl kayıtlarla birleştirildi, verileri aktarıldı. Kopyaların kendisi henüz silinmedi, silme komutu bu oturumda onaylanmadı. Kopyalara başka tablodan bağlantı yok.
- [ ] **Diğer TOZOK kopyalarını taramak** *(eklendi: 06.10.2026)*: 79 TOZOK kaydının bir kısmı MEB biçimli kayıtların kopyası olabilir; isim biçimi farklı olduğu için önceki temizlikte yakalanmadılar. Saint Joseph ayrıca kontrol edilmeli: TOZOK kaydının telefonu 0216 (Anadolu yakası), eski kayıt ise Şişli diyor.

## Arayüz / i18n

- [x] `tercih-sihirbazi.html` ve `explorer.html` sayfalarının tam İngilizce desteği *(tamamlandı: 06.10.2026)*. Aynı işte tercih sihirbazında bir hata da düzeltildi: giriş yapmış kullanıcının "Bana Göre Sırala" tercihleri, ROC geçişinden beri tanımsız bir değişken yüzünden kaydedilemiyordu.

## Hesaplar / Güvenlik (kullanıcı tarafı)

- [ ] Kullanılmayan Google OAuth istemcisini (`eduscor-web`) silmek. "Web client 1" kalacak.
- [ ] Sohbete yapıştırılmış GitHub token'ını GitHub'dan silmek.
- [ ] AdSense incelemesi: Google'ın yanıtı bekleniyor.
