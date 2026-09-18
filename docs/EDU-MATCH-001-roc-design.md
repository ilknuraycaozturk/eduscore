# EduScor Match Engine — Design Note

**Document Code:** EDU-MATCH-001
**Document Title:** Match Engine v2 — Rank Order Centroid (ROC) Tabanlı Ağırlıklandırma
**Version:** 1.0 (Tasarım aşaması — kod yazılmadı)
**Status:** Draft — onay bekliyor
**Related Skill:** eduscor-match-decision
**Related Document:** EDU-GOV-001 (Evidence Ownership & Boundary Principle)

---

## PART 1 — Mevcut Sistem (v1) Dokümantasyonu

`tercih-sihirbazi.html` sayfasında zaten çalışan bir sistem var:

### 1.1 İki Aşamalı Yapı

1. **Objektif filtre:** Kullanıcının LGS puanı, `institution_criteria_scores`'daki ham `akademik_basari` puanıyla karşılaştırılır — sadece girebileceği okullar listelenir. `success_score`'a hiç dokunulmaz.
2. **Subjektif sıralama:** Kullanıcı, diğer kriterlere 0-4 arası önem verir (slider). Ağırlıklı ortalama (`weightedSum / weightTotal`) ile `matchScore` hesaplanır.

### 1.2 Güçlü Yön
Kurumsal skor ile kişisel uygunluk zaten ayrı — EDU-GOV-001 prensibiyle uyumlu.

### 1.3 Sınır
Ağırlıklar, kullanıcının 0-4 slider'la **serbestçe** verdiği sayılardır — birbirine göre **tutarlı** olmaları garanti değil (örn. bir kullanıcı 5 kriterin hepsine "4=Çok Önemli" verebilir, bu durumda hiçbiri diğerinden ayrışmaz).

---

## PART 2 — v2 Tasarımı: ROC Tabanlı Ağırlıklandırma

### 2.1 Temel Fikir

Kullanıcı kriterlere **sayı vermez**, önemine göre **sıralar** (mevcut sürükle-bırak sıralama arayüzü kullanılabilir). Sıralamadan matematiksel olarak ağırlık türetilir — Rank Order Centroid formülü:

```
n = sıralanan kriter sayısı
i. sıradaki kriterin ağırlığı: w_i = (1/n) × Σ(j=i to n) (1/j)
```

**Örnek (4 kriter sıralanmış):**

| Sıra | Kriter | Ağırlık |
|---|---|---|
| 1 | Fiziksel Altyapı | 0.521 (%52.1) |
| 2 | Öğretmen Kalitesi | 0.271 (%27.1) |
| 3 | Sosyal-Kültürel | 0.146 (%14.6) |
| 4 | Konum/Ulaşım | 0.063 (%6.3) |

Toplam = 1.0 (matematiksel olarak garanti).

### 2.2 Neden Bu Yöntem Uygun

- **Literatürde bilinen bir yöntem** (SMART/SWING ağırlıklandırma ailesinden, MCDM'de yaygın) — uydurma bir formül değil
- **Tutarsızlık imkânsız** — sıralama zaten tek bir toplam sıra ürettiği için AHP'deki gibi bir "tutarlılık oranı" kontrolüne gerek yok
- **UX yükü düşük** — 9 kriter için 36 ikili karşılaştırma yerine, tek bir sıralama işlemi
- **"Önemsiz" kriterler:** Kullanıcı sadece önemsediği kriterleri sıralamaya dahil eder, sıralamaya girmeyenler otomatik olarak dışlanır (mevcut "ağırlık=0" davranışıyla eşdeğer)

### 2.3 Neyin Değişmeyeceği

- **Aşama 1 (objektif LGS filtresi) hiç değişmiyor** — sadece Aşama 2'nin (ağırlıklandırma) matematiği değişiyor
- Kurumda o kriter yoksa atlanır kuralı **korunuyor**
- `success_score`'a **hiç dokunulmuyor** (EDU-GOV-001 ile tutarlı)

---

## Karar Listesi (18.09.2026 tarihinde netleştirildi)

1. **UI:** ✅ Tam sıralama moduna geçilecek, 0-4 slider'lar **tamamen kaldırılacak** — akademik kanıt (slider'ların "anchoring bias" ve "hepsine yüksek puan verme" sorunu) ve endüstri standardı (SurveyMonkey/Qualtrics'in ranking soru tipi) bu yönde.
2. **Katılım:** ✅ Kullanıcı sadece önemsediği kriterleri sıraya sokar — bu, 9 kriteri doğal olarak "3-8 öğe" UX sınırına indirir (sıralamaya hiç girmeyenler otomatik dışlanır, mevcut "ağırlık=0" davranışıyla eşdeğer).
3. **Geçiş:** ✅ v1 (slider) tamamen kaldırılıyor, iki sistem bir arada tutulmayacak.

### Kullanıcı Dostu Olma Şartı (Kullanıcı tarafından vurgulandı)

Bu, tasarımın merkezi ilkesi. Somut karşılıkları:

- **Sürükle-bırak, dokunmatik uyumlu** — masaüstünde mouse, mobilde parmakla sürükleme aynı derecede rahat çalışmalı
- **Az adım:** Kullanıcı sadece önemsediği kriterleri, tek bir listede yukarı/aşağı taşır — ayrı ayrı ikili karşılaştırma ekranları YOK (bu, tam AHP'nin reddedilme sebebiydi)
- **Görsel geri bildirim:** Her kriterin yanında sıra numarası (1, 2, 3...) net görünür; en üstteki "en önemli" olarak vurgulanır
- **Ağırlıkların kendisi gösterilmez** — kullanıcı "%52.1 ağırlık" gibi bir sayı görmez, sadece sıralamasını görür (ROC hesaplaması arka planda kalır — Trust Score'daki "sayısal skor kullanıcıya gösterilmesin" ilkesiyle tutarlı bir sadelik)
- **Geri dönülebilir:** Kullanıcı istediği an sırayı değiştirebilir, sonuçlar anlık güncellenir

---

*Bu bölüm, tasarım aşamasının onaylandığını gösterir. Sıradaki adım: kod uygulaması.*
