# EduScor Scoring Model — Design Note

**Document Code:** EDU-SCORE-002
**Document Title:** Scoring Model v2 — Design Note (Weight Renormalization & Evidence Coverage)
**Version:** 1.0 (Design phase — no code implemented)
**Status:** Draft — awaiting decisions
**Related Skill:** eduscor-scoring-model
**Related Document:** EDU-GOV-001 (Evidence Ownership & Boundary Principle)

---

## PART 1 — v1 Mevcut Durum Dokümantasyonu

### 1.1 Kriterler ve Ağırlıklar (tam liste)

| Kriter | Ağırlık | Sırası | v1'de fiilen kullanılıyor mu? |
|---|---|---|---|
| LGS Akademik Başarısı | 28 | 1 | ✅ |
| Yabancı Dil Eğitimi | 15 | 2 | ✅ |
| Üniversite Yerleştirme | 14 | 3 | ✅ |
| Fiziksel Altyapı | 10 | 4 | 🟡 Nadiren (çok az kurumda "Profilini Sahiplen" verisi var) |
| Sosyal, Kültürel Etkinlikler | 9 | 5 | ❌ Veri yok |
| Öğretmen Kalitesi | 8 | 6 | ❌ Veri yok |
| Güvenlik, Disiplin | 7 | 7 | 🟡 Nadiren |
| Konum, Ulaşım | 5 | 8 | ❌ Veri yok |
| Burs, Ücret | 4 | 9 | 🟡 Nadiren |
| **Toplam** | **100** | | |

### 1.2 Formül (gerçek veriyle doğrulandı)

Önceki bir oturumun `methodology_note` alanında *"kalanlar arasında yeniden normalize edilmedi"* ifadesi vardı. Bu iddia **gerçek veriyle test edilip yanlış bulundu:**

**TED Ankara Koleji Vakfı Özel Lisesi** (4 kriter dolu):
```
(15×50 + 10×100 + 7×100 + 4×90) / (15+10+7+4) = 2810 / 36 = 78.1
```
`success_score = 78.1` ile **birebir eşleşiyor.** Yani formül `Σ(ağırlık × skor) / Σ(kullanılan ağırlıklar)` — **kullanılan kriterlerin ağırlığı üzerinden gerçekten yeniden normalize ediliyor**, toplam 100 üzerinden değil.

Tek kriterli kurumlarda (`success_score_criteria_count=1`) bu ayrım görünmüyor çünkü matematiksel olarak `w×s/w = s` (ağırlık ne olursa olsun sonuç değişmiyor) — bu, önceki `methodology_note` yazımının yanlış yorumlanmasına yol açmış olabilir.

**Düzeltme notu:** Bu Design Note'un ilk taslağında ben de aynı yanlış varsayımla başlamıştım; gerçek veriyle test ederek düzelttim. Trust v0.1 sürecindeki "önce gerçek veriyi doğrula" pratiğinin bir örneği.

### 1.3 Gerçek Problem: Normalize Etmenin Kendisi

Normalize etme matematiksel olarak doğru çalışıyor, ama **yan etkisi** şudur:

| Kurum | Kullanılan Kriter | success_score |
|---|---|---|
| Antalya Demre MTAL | Sadece `yabanci_dil` (50) | **40.0** |
| TED Ankara Koleji | 4 kriter (yabanci_dil, fiziksel_altyapi, guvenlik, burs) | **78.1** |

Aynı 0-100 ölçeğinde sunulan bu iki skor, **kanıt miktarı bakımından tamamen farklı** güvenilirliktedir — ama kullanıcı arayüzünde bu fark hiçbir şekilde görünmüyor. Az kanıtla elde edilen yüksek bir skor (örn. tek kriterde 100 alan bir kurum), çok kanıtla elde edilen orta bir skorla (örn. 4 kriterde 78) **görsel olarak ayırt edilemez.**

### 1.4 Veri Kapsamı ve Güncellik

