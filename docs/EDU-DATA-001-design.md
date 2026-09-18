# EduScor Data Engine — Design Note

**Document Code:** EDU-DATA-001
**Document Title:** Mevcut Data Pipeline Dokümantasyonu ve Entity Resolution Katmanı Önerisi
**Version:** 1.0 (Tasarım aşaması — kod yazılmadı)
**Status:** Draft — onay bekliyor
**Related Skill:** eduscor-data-engine
**Related Document:** EDU-GOV-001 (Evidence Ownership & Boundary Principle)

---

## PART 1 — Mevcut Durum: Dağınık Ama Kapsamlı Bir Pipeline

`scripts/` klasöründe **23 Python script'i** var, dört kategoride:

| Kategori | Script'ler | Görev |
|---|---|---|
| **Scrape** | scrape_meb_schools, scrape_lgs_taban_puanlari, scrape_ookgm, scrape_tabanpuanlari, scrape_yks_sinavizcisi | Ham veriyi kaynaktan çeker |
| **Load** | load_to_supabase, load_lgs_scores_to_supabase, load_ookgm_to_supabase, load_tabanpuan_to_supabase | Supabase'e yazar |
| **Derive** | derive_address_from_website, derive_criteria_from_website, derive_email_from_website, extract_criteria_candidates | Web sitesinden ek bilgi çıkarır |
| **Diagnose/Validate** | 8 teşhis script'i + validate_konum_ulasim_baglica | Geliştirme sırasında kaynak yapısını keşfeder |

Her script **bağımsız** çalışıyor — ortak bir kütüphane/modül paylaşmıyorlar.

---

## PART 2 — Bugünün Dersi: Üç Sorunun Ortak Kök Nedeni

Bugün üç ayrı veri kalitesi sorunu bulduk ve düzelttik:

| Sorun | Etkilenen kayıt | Kök neden |
|---|---|---|
| Yanlış konum (location_id) | 303 kurum | İsim ↔ konum eşleştirmesi, Türkçe İ/I/ı normalizasyonu tutarsız |
| Yanlış web sitesi eşleşmesi | 48 kurum | Benzer isimli kurumlar arasında otomatik/manuel eşleştirme hatası |
| Mükerrer kurum kaydı | 18 kurum | Aynı okulun farklı kaynaklardan (MEB pilot turu vs. genişleme turu) iki kez yüklenmesi, format farkı (2 parçalı/3 parçalı isim) nedeniyle eşleşme kontrolü başarısız |

**Ortak payda:** `eduscor-data-engine` skill'inin *"execute entity resolution"* görevi, pratikte **hiçbir yükleme script'inde uygulanmıyor**. Her script kendi normalizasyon mantığını (varsa) ayrı ayrı yazıyor — biri Türkçe büyük İ'yi doğru işliyor, diğeri işlemiyor; biri yeni kayıt eklemeden önce mevcutlarla karşılaştırıyor, diğeri doğrudan ekliyor.

Bu, **tek seferlik bir temizlik sorunu değil** — pipeline bu haliyle çalışmaya devam ettikçe, yeni veri yüklendikçe **aynı hatalar tekrar oluşacak.**

---

## PART 3 — Önerilen Çözüm: Ortak Bir Normalizasyon + Eşleştirme Katmanı

### 3.1 Ortak Bir Yardımcı Modül

`scripts/eduscor_data_utils.py` (yeni, paylaşılan bir dosya) içinde:

- **`normalize_turkish(text)`**: Tüm script'lerin kullanacağı **tek, doğru** Türkçe normalizasyon fonksiyonu (İ→i, I→ı, Ç→c, vb. — bugün SQL'de kullandığımız `translate()` mantığının Python karşılığı)
- **`find_existing_institution(name, location)`**: Yeni bir kayıt eklemeden önce, mevcut veritabanında (normalize edilmiş isim + konum ile) zaten var olup olmadığını kontrol eden fonksiyon — **entity resolution**'ın kendisi

### 3.2 Kural: Her Load Script'i Bu Katmanı Kullanmalı

Yeni bir `load_*.py` script'i yazılırken (ya da mevcutlar güncellenirken), doğrudan `INSERT` yapmadan önce `find_existing_institution()` çağrılmalı. Eşleşme varsa güncelle, yoksa ekle — "önce ara, sonra ekle" prensibi.

### 3.3 Neyin Değişmeyeceği

- Mevcut 23 script'in **hiçbiri** bugün yeniden yazılmıyor — bu, kademeli bir iyileştirme, büyük patlama (big-bang) değişikliği değil
- Diagnose script'leri (geliştirme aracı) bu kapsamın dışında — onlar zaten veri yazmıyor

---

## Açık Kararlar

1. `eduscor_data_utils.py` şimdi mi yazılsın (küçük, tek dosyalık bir modül), yoksa bir sonraki veri yükleme ihtiyacı çıktığında mı (örn. dbtakip scraper'ı geliştirirken) yazılsın?
2. Mevcut 4 `load_*.py` script'i geriye dönük olarak bu modülü kullanacak şekilde güncellensin mi (küçük bir refactor), yoksa sadece **yeni** script'ler için mi zorunlu tutulsun?

## Açık Soru

`find_existing_institution()` fonksiyonu, ne kadar "gevşek" eşleştirme yapmalı? Bugünün 18 mükerrer kaydında %100 aynı isim + il eşleşmesi vardı (güvenliydi). Ama gelecekte daha "yaklaşık" eşleşmeler (örn. Levenshtein mesafesi) gerekebilir mi — bu, yanlış pozitif riski taşır (iki farklı okulu aynı sanmak), bu yüzden dikkatli bir eşik gerektirir.
