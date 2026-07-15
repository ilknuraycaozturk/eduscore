# EduScor Operasyonel Veri ve Büyüme Aksiyon Planı (Action Plan)

**Doküman Kodu:** EDU-OPS-001
**Sürüm:** 1.0
**Hazırlayan:** EduScor Ürün Ofisi
**Tarih:** 15 Temmuz 2026

---

## 1. Genel Strateji Özeti

EduScor, veri toplama ve güncelleme maliyetlerini en aza indirmek için **"Topluluk Katılımlı Veri Modeli" (Crowdsourcing)** ve **"Almak için Ver" (Give-to-Get)** modelini kullanır. Süreç, küresel örneklerden (Niche, Glassdoor, Waze) esinlenen 4 ana fazda yürütülecektir.

---

## 2. Faz Bazlı Aksiyon Adımları

### FAZ 1: Altyapı ve Akıllı Tohumlama (Ay 1)
*Hedef: Sistemi sıfır manuel veri girişiyle, Bağlıca bölgesindeki tüm okul iskeletleriyle doldurmak.*

- **Aksiyon 1.1 — Resmi Veri Çekimi (Seeding):** MEB kamuya açık veri kaynaklarından Bağlıca bölgesindeki tüm okulların resmi adı, adresi, harita koordinatları ve türü (kolej, anaokulu, dil okulu) çekilerek veri tabanına aktarılır. *Sorumlu: Yazılım Geliştirici.*
- **Aksiyon 1.2 — AI Web-Scraping Botlarının Kurulması:** Bağlıca'daki okulların kurumsal web sitelerini tarayan basit botlar yazılır; toplanan düz metinler LLM entegrasyonu ile yapılandırılmış verilere (sınıf mevcutları, kulüp imkanları vb.) dönüştürülüp taslak olarak kaydedilir. *Sorumlu: Yazılım Geliştirici.*
- **Aksiyon 1.3 — "Taslak Veri" Şeffaflık Uyarısı:** Doğrulanmamış okul profillerine *"Bu sayfadaki bilgiler okulun kurumsal web sitesinden yapay zeka ile otomatik derlenmiştir. Doğruluğunu kontrol ediniz."* uyarısı eklenir. *Sorumlu: Ürün Tasarımcısı (UI/UX Designer).*

### FAZ 2: Mikro-Lokal Lansman ve Okul Katılımı (Ay 2)
*Hedef: Veri giriş yükünü okul yöneticilerine devretmek ve ilk doğrulanmış verileri toplamak.*

- **Aksiyon 2.1 — "Profilini Sahiplen" (Claim Profile) Modülü:** Okul yöneticilerinin resmi e-posta veya evrakla kimlik doğrulayıp sayfadaki bilgileri güncelleyebileceği arayüz. *Sorumlu: Yazılım Geliştirici / Ürün Sahibi.*
- **Aksiyon 2.2 — Bağlıca Okul Yönetici İletişim Kampanyası:** Okullara, velilerin EduScor üzerinden karşılaştırma yaptığı ve sayfalarını güncel tutmalarının (ücretsiz "Doğrulanmış Okul" rozeti) veli gözünde güveni artıracağı bildirilir. *Sorumlu: Pazarlama / Kurucu Ortaklar.*
- **Aksiyon 2.3 — "Toplam Maliyet Hesaplayıcı" Tasarımı:** Velilerin okul fiyatlarını (yemek, servis, kitap dahil) anonim olarak ekleyebileceği alan. *Sorumlu: Ürün Tasarımcısı.*

### FAZ 3: Velilerle "Give-to-Get" ve "Waze" Çarkı (Ay 3)
*Hedef: En zor ulaşılan gizli maliyet ve yorum verilerini veliler aracılığıyla organik olarak toplamak.*

- **Aksiyon 3.1 — "Almak için Ver" Kilidinin Devreye Alınması:** Detaylı maliyet karşılaştırmaları/analiz raporlarını görebilmek için, kendi çocuğunun okuduğu/okuduğu okul hakkında 3 soruluk mini anket zorunlu tutulur. *Sorumlu: Ürün Sahibi.*
- **Aksiyon 3.2 — "Waze" Tarzı Topluluk Doğrulama Sistemi:** Bir veli fiyat girdiğinde, diğer velilere *"Bu fiyat bilgisi hala güncel mi?"* Evet/Hayır sorusu çıkar, veri topluluğa teyit ettirilir. *Sorumlu: Yazılım Geliştirici / Ürün Tasarımcısı.*
- **Aksiyon 3.3 — Doğrulanmış Veli İnceleme Filtresi:** Yorum güvenilirliği için velilerden (bilgileri maskelenmiş) öğrenci belgesi/okul faturası istenir; bu yorumlar "Doğrulanmış Veli" etiketiyle gösterilir. *Sorumlu: Yazılım Geliştirici.*

### FAZ 4: Güvenli Gelir Modelleri (Ay 4+)
*Hedef: Tarafsızlık ve güven ilkelerini bozmadan gelir üretmeye başlamak.*

- **Aksiyon 4.1 — "Zenginleştirilmiş Profil" Satış Paketi:** Okullara 3D sanal tur, tanıtım videosu, randevu modülü ekleme imkanı sunan abonelik; EduScor skorunu **kesinlikle etkilemez**. *Sorumlu: Kurucu Ortaklar / Satış Temsilcisi.*
- **Aksiyon 4.2 — Nitelikli Veli Yönlendirme (Lead Generation) Altyapısı:** Bütçe/felsefe kriterleriyle %100 eşleşen velilerin rızasıyla okulların tanıtım günlerine başvuru toplanır; okullardan başvuru başına (CPL) ücret alınır. *Sorumlu: Ürün Sahibi / Yazılım Geliştirici.*

---

## 3. Temel Performans Göstergeleri (KPIs)

- **Operasyonel Verimlilik:** Manuel / Otomatik veri girişi oranı (Hedef: <%5 Manuel)
- **Okul Sahiplenme Oranı (Claim Rate):** Bağlıca okullarının profil güncelleme oranı (Hedef: 3 ayda %40)
- **Veli Katılım Oranı (Engagement Rate):** "Give-to-Get" anketi tamamlama oranı (Hedef: %25)
- **Veri Güncellik Puanı:** Topluluk teyitli fiyat verisi oranı (Hedef: %80)

---

## 4. Kritik Riskler ve Önlemler (Mitigation)

| Risk Tanımı | Etki Derecesi | Alınacak Önlem |
| :--- | :--- | :--- |
| Okulların sahte profillerle sistemi manipüle etmesi | Yüksek | Profil sahiplenmede resmi MEB kurumsal e-posta veya vergi levhası kontrolü zorunluluğu |
| Velilerin yanlış/yanıltıcı maliyet verisi girmesi | Orta | "Waze" modeliyle veri, birden fazla veli onaylamadan "kesinleşmiş" gösterilmez |
| Okulların olumsuz yorumları sildirmek için para teklif etmesi | Yüksek | EduScor Etik Beyanı'nın (Trust Statement) anasayfada açıkça yayınlanması, asla taviz verilmemesi |
