# EduScor Simulation & Evaluation Log

**Document Code:** EDU-SIM-001
**Document Title:** Trust Model v0.1 — Sensitivity & Independent Validation Experiment Log
**Version:** 1.0
**Status:** Completed (Experiment Round 1)
**Prepared By:** EduScor Product Office (Claude, human-reviewed)
**Related Skill:** eduscor-simulation-evaluation
**Related Model:** trust_model_version = `v0.1_experimental_baseline`

---

## Experiment TE-TRUST-001 — Trust v0.1 Weight Sensitivity & Independent Validation

### Metadata

| Alan | Değer |
|---|---|
| Deney tarihi | 07.09.2026 |
| Dataset | `institution_criteria_scores`, 11.935 kayıt (score IS NOT NULL) |
| Model | `v0.1_experimental_baseline` |
| Deney türü | Salt-okunur analiz — üretim verisine ve modelin kendisine hiçbir değişiklik yapılmamıştır |
| Metodoloji | eduscor-simulation-evaluation kapsamında ağırlık duyarlılığı analizi + bağımsız çapraz doğrulama |

---

### Experiment 1 — Weight Sensitivity Analysis

**Amaç:** Mevcut ağırlık şemasının (source_reliability 0.4 / recency 0.2 / completeness 0.2 / cross_source_consistency 0.2) sonucu ne kadar belirlediğini test etmek.

**Yöntem:** Aynı veri üzerinde, üretim tablosuna hiçbir yazma yapmadan, iki alternatif ağırlık şemasıyla trust_score sorgu anında yeniden hesaplandı:
- Senaryo B (Eşit ağırlık): 0.25 / 0.25 / 0.25 / 0.25
- Senaryo C (Source-reliability baskın): 0.7 / 0.1 / 0.1 / 0.1

**Sonuç:**

| Senaryo | Ortalama | Std. Sapma | v0.1 ile Korelasyon |
|---|---|---|---|
| v0.1 (mevcut) | 0.690 | 0.103 | — |
| Eşit ağırlık | 0.697 | 0.080 | 0.982 |
| Source-reliability baskın | 0.682 | 0.149 | 0.981 |

**Gözlem:** Ağırlık şeması önemli ölçüde değiştirilse dahi (0.4/0.2/0.2/0.2 → 0.7/0.1/0.1/0.1), sonuç sıralaması neredeyse değişmiyor (korelasyon ≥ 0.98). Bu, ağırlık seçiminin görece etkisiz olduğunu düşündürse de, kök nedeni anlamak için Experiment 2 yürütülmüştür.

---

### Experiment 2 — Component Variance / Root Cause Analysis

**Amaç:** Experiment 1'in sonucunu açıklamak — ağırlıklar mı etkisiz, yoksa bileşenlerin kendisi mi ayırt edici bilgi taşımıyor?

**Yöntem:** Her bir bileşenin (source_reliability, recency, completeness, cross_source_consistency) veri kümesi genelindeki standart sapması ve farklı değer sayısı ölçüldü.

**Sonuç:**

| Bileşen | Std. Sapma | Farklı Değer Sayısı |
|---|---|---|
| source_reliability | 0.194 | 5 |
| recency | 0.301 | değişken (NULL dahil) |
| completeness | 0.005 | 2 |
| cross_source_consistency | 0.000 | 1 (sabit) |

**Bulgu (kritik):**

> Nominal olarak 4 boyutlu olan Trust v0.1, mevcut veri yapısında pratik olarak 2 boyutlu davranmaktadır.

`cross_source_consistency` mevcut veri kümesinde sabit bir değerdedir (tüm satırlarda 0.5); bu nedenle ağırlığı ne olursa olsun sonucun değişkenliğine katkı sağlayamaz. `completeness` bileşeninin de mevcut veri dağılımında ayırt edici varyansı yetersizdir (yalnızca iki farklı değer alabilmektedir). Gözlemlenen ayırt edici gücün tamamına yakını `source_reliability` ve `recency` bileşenlerinden gelmektedir.

Bu, Experiment 1'deki yüksek korelasyonun nedenini açıklar: ağırlıklar "iyi kalibre edilmiş" olduğu için değil, iki bileşenin şu an için istatistiksel olarak düz (flat) olması nedeniyle ağırlık değişiklikleri etkisiz kalmaktadır.

---

### Experiment 3 — Independent Validation Attempt

**Amaç:** `is_verified` (insan doğrulaması) alanı ile `trust_score_computed` arasındaki ilişkiyi, modelin formülünden bağımsız bir çapraz kontrol olarak incelemek (`trust_score_computed` hesaplamasında `is_verified` doğrudan kullanılmamaktadır).

**Sonuç:**

| is_verified | Kayıt Sayısı | Ort. trust_score |
|---|---|---|
| false | 11.933 | 0.690 |
| true | 2 | 0.725 |

**Bulgu:** Bağımsız doğrulama için mevcut örneklem büyüklüğü (n=2) yetersizdir; bu nedenle doğrulama performansı hakkında çıkarım yapılmamıştır.

---

## Limitasyonlar

1. Analiz tek bir zaman kesitinde (07.09.2026) yapılmıştır, zamansal tekrar (replikasyon) içermez.
2. `completeness` bileşeni hâlâ metin-tabanlı bir proxy'dir (bkz. Trust v0.1 metodolojisi); bu deney bileşenin kendisini değil, mevcut veri dağılımındaki varyansını ölçmüştür.
3. Experiment 3, örneklem yetersizliği nedeniyle bir doğrulama/red kararı üretmemiştir — bu, modelin başarısız olduğu anlamına gelmez, yalnızca şu an test edilemediği anlamına gelir.

## Kararlar

- Trust v0.1 formülü ve ağırlıkları bu deney sonucunda **değiştirilmemiştir**.
- Bulgular metodoloji dokümanına doğrudan işlenmemiş, bu ayrı deney günlüğünde tutulmuştur (deney sonucu ile model metodolojisinin karışmaması için).
- v0.2 geliştirmesi bu aşamada **başlatılmamıştır**.

## v0.2 İçin Ortaya Çıkan Veri İhtiyaçları (Hipotezler, Henüz Uygulanmadı)

1. **Completeness v0.2:** Metin-tabanlı proxy yerine alan-bazlı model (mevcut alan sayısı / beklenen alan sayısı).
2. **Cross-source Consistency PoC:** Aynı kriter için en az 2 bağımsız kaynağın toplanması — şu anki şema/veri tek kaynaklıdır, bu bileşen ancak çoklu kaynak sonrası anlamlı hale gelebilir.
3. **Human Validation Dataset:** Kontrollü şekilde daha fazla `is_verified` örneği toplanması, bağımsız doğrulamanın istatistiksel olarak mümkün olması için.

**Önerilen döngü:** v0.1 → Evaluation → Bulgular → Veri İhtiyacı → v0.2 Hipotezi → Yeni Veri Toplama → v0.2 → Tekrar Evaluation.
