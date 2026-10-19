# EduScor — Açık İş Listesi (Backlog)

*Son güncelleme: 19.10.2026*

Unutulmaması gereken, henüz başlanmamış ya da yarım kalmış işler. Biten iş `[x]` ile işaretlenir ve tarihi yazılır; liste silinmez.

## Puanlama (Scoring Model)

- [x] **Resmi siteden alınan LGS kapanış puanlarını kriter skoruna çevirme kuralı** *(tamamlandı: 06.10.2026)*. Tasarım ve sonuç: `docs/EDU-SCORE-003-lgs-puan-skor-donusumu.md`. Robert, Saint Benoit, Saint Michel ve Sainte Pulcherie'ye uygulandı.
- [x] **Genel skoru (`success_score_v2`) otomatik güncel tutmak** *(tamamlandı: 06.10.2026)*. Veritabanı tetikleyicisi kuruldu (`docs/sql/EDU-SCORE-004-v2-otomatik-guncelleme.sql`). Kriter puanı eklenince, değişince ya da silinince okulun genel skoru ve kanıt kapsamı kendiliğinden yeniden hesaplanıyor. Eski kalan ~75 okul ve hiç hesaplanmamış 35 okul bir kez düzeltildi.
- [x] **`success_score_v2_computed_at` otomatik güncellenmiyordu** *(tamamlandı: 06.10.2026)*. `eduscor_recompute_v2` artık skorla birlikte hesaplanma tarihini de yazıyor (migration: `recompute_v2_sets_computed_at`). Skor mantığı ve yetkiler değişmedi; geri alınan bir testle doğrulandı. Mevcut eski tarihler toplu güncellenmedi, okullar bir sonraki skor değişikliğinde doğal olarak güncellenecek. Tarih alanı sitede gösterilmiyor. Depodaki iki EDU-SCORE-004 SQL dosyası da aynı satırla güncellendi (commit `2d897de`).

## Veri (Data Engine)

- [ ] **Koç ve İtalyan Lisesi 2026 kapanış puanı** *(eklendi: 06.10.2026)*: Koç'un sitesinde yalnızca 1. ön kayıt taban puanı (474) var. İtalyan Lisesi'nin sitesinde ise puan yok, yalnızca basında geçen 1. dönem taban puanı (465) var. İkisi de kapanış puanı olmadığı için kaydedilmedi. Okullar kapanış puanı yayımlarsa eklenecek.
- [x] **dbtakip scraper'ını resmen kapatmak** *(tamamlandı: 08.10.2026)*. Teşhis tamamlandı: detay sayfalarında yalnızca 14 özel lisede 2024 puanı var. Zamanlanmış bir scraper yoktu; yalnızca elle başlatılan 3 teşhis iş akışı (`diagnose-dbtakip*.yml`) vardı, bunlar depodan silindi. Teşhis betikleri (`scripts/diagnose_dbtakip*.py`) arşiv olarak saklandı. Veritabanındaki 6 okulun dbtakip kaynaklı LGS taban puanı (Alman, Notre Dame de Sion, Üsküdar Amerikan, Hisar, İELEV, İzmir Amerikan) `dusuk_dogrulanmamis_ucuncu_taraf` etiketiyle bırakıldı; skora girmiyor, sitede gösterilmiyor. Okullar resmi puan yayımladıkça üzerine yazılacak.

- [x] **TOZOK kopyalarının silinmesi** *(tamamlandı: 06.10.2026)*. 5 okulun (İtalyan, Notre Dame de Sion, Saint Benoit, Saint Michel, Sainte Pulcherie) TOZOK kopyaları, verileri asıl kayıtlara aktarıldıktan sonra silindi.
- [x] **Diğer TOZOK kopyalarını taramak** *(tamamlandı: 06.10.2026)*. 79 TOZOK kaydı ad (il bazında), web alan adı ve telefona göre MEB biçimli kayıtlarla karşılaştırıldı. Yalnızca 2 kopya çıktı: Saint Joseph İstanbul ve Saint Joseph İzmir. Telefon, web ve MSP bilgisi asıl kayıtlara aktarıldı, kopyalar silindi. Kopyalardaki dbtakip LGS puanları (464,42 ve 360) doğrulanmamış olduğu için aktarılmadı. Saint Joseph İstanbul'un ilçesi okulun kendi sitesine göre Şişli'den **Kadıköy**'e düzeltildi. Kalan 77 kaydın MEB tarafında karşılığı yok.
- [x] **Yer tutucu telefon `0 212 212 12 12`** *(tamamlandı: 06.10.2026)*. TOZOK listesinde 4 ilgisiz okulda (Elit Gençler, Galileo Galilei, Sezin, Koç) aynı numara vardı. Okulların kendi sitelerinden doğrulanan numaralarla hem `tozok_msp_ozel_okullar` hem `institutions` tablosunda düzeltildi. İz `data_anomalies` tablosunda.