- Toplam kurum: 14.964 — `success_score` dolu: 7.994 (%53.4)
- `success_score_computed_at`: **tüm kayıtlarda aynı zaman damgası** (23 Ağustos 2026) — tek seferlik bir hesaplama, otomatik/canlı değil
- Bu tarih, MEB scraper'ın son genişlemesinden (kurum kodu doluluk %1.4→%30.4) **öncesine** denk geliyor — mevcut skorlar güncel veriyle **senkronize değil**
- Hesaplama mantığı DB'de bir trigger/fonksiyon olarak değil, artık repoda bulunmayan bir script'in tek seferlik çıktısı olarak mevcut

---

## PART 2 — v2 Tasarım Önerileri

### Öneri 1 — Yeniden Normalizasyon

**Durum:** v1 zaten yeniden normalize ediyor (bkz. 1.2). v2 için önerilen değişiklik yok, **mevcut davranış korunacak** — ama artık açıkça ve doğru şekilde dokümante edilmiş olacak (v1'in kendi `methodology_note`'u yanlıştı, v2 bunu düzeltecek).

**Gerekçe:** Zaten doğru çalışan bir mekanizmayı "düzeltmek" gereksiz risk taşır. Asıl eksik, normalizasyonun *yanında* kanıt miktarını göstermemesi (bkz. Öneri 2).

---

### Öneri 2 — Score ile Evidence Coverage Ayrımı

**Tasarım:** İki ayrı, birbirine karıştırılmayan alan:

- **`success_score`** (mevcut): Kullanılan kriterlerin ağırlıklı ortalaması — "eldeki kanıta göre ne kadar iyi"
- **`evidence_coverage`** (yeni): Kullanılan kriterlerin ağırlık toplamının, tüm 9 kriterin ağırlık toplamına (100) oranı — "bu skor, olası kanıtın ne kadarına dayanıyor"

Örnek: TED Ankara Koleji için `evidence_coverage = 36/100 = %36`. Antalya Demre MTAL için `evidence_coverage = 15/100 = %15`.

**Gerekçe:** `eduscor-scoring-model` ilkesi — *"Distinguish raw values, normalized values, dimension scores, uncertainty adjustments, and composite scores."* Score ve coverage'ı ayrı tutmak, ileride kullanıcı arayüzünde "78 puan (kanıtın %36'sı)" gibi dürüst bir gösterim imkânı yaratır — şu an bu ayrım hiç yok.

**Metodolojik etki:** Bu, EDU-GOV-001'deki Evidence Ownership ilkesiyle doğrudan uyumlu — Scoring Model, kendi kanıt kalitesini de bir çıktı olarak üretir, gizlemez.

---

### Öneri 3 — Yeni Alanların Gerekliliği

