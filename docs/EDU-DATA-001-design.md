# EduScor Data Engine — Design Note

**Document Code:** EDU-DATA-001
**Document Title:** Mevcut Data Pipeline Dokümantasyonu ve Entity Resolution Katmanı Önerisi
**Version:** 2.0 (Uygulandı — 19.09.2026)
**Status:** ✅ Tamamlandı — hem Karar 1 (modül oluşturma) hem Karar 2 (4 script refactor) çözüldü
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
| Mükerrer kurum kaydı | 18 kurum | Aynı okulun farklı kaynaklardan (MEB pilot turu vs. genişleme turu) iki kez yüklenmesi |

**DÜZELTME (19.09.2026):** Bu belgenin ilk taslağı, "hiçbir yükleme script'i entity resolution yapmıyor" varsayımıyla yazılmıştı — bu **yanlış** çıktı. Gerçek kod incelemesi gösterdi ki **4 `load_*.py` script'inin de kendi** `normalize_name()` / `find_existing_match()` / `turkish_lower()` fonksiyonu var, ve `load_to_supabase.py`'de "location_id ile sınırlamıyoruz, global dedup yapıyoruz" şeklinde daha önce yaşanmış bir bug'ın düzeltmesi bile mevcut.

**Gerçek kök neden:** Entity resolution mantığı **yok değil, 4 kez bağımsız olarak kopyalanmış.** `load_to_supabase.py`'de yapılan bir düzeltme (global dedup), diğer 3 script'e (`load_lgs_scores_to_supabase.py`, `load_ookgm_to_supabase.py`, `load_tabanpuan_to_supabase.py`) hiç yayılmamış — her biri kendi (muhtemelen farklı olgunlukta) kopyasını taşıyor. Bu, klasik bir DRY (Don't Repeat Yourself) ihlali: bir yerde bulunan bug, merkezi olmadığı için diğer 3 yerde tekrar tekrar bulunmayı bekliyor.

`eduscor-data-engine` skill'inin *"execute entity resolution"* görevi bu yüzden hâlâ geçerli bir eksiklik — ama "hiç yok" değil, "merkezi değil, tutarsız" olarak yeniden tanımlanmalı.

---

## PART 3 — Uygulanan Çözüm: Merkezi Bir Modül (19.09.2026'da tamamlandı)

### 3.1 eduscor_data_utils.py Oluşturuldu

`scripts/eduscor_data_utils.py` — `normalize_turkish()` ve `find_existing_institution()` fonksiyonlarını içeren, tüm script'lerin ortak olarak kullanacağı tek modül. 4 script'teki dağınık kopyaların **en olgun versiyonu** (load_to_supabase.py'deki "global dedup" düzeltmesi dahil) temel alınarak yazıldı.

### 3.2 Sıradaki Adım: 4 Script'i Refactor Etmek

Her `load_*.py` script'indeki kendi `normalize_name()` / `find_existing_match()` / `turkish_lower()` tanımları silinip, yerine `from eduscor_data_utils import normalize_turkish, find_existing_institution` import'u konulacak. Bu, kod tekrarını ortadan kaldırır — bir düzeltme artık **tek yerde** yapılır, 4 script'e otomatik yayılır.

### 3.3 Neyin Değişmeyeceği

- Her script'in **kendi iş mantığı** (hangi kaynaktan veri çektiği, hangi alanları doldurduğu) aynı kalıyor — sadece normalizasyon/eşleştirme kısmı merkezi hale geliyor
- Diagnose script'leri bu kapsamın dışında

---

## Karar Durumu

1. ✅ **Karar 1 (çözüldü, 18.09.2026):** `eduscor_data_utils.py` oluşturuldu.
2. ✅ **Karar 2 (çözüldü, 19.09.2026):** 4 `load_*.py` script'inin tamamı refactor edildi.

## PART 4 — Refactor Sonuçları (19.09.2026)

Her script farklı bir özel durum içeriyordu, hiçbiri "kopyala-yapıştır" ile değil, tek tek incelenip dikkatle güncellendi:

| Script | Özel durum | Ne yapıldı |
|---|---|---|
| `load_to_supabase.py` | `turkish_title`/`turkish_capitalize_words` başka yerlerde (konum işleme) kullanılıyor | Sadece `normalize_name`/`find_existing_match` merkezi hale getirildi, diğerleri korundu |
| `load_lgs_scores_to_supabase.py` | En basit yapı, `turkish_lower` başka yerde kullanılmıyor | Tüm 3 fonksiyon (`turkish_lower` dahil) merkezi hale getirildi |
| `load_ookgm_to_supabase.py` | `turkish_lower` `map_tur()` içinde de kullanılıyor | Sadece `normalize_name`/`find_existing_match` merkezi hale getirildi |
| `load_tabanpuan_to_supabase.py` | Kendi özgü `normalize_name_lenient` (İ/I ayrımını yok sayan) eşleştirme mantığı var — tabanpuanlari.net kaynağının kendine özgü büyük/küçük harf sorunu için | `normalize_name_lenient`/`find_existing_match`'e **dokunulmadı** (regresyon riski). Sadece kullanılmayan eski `normalize_name` (ölü kod) temizlendi |

Her adımda hem `py_compile` (sözdizimi) hem gerçek `import` + fonksiyon çağrısı testi (bugünkü Bala/Çamlıdere gerçek örnekleriyle) yapıldı — varsayımla değil, doğrulanarak ilerlendi.

**Sonuç:** Entity resolution mantığı artık `eduscor_data_utils.py`'de merkezi — gelecekte bir düzeltme (örn. yeni bir Türkçe karakter sorunu bulunursa) tek yerde yapılıp tüm script'lere otomatik yayılacak. Script'lere özgü davranışlar (lenient eşleştirme gibi) bilinçli olarak korundu, tek tip bir yaklaşıma zorlanmadı.

## Açık Soru

`find_existing_institution()` fonksiyonu, ne kadar "gevşek" eşleştirme yapmalı? Bugünün 18 mükerrer kaydında %100 aynı isim + il eşleşmesi vardı (güvenliydi). Ama gelecekte daha "yaklaşık" eşleşmeler (örn. Levenshtein mesafesi) gerekebilir mi — bu, yanlış pozitif riski taşır (iki farklı okulu aynı sanmak), bu yüzden dikkatli bir eşik gerektirir.