- [x] **MEB toplu taramasının düzeltilmesi ve 81 il yeniden tarama** *(tamamlandı: 08.10.2026)*. Ölçüm ve nedenler: `docs/EDU-DATA-001-meb-kapsama-olcumu.md`. Resmi ilkokul kapsaması %98,5; ilkokul %91, ortaokul %84, lise %84 (fark büyük ölçüde özel okullar).
- [x] **Veri temizliği B1–B3** *(tamamlandı: 19.10.2026)*. Ankara'ya düşmüş 4.261 koordinat boşaltıldı; başka ildeki okula yazılmış 307 kurum kodu/e-posta temizlendi; "İL - Ad" ve "İL - İLÇE - Ad" biçimli 4.733 lise kopyası birleştirildi (eski kayıt korundu). Yedekler: `_yedek_20261019_*` tabloları.
- [ ] **Koordinat tamamlama (B4)** *(eklendi: 19.10.2026)*: `geocode-institutions.yml` iş akışı hazır; `LOCATIONIQ_API_KEY` secret'ı eklenince günde ~4.800 kurum işleyecek (~58 bin koordinatsız kurum, ~2 hafta). LocationIQ ücretsiz planının atıf ve veri saklama koşulları kayıt sırasında doğrulanmalı.
- [ ] **Özel okullar için kaynak**: MEB okul listesi yalnızca resmi okulları veriyor; ~2.100 özel ilkokul ve karşılığı ortaokul/liseler eksik.
- [ ] **Eşleşmesi belirsiz kalanlar**: 29 belirsiz lise çifti, kurum kodu iki farklı ilde kalan 12 grup, aynı kodu taşıyan 50 grup; %95 altındaki 8 il (Hakkari, Sinop, Trabzon, Artvin, Edirne, Ordu, Bilecik, Gümüşhane) ve 2017 ilçe referansında olmayan yeni ilçeler.

## Arayüz / i18n

- [x] `tercih-sihirbazi.html` ve `explorer.html` sayfalarının tam İngilizce desteği *(tamamlandı: 06.10.2026)*. Aynı işte tercih sihirbazında bir hata da düzeltildi: giriş yapmış kullanıcının "Bana Göre Sırala" tercihleri, ROC geçişinden beri tanımsız bir değişken yüzünden kaydedilemiyordu.

## Hesaplar / Güvenlik (kullanıcı tarafı)

- [x] **Kullanılmayan Google OAuth istemcisini (`eduscor-web`) silmek** *(tamamlandı: 08.10.2026)*. Supabase Google sağlayıcısının kullandığı Client ID (`…ddvoed443…`, "Web client 1") ile karşılaştırılarak diğer istemci (`…2h5cv031…`) silindi. Sitede Google ile giriş test edildi, sorunsuz.
- [x] **Sohbete yapıştırılmış GitHub token'ını GitHub'dan silmek** *(tamamlandı: 08.10.2026)*. Yeni fine-grained token oluşturuldu (yalnızca `eduscore`, Actions read/write), `WORKFLOW_PAT` secret'ı onunla güncellendi, eski token silindi. Bu sırada `SUPABASE_SERVICE_ROLE_KEY` secret'ı yanlışlıkla üzerine yazıldı; Supabase secret key'i yeniden girilerek düzeltildi ve `derive-email` iş akışının elle çalıştırılmasıyla doğrulandı.
- [ ] AdSense incelemesi: Google'ın yanıtı bekleniyor.
- [x] **`scrape_progress` tablosuna sızmış Supabase secret key** *(tamamlandı: 06.10.2026)*. Anahtar döndürüldü, satır silindi, GitHub Actions yeni anahtarla doğrulandı. Kaynak, scraper'daki değişken adı çakışmasıydı ve kodda zaten düzeltilmişti.
- [x] **RLS kapalı 6 tablo** *(tamamlandı: 06.10.2026)*. `_uavt_district_bridge`, `program_enum_lookup`, `scoring_model_versions`, `institution_email_domains`, `meb_il_ilce_kodlari`, `tozok_msp_ozel_okullar`. Hiçbiri sitede kullanılmadığı için RLS politikasız açıldı (migration: `enable_rls_on_internal_reference_tables`). Anon erişimi kapandı, scraper'lar gizli anahtarla etkilenmeden çalışıyor. Metodoloji sayfasında model sürümü gösterilecekse `scoring_model_versions` için ayrıca okuma politikası gerekir.
- [x] **Tetikleyici fonksiyonlarının RPC yetkisi** *(tamamlandı: 06.10.2026)*. 6 tetikleyici fonksiyonunun `EXECUTE` yetkisi PUBLIC/anon/authenticated'dan geri alındı (migration: `revoke_rpc_execute_on_trigger_functions`). Tetikleyiciler çalışmaya devam ediyor; geri alınan bir testle doğrulandı (skor 95→85 hesaplandı, sonra geri alındı). `is_login_locked` giriş sayfası için bilerek açık bırakıldı.
- [ ] **Supabase güvenlik danışmanının kalan uyarıları** *(eklendi: 06.10.2026)*:
  - Sızdırılmış parola koruması (HaveIBeenPwned kontrolü) kapalı. 06.10.2026'da Authentication → Sign In / Providers → Email panelinden açılmaya çalışıldı, kayıt tutmadı (Attack Protection sayfasında hâlâ DISABLED). Proje FREE planda; özellik büyük olasılıkla ücretli plana özel. **Plan yükseltilince açılacak.** O zamana kadar giriş deneme sınırı (`login_attempts`) ve MFA koruma sağlıyor.
  - `vector` ve `pg_trgm` eklentileri `public` şemasında. Taşımak indeksleri ve sorguları etkileyebilir; acil değil.
  - `is_login_locked` ve politikasız RLS tabloları için çıkan uyarılar bilinçli tercih; işlem gerekmez.
