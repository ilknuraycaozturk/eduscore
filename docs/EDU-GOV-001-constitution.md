# EduScor-AI Constitution

**Document Code:** EDU-GOV-001
**Document Title:** Evidence Ownership & Boundary Principle
**Version:** 1.0
**Status:** Adopted
**Scope:** Bu doküman, tüm EduScor-AI skill'lerinin (Education Framework, Data Engine, Trust & Uncertainty, Scoring Model, Match & Decision, EduNode, AI Governance, Simulation/Evaluation, Grant/PM/Compliance, Commercial Growth) uyduğu ortak, üst düzey bir mimari prensibi tanımlar.

---

## Temel Prensip

> **Evidence is produced locally, consumed downstream, and never altered outside its owning layer.**
>
> Kanıt kendi sorumluluk alanında üretilir, aşağı akıştaki katmanlar tarafından kullanılır; ancak başka bir katman tarafından değiştirilmez.

Her skill bir **kanıt (evidence)** üretir. Bir sonraki skill bu kanıtı **girdi olarak kullanır**, ama kendi sorumluluk alanı dışındaki çıktıyı **doğrudan değiştirmez**.

---

## Evidence-Driven Architecture — Katman Tablosu

| Katman / Skill | Ürettiği Temel Çıktı | Yetki Sınırı |
|---|---|---|
| Education Framework | Kanıt: tanımlar, kriterler, göstergeler | Eğitimsel çerçeveyi tanımlar; skor üretmez |
| Data Engine | Kanıt: normalize edilmiş veri + provenance | Veriyi toplar/normalize eder; güven veya skor belirlemez |
| Trust & Uncertainty | Kanıt: güvenilirlik, belirsizlik ve veri kalitesi metrikleri | Verinin güven düzeyini değerlendirir; EduScor'u değiştirmez |
| Scoring Model | Kanıt: boyut skorları, kompozit skorlar + varsayımlar | Kurumsal skoru üretir; kişisel öneri yapmaz |
| Match & Decision | Kanıtı kullanır: skorlar + kullanıcı tercihleri | Uygunluk/recommendation üretir; kurumsal skoru değiştirmez |
| EduNode | Kanıt: gözlemlenen/kanıtlanabilir ilişkiler | İlişki bilgisi üretir; nedensellik iddia etmez |
| AI Governance | Kanıt: bias, Goodhart, fairness, audit ve explainability bulguları | Denetler; modelin sahibi değildir |
| Simulation / Evaluation | Kanıt: test, sensitivity, robustness, validation sonuçları | Model hakkında kanıt üretir; modeli doğrudan değiştirmez |
| Grant / PM / Compliance | Kanıtın fonlanabilir yapıya dönüştürülmesi | Bilimsel/teknik kanıtı WP, KPI, TRL, deliverable vb. yapıya çevirir |
| Commercial Growth | Kanıta dayalı ticari strateji ve büyüme hipotezleri | Pazarlama/growth stratejisi üretir; skoru asla değiştirmez |

---

## Evidence Chain (Kanıt Zinciri)

```
EDUCATION FRAMEWORK
       │
       ▼
   DEFINITIONS
       │
       ▼
   DATA ENGINE
       │
       ▼
 NORMALIZED DATA
       │
       ▼
TRUST & UNCERTAINTY
       │
       ▼
 TRUST EVIDENCE
       │
       ▼
 SCORING MODEL
       │
       ▼
 SCORE + ASSUMPTIONS
       │
       ├──────────────► MATCH & DECISION
       │
       ├──────────────► GOVERNANCE
       │
       └──────────────► SIMULATION / EVALUATION
                              │
                              ▼
                         TEST EVIDENCE
                              │
                    ┌─────────┴─────────┐
                    ▼                   ▼
                 GRANT              GROWTH
```

**Kritik nokta:** Bu oklar "değiştirir" anlamına gelmez, "beslenir/kullanır" anlamına gelir. Özellikle Simulation/Evaluation'ın Scoring Model'e okla bağlanması, Evaluation'ın modeli **değiştirdiği** anlamına gelmez — sadece **bilgilendirdiği** anlamına gelir:

- **Evaluation der ki:** "Model şu koşullarda şu davranışı gösteriyor."
- **Scoring Model der ki:** "Bu bulgu ışığında yeni bir model sürümü geliştirebiliriz."
- Bu geçiş **otomatik değildir** — Evaluation, Scoring Model'i kendiliğinden güncellemez; bir insan/başka bir süreç bu kanıtı değerlendirip karar verir.

---

## Somut Örnekler

### Örnek 1 — Commercial Growth ↔ Scoring

❌ **Yasak:**
> "Bu okulun puanı düşük, okul ücretli üyelik satın alırsa puanını yükseltelim."

✅ **İzin verilen:**
> "Okullar için veri profili, analitik dashboard, benchmark ve görünürlük hizmeti sunabiliriz."

**Neden:** Ticari model kanıtı (skoru) değiştirmiyor; kanıtın etrafında bir ürün/hizmet oluşturuyor.

### Örnek 2 — Match & Decision ↔ Scoring

❌ **Yasak:**
> "Bu öğrencinin tercihleri nedeniyle okulun kurumsal skorunu düşürelim."

✅ **Doğru model:**
> Institutional Score + User Preferences → Suitability / Match Score

**Neden:** EduScor (kurumsal skor) başka, kullanıcıya uygunluk (match score) başkadır. Biri diğerini değiştirmez, ikisi birlikte üçüncü, ayrı bir çıktı üretir.

---

## Bu Prensibin Pratikte Uygulanmış Örneği (EduScor Trust v0.1)

2026-09-07 tarihli Trust Model v0.1 deneyinde (bkz. `EDU-SIM-001`) bu prensip fiilen uygulandı:

1. Trust & Uncertainty katmanı, `institution_criteria_scores` tablosuna **kanıt üretti** (`trust_score_computed`, `source_reliability`, vb.)
2. Bu kanıt, mevcut `score` sütununa **hiçbir şekilde bağlanmadı** — Scoring Model'in çıktısı değiştirilmedi
3. Simulation/Evaluation katmanı bu kanıtı test etti (duyarlılık analizi, bağımsız doğrulama) ve **kendi kanıtını** (deney bulguları) üretti
4. Bu bulgular Trust modelinin **kendisini otomatik olarak değiştirmedi** — sadece v0.2 için hipotezler önerdi, karar insan tarafından (kullanıcı onayıyla) verilecek

Bu, "Evidence is produced locally, consumed downstream, and never altered outside its owning layer" prensibinin gerçek bir vaka çalışmasıdır.

---

## İlgili Dokümanlar

- `EDU-SIM-001` — Trust Model v0.1 Evaluation Log (bu prensibin ilk uygulanma örneği)
- 10 EduScor-AI skill dosyasının her biri, "Respect module boundaries" ilkesinin altında bu prensibin kendi bağlamına uyarlanmış bir cümlesini içerir (2026-09-07 güncellemesi).