| Alan | Önerilen mi? | Gerekçe |
|---|---|---|
| `criteria_available` | ✅ Önerilir | Kurum türüne göre teorik olarak kaç kriter uygulanabilir (örn. anaokulu için `universite_yerlestirme` hiç uygulanamaz — Trust v0.1'deki "lise-özel kriter" ayrımıyla tutarlı) |
| `criteria_used` | ✅ Zaten var (`success_score_criteria_count` olarak) | İsim netliği için `criteria_used` olarak yeniden adlandırılabilir, ama zorunlu değil |
| `evidence_coverage` | ✅ Önerilir (Öneri 2) | Yukarıda detaylandırıldı |

**Not:** `criteria_available` hesaplaması, hangi kriterin hangi kurum türüne uygulanabilir olduğuna dair bir kural seti gerektirir — bu, Trust v0.1'de zaten karşılaştığımız "lise-özel kriter" sorununun scoring tarafındaki karşılığıdır. Bu kural seti **henüz tanımlanmamıştır**, ayrı bir alt-karar gerektirir.

---

### Öneri 4 — Minimum Kanıt Eşiği (Varsayım, Karar Verilmedi)

**Olası tasarım (sadece öneri, henüz karar değil):** `evidence_coverage` belirli bir eşiğin (örn. %20) altındaysa, `success_score` yine hesaplanır ama arayüzde "Ön Değerlendirme" gibi bir etiketle sunulabilir; eşik üstündekiler "Değerlendirildi" etiketiyle.

**Bu tamamen bir varsayımdır — eşik değeri (%20, %30, vb.) hiçbir veriye dayanmamaktadır, keyfi bir başlangıç noktasıdır.** Karar için Simulation/Evaluation ile test edilmesi gerekir (örn. farklı eşiklerin kaç kurumu hangi kategoriye soktuğu analiz edilmeden karar verilmemeli — tıpkı Trust v0.1'deki ağırlık duyarlılığı deneyi gibi).

---

### Öneri 5 — Versiyon Ayrımı

v1 (`v1_partial_3of9`, `1aef7c78-...`) **değiştirilmeyecek/silinmeyecek.** v2, `scoring_model_versions` tablosuna yeni bir kayıt olarak eklenecek (örn. `v2_evidence_coverage`), `is_experimental=true` ile işaretlenecek. `institutions.success_score_model_version_id` yalnızca v2 hesaplaması tamamlandığında ve onaylandığında güncellenecek.

---

### Öneri 6 — Güncel Veriyle Yeniden Hesaplama (Tasarım)

**Kapsam:** Mevcut 14.964 kurumun tamamı, güncel `institution_criteria_scores` verisiyle (MEB scraper genişlemesi dahil) yeniden hesaplanacak.

**Yöntem taslağı:**
1. Her kurum için mevcut (score IS NOT NULL) kriterleri ve ağırlıklarını al
2. Öneri 1'deki (değişmeyen) ağırlıklı ortalama formülünü uygula
3. Öneri 2'deki `evidence_coverage`'ı hesapla
4. Sonuçları v2 model versiyonu altında **ayrı bir sütun setine** yaz (v1 sütunlarının üzerine değil — bkz. Öneri 5)

**Not:** Bu, henüz uygulanmamış bir tasarımdır; kod yazılmadı.

---

### Öneri 7 — Trust Score Entegrasyonu

**Yok.** Trust Score v0.1 tamamen bağımsız kalmaya devam ediyor. `trust_score_computed`, v2'nin hiçbir hesaplamasına girdi olarak kullanılmayacak. Bu, sizin önceki kararınızla ("Trust'a artık dokunmayalım") ve EDU-GOV-001'deki *"Trust & Uncertainty verinin güven düzeyini değerlendirir; EduScor'u değiştirmez"* ilkesiyle tam uyumludur.

---

## Karar Listesi (07.09.2026 tarihinde netleştirildi)

1. **Evidence Coverage alanı (Öneri 2):** ✅ **Kabul edildi.** Düşük risk, yüksek değer — mevcut hiçbir hesaplamayı bozmuyor.
2. **`criteria_available` kural seti (Öneri 3):** ✅ **Ayrı bir alt-görev olarak ele alınacak.** Şimdilik `evidence_coverage`, kurum türüne göre payda inceliği olmadan, basitçe toplam 100 ağırlık üzerinden hesaplanacak. "Hangi kriter hangi kurum türüne uygulanır" sorusu (Trust v0.1'deki lise-özel kriter ayrımına benzer) ayrıca ele alınacak.
3. **Minimum kanıt eşiği (Öneri 4):** ⏸️ **Ertelendi.** Simulation/Evaluation'ın bekleyen deneyler listesine eklendi — önce `evidence_coverage`'ın gerçek dağılımı (kaç kurum hangi aralıkta) gözlemlenecek, eşik tartışması o zaman somutlaşacak.
4. **Yeniden hesaplama zamanlaması (Öneri 6):** 🔓 **Hâlâ açık.** İki seçenek makul kabul edildi (tasarım onayından hemen sonra / MEB otomatik turunun 81 ili tamamlamasından sonra) — kesin zamanlama kararı henüz verilmedi.

## Açık Sorulara Cevaplar (07.09.2026)

1. **`evidence_coverage` UI'a yansısın mı?** ➡️ **Hayır, şimdilik.** Trust Score ile aynı mantık: önce backend'de var olsun, Simulation/Evaluation ile faydası test edilsin, sonra UI kararı ayrıca verilsin.
2. **Eşik altı kurumlar için score hesaplansın mı?** ➡️ **Evet, hesaplansın ama etiketlensin.** "Veri olmayan kriter asla 0 sayılmaz" ilkesiyle tutarlı — az kanıt, "veri yok" demek değildir.

---

*Bu bölüm, tasarım aşamasının onaylandığını gösterir. Kod henüz yazılmamıştır — uygulama, Karar 4'teki zamanlama netleştiğinde ayrı bir onayla başlayacaktır.*
