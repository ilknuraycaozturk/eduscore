/**
 * EduScor i18n — paylaşılan çeviri sözlüğü ve dil değiştirme mantığı.
 * Her sayfaya <script src="i18n.js"></script> ile eklenir.
 *
 * KULLANIM:
 *   HTML'de çevrilecek her eleman: <span data-i18n="hero_title">...</span>
 *   Placeholder'lar için: <input data-i18n-placeholder="search_placeholder">
 *   Sayfa yüklenince ve dil değiştirilince applyI18n() otomatik çağrılır.
 *
 * KAPSAM: Sadece STATİK arayüz metinleri (başlık/buton/menü). Veritabanından
 * gelen kurum isimleri/açıklamaları bu sistemin kapsamı DIŞINDA (institution_translations
 * ayrı, henüz doldurulmamış bir tablo - kullanıcı bilinçli olarak bu kapsamı istemedi).
 */

const I18N_DICT = {
    // --- Navigasyon (tüm sayfalarda ortak) ---
    nav_home: { tr: "Ana Sayfa", en: "Home" },
    nav_how: { tr: "Nasıl Çalışır?", en: "How It Works" },
    nav_explorer: { tr: "Platformu Keşfet", en: "Explore Platform" },
    nav_methodology: { tr: "Metodoloji", en: "Methodology" },
    nav_edunode: { tr: "EduNode", en: "EduNode" },
    nav_for_institutions: { tr: "Okulunuzu Sahiplenin", en: "Claim Your School" },
    nav_favorites: { tr: "Favorilerim", en: "My Favorites" },
    nav_login: { tr: "Giriş Yap", en: "Log In" },
    nav_logout: { tr: "Çıkış Yap", en: "Log Out" },
    nav_stats: { tr: "İstatistikler", en: "Statistics" },

    // --- Ana Sayfa Hero ---
    hero_badge: { tr: "Eğitim Karar Destek Platformu", en: "Education Decision Support Platform" },
    hero_title_part1: { tr: "En Doğru Eğitim Kararını", en: "Make the Right Education Decision" },
    hero_title_span: { tr: "Veriyle", en: "With Data" },
    hero_title_part2: { tr: "Alın", en: "" },
    hero_subtitle: {
        tr: "Kulaktan dolma bilgilerle değil, şeffaf kriterler ve bağımsız veri modelleriyle — sadece puan değil, size en uygun seçeneği bulmanıza yardımcı oluyoruz.",
        en: "Not hearsay — with transparent criteria and independent data models, we help you find not just a score, but the right fit for you.",
    },

    // --- Arama Formu ---
    search_location_placeholder: { tr: "İl, ilçe veya mahalle...", en: "Province, district or neighborhood..." },
    search_query_placeholder: { tr: "Kurum adı veya anahtar kelime...", en: "School name or keyword..." },
    search_submit: { tr: "Sorgula", en: "Search" },
    search_near_me: { tr: "Yakınımda Ara", en: "Search Near Me" },
    search_near_me_selected: { tr: "📍 Yakınımda Ara (seçili)", en: "📍 Search Near Me (selected)" },
    search_step_segment: { tr: "Kurum / Segment Tipi", en: "Institution / Segment Type" },
    search_step_location: { tr: "Bölge / Konum", en: "Region / Location" },
    search_step_query: { tr: "Tercih Detayı", en: "Preference Detail" },
    search_segment_placeholder: { tr: "Segment Seçin", en: "Select a Segment" },
    search_segment_notice: {
        tr: '🔜 Bu segment için veri aktarımı henüz devam ediyor — şu an en kapsamlı verimiz <b>Lise</b>, <b>Ortaokul</b>, <b>İlkokul</b> ve <b>Anaokulu</b> için.',
        en: '🔜 Data collection for this segment is still in progress — our most comprehensive data currently covers <b>High School</b>, <b>Middle School</b>, <b>Primary School</b>, and <b>Preschool</b>.',
    },
    seg_preschool: { tr: "01. Okul Öncesi / Anaokulu 🔜", en: "01. Preschool / Kindergarten 🔜" },
    seg_primary: { tr: "02. İlkokul 🔜", en: "02. Primary School 🔜" },
    seg_middle: { tr: "03. Ortaokul 🔜", en: "03. Middle School 🔜" },
    seg_high: { tr: "04. Lise", en: "04. High School" },
    radius_5: { tr: "5 km içinde", en: "Within 5 km" },
    radius_10: { tr: "10 km içinde", en: "Within 10 km" },
    radius_20: { tr: "20 km içinde", en: "Within 20 km" },
    radius_50: { tr: "50 km içinde", en: "Within 50 km" },
    radius_unlimited: { tr: "Sınırsız (sadece sırala)", en: "Unlimited (sort only)" },

    // --- Genel Butonlar ---
    btn_view_details: { tr: "Detayları Gör", en: "View Details" },
    btn_show_more: { tr: "Daha Fazla Göster", en: "Show More" },
    btn_save: { tr: "Kaydet", en: "Save" },
    btn_cancel: { tr: "İptal", en: "Cancel" },

    // --- Footer / Genel ---
    footer_tagline: { tr: "Şeffaf, bağımsız eğitim karar zekası platformu.", en: "A transparent, independent education decision intelligence platform." },
    lang_toggle_label: { tr: "EN", en: "TR" }, // buton hep "diğer dile geç" yazar

    // --- Ortak nav linkleri (emoji dahil, tüm sayfalarda tekrarlanan) ---
    nav_home_emoji: { tr: "Ana Sayfa", en: "Home" },
    nav_explorer_emoji: { tr: "Genel Arama", en: "Explore" },
    nav_lise_skoru_emoji: { tr: "Lise Skoru", en: "School Score" },
    nav_tercih_sihirbazi_emoji: { tr: "Tercih Sihirbazı", en: "Preference Wizard" },
    nav_edunode_emoji: { tr: "EduNode", en: "EduNode" },
    nav_favorilerim_emoji: { tr: "Favorilerim", en: "My Favorites" },
    nav_giris_yap: { tr: "Giriş Yap", en: "Log In" },
    nav_zaten_hesabim_var: { tr: "Zaten hesabım var", en: "I already have an account" },
    nav_giris_sayfasina_don: { tr: "← Giriş sayfasına dön", en: "← Back to login" },
    nav_hesabim_yok: { tr: "Hesabım yok, kayıt ol", en: "No account, sign up" },
    nav_okulunuzu_sahiplenin_cta: { tr: "Okulunuzu Sahiplenin →", en: "Claim Your School →" },
    nav_geri_don: { tr: "← Geri dön", en: "← Go back" },
    nav_genel_aramaya_git: { tr: "Genel Aramaya Git →", en: "Go to Explore →" },
    nav_genel_aramaya: { tr: "Genel aramaya", en: "to explore" },

    // --- Sayfa başlıkları (H1) ---
    h1_edunode: { tr: "EduNode — Okulların Kariyer Ağı", en: "EduNode — Career Network of Schools" },
    h1_favorilerim: { tr: "Favorilerim", en: "My Favorites" },
    h1_giris: { tr: "Giriş Yap", en: "Log In" },
    h1_gizlilik: { tr: "Gizlilik Politikası", en: "Privacy Policy" },
    h1_istatistikler: { tr: "Platform İstatistikleri", en: "Platform Statistics" },
    h1_kayit: { tr: "Kayıt Ol", en: "Sign Up" },
    h1_kurum_paneli: { tr: "Kurum Paneli", en: "Institution Panel" },
    h1_kurumlar_icin: { tr: "Kurumunuzun Profilini Sahiplenin", en: "Claim Your Institution's Profile" },
    h1_lise_skoru: { tr: "Lise Skoru Hesaplayıcı", en: "High School Score Calculator" },
    h1_nasil_calisir: { tr: "EduScor Nasıl Çalışır?", en: "How EduScor Works" },
    h1_tercih_sihirbazi: { tr: "Lise Tercih Sihirbazı", en: "High School Preference Wizard" },

    // --- Giriş paragrafları (H1'in hemen altındaki tanıtım metni) ---
    intro_nasil_calisir: {
        tr: "EduScor, eğitim kararlarını şansa bırakmamanız için kurulmuş bir platform. Nasıl arama yaptığımızı, puanları nasıl hesapladığımızı ve verilerimizin nereden geldiğini burada tam şeffaflıkla açıklıyoruz.",
        en: "EduScor is a platform built so you don't leave education decisions to chance. Here we explain, with full transparency, how we search, how we calculate scores, and where our data comes from.",
    },
    intro_kurumlar_icin: {
        tr: "EduScor'daki okulunuzun/kurumunuzun bilgilerini siz güncelleyin, \"Doğrulanmış\" rozetini kazanın ve velilere en doğru bilgiyi doğrudan siz ulaştırın.",
        en: "Update your school's/institution's information on EduScor yourself, earn the \"Verified\" badge, and deliver the most accurate information to parents directly.",
    },
    intro_tercih_sihirbazi: {
        tr: "LGS yüzdelik diliminizi ve tercihlerinizi girin, gerçekçi olarak yerleşebileceğiniz liseleri görün.",
        en: "Enter your LGS percentile and preferences to see high schools you can realistically be placed into.",
    },
    intro_lise_skoru: {
        tr: "Türkiye'deki liseleri, sizin için önemli olan kriterlere göre ağırlıklandırıp kişiselleştirilmiş bir sıralama oluşturuyoruz. Her kritere 1 (önemsiz) ile 5 (çok önemli) arası bir puan verin.",
        en: "We weight high schools across Turkey according to the criteria that matter to you, creating a personalized ranking. Rate each criterion from 1 (unimportant) to 5 (very important).",
    },
    intro_edunode: {
        tr: "Her okul, yetiştirdiği başarılı isimlerle kanıtlanmış bir düğüm (node). Bir okula tıklayın, o okulun mezunlarını hangi kariyer başarılarına taşıdığını keşfedin.",
        en: "Every school is a proven node through the successful names it has produced. Click a school to discover the career achievements of its graduates.",
    },

    // --- Ana Sayfa: Manifesto Kutusu ---
    manifesto_title: { tr: "Eğitim Kararı Şansa Bırakılmaz", en: "Education Decisions Shouldn't Be Left to Chance" },
    manifesto_subtitle: {
        tr: "EduScor, eğitim kurumlarını ticari kaygılardan uzak, tamamen şeffaf ve bilimsel ağırlıklandırma algoritmalarıyla puanlar. Velilerin ve öğrencilerin doğru veriye ulaşmasını hedefler.",
        en: "EduScor scores educational institutions free from commercial concerns, using fully transparent and scientific weighting algorithms. It aims to help parents and students reach accurate data.",
    },
    manifesto_edunode_title: { tr: "Öne Çıkan Başarı Hikayeleri", en: "Featured Success Stories" },
    manifesto_edunode_subtitle: {
        tr: "Hangi okul, hangi kariyere taşıdı? EduNode'da gerçek, doğrulanmış yolculukları keşfedin.",
        en: "Which school led to which career? Discover real, verified journeys on EduNode.",
    },
    manifesto_edunode_cta: { tr: "Keşfet →", en: "Explore →" },

    // --- Ana Sayfa: 3 Numaralı Kart ---
    card1_title: { tr: "Akademik Gelişim", en: "Academic Development" },
    card1_desc: {
        tr: "Kurumların kitlesel başarı oranları, sınav çıktıları ve proje üretim kapasiteleri objektif metriklerle ölçülür.",
        en: "Institutions' aggregate success rates, exam outcomes, and project output capacity are measured with objective metrics.",
    },
    card2_title: { tr: "Sosyal & Sosyo-Kültürel", en: "Social & Socio-Cultural" },
    card2_desc: {
        tr: "Sanat, spor and kulüp faaliyetlerinin çeşitliliği ile öğrencilerin sosyal ekosisteme katılım endeksleri puanlanır.",
        en: "The diversity of arts, sports, and club activities, along with students' social ecosystem participation indices, are scored.",
    },
    card3_title: { tr: "Fiziksel Donanım", en: "Physical Infrastructure" },
    card3_desc: {
        tr: "Sınıf mevcudiyet standartları, teknolojik altyapı, laboratuvar ve yeşil alan rasyoları analiz edilir.",
        en: "Classroom capacity standards, technological infrastructure, laboratory and green space ratios are analyzed.",
    },

    // --- nasil-calisir.html: Yeni hesaplama mantığı bölümü (23 Ağustos 2026) ---
    h2_kriterler: { tr: "2. Kriterler Kararınızı Nasıl Destekler", en: "2. How Criteria Support Your Decision" },
    how_criteria_intro: {
        tr: 'Her kurum <b>9 somut kriterde</b> değerlendirilir: Akademik Başarı, Yabancı Dil Eğitimi, Üniversiteye Yerleştirme, Fiziksel Altyapı, Sosyal/Kültürel Etkinlikler, Öğretmen Kalitesi, Güvenlik/Disiplin, Konum/Ulaşım, Burs/Ücret. Kurumlardan öznel bir puan ("kendinizi 100 üzerinden değerlendirin") istemiyoruz — bunun yerine <b>somut, doğrulanabilir gerçekler</b> soruyoruz (ör. "haftalık kaç saat yabancı dil dersi var?", "kamera sistemi var mı?"). Skoru bu gerçeklerden, sabit ve şeffaf bir formülle biz hesaplıyoruz.',
        en: 'Every institution is evaluated on <b>9 concrete criteria</b>: Academic Achievement, Foreign Language Education, University Placement, Physical Infrastructure, Social/Cultural Activities, Teacher Quality, Security/Discipline, Location/Transport, Scholarships/Fees. We don\'t ask institutions for a subjective score ("rate yourself out of 100") — instead we ask <b>concrete, verifiable facts</b> (e.g. "how many hours of foreign language instruction per week?", "is there a camera system?"). We compute the score from these facts using a fixed, transparent formula.',
    },
    how_formula_label: { tr: "Formül", en: "Formula" },
    how_formula_text: {
        tr: "Kurum Skoru = Σ(Kriter Puanı × Sabit Ağırlık) / Σ(Sabit Ağırlık)",
        en: "Institution Score = Σ(Criterion Score × Fixed Weight) / Σ(Fixed Weight)",
    },
    how_formula_note: {
        tr: "— sadece VERİSİ OLAN kriterler üzerinden hesaplanır.",
        en: "— calculated only over criteria for which data EXISTS.",
    },
    how_missing_criteria: {
        tr: '<b>Eksik kriterler asla "0 puan" sayılmaz</b> — hesaplamaya hiç dahil edilmez. Her kurum sayfasında, skorun kaç kriterden (9 üzerinden) hesaplandığını ve buna bağlı güven seviyesini (Düşük / Sınırlı / Orta) her zaman görürsünüz.',
        en: '<b>Missing criteria are never counted as "0 points"</b> — they are simply excluded from the calculation. On every institution page, you always see how many of the 9 criteria the score is based on, along with the corresponding confidence level (Low / Limited / Medium).',
    },
    how_personalization: {
        tr: "<b>Kişiselleştirme:</b> Tercih Sihirbazı'nda, LGS yerleşim filtresinden sonra, kalan kriterleri KENDİ önceliklerinize göre (Önemsiz → Çok Önemli) ağırlıklandırabilirsiniz. Bu kişisel sıralama, kurumun resmi skorunu asla değiştirmez — ayrı ve size özel bir hesaplamadır.",
        en: "<b>Personalization:</b> In the Preference Wizard, after the LGS placement filter, you can weight the remaining criteria according to YOUR OWN priorities (Unimportant → Very Important). This personal ranking never changes the institution's official score — it's a separate, personalized calculation just for you.",
    },
    how_oecd_note: {
        tr: '<b>OECD referansı:</b> 9 kriterin boyut yapısı, OECD\'nin <i>Education at a Glance</i> ve PISA çerçevelerindeki çok boyutlu gösterge mantığından esinlenilmiştir. OECD\'nin okulları tek bir sayısal skorla sıralayan resmî, onaylı bir formülü <b>yoktur</b> — skorlama modelimiz kendi başına deneysel ve pilot doğrulaması süren bir sistemdir. Detaylar için <a href="metodoloji.html" class="underline font-semibold">Metodoloji</a> sayfasına bakabilirsiniz.',
        en: '<b>OECD reference:</b> The dimension structure of the 9 criteria is inspired by the multi-dimensional indicator logic in OECD\'s <i>Education at a Glance</i> and PISA frameworks. OECD does <b>not</b> have an official, endorsed formula that ranks schools with a single numerical score — our scoring model is itself experimental and undergoing pilot validation. See the <a href="metodoloji.html" class="underline font-semibold">Methodology</a> page for details.',
    },

    // --- nasil-calisir.html: 23 Ağustos güncellemesi (güncel segment kapsamı, kurum
    // beyanı kaynağı, dürüst veri kapsama notu) ---
    how_search_segment: {
        tr: 'Okul öncesinden lise sona kadar 4 segmentte kapsamlı verimiz var; diğer segmentler (yetişkin eğitimi, kurslar, üniversite vb.) "🔜 Yakında" etiketiyle işaretli, veri toplama süreci devam ediyor.',
        en: 'We have comprehensive data across 4 segments from preschool through high school; other segments (adult education, courses, university, etc.) are marked "🔜 Coming Soon" — data collection is ongoing.',
    },
    source_kurum_title: { tr: "Kurumların Kendi Beyanı", en: "Institutions' Own Declarations" },
    source_kurum_desc: {
        tr: 'Onaylı kurum yöneticileri, kendi kurum panellerinden somut göstergeler girer (ör. "haftalık kaç saat yabancı dil dersi var?", "kamera sistemi var mı?") — biz bu göstergelerden skoru hesaplarız. Bu veri, bağımsız doğrulama tamamlanana kadar "Taslak" olarak işaretlenir.',
        en: 'Approved institution admins enter concrete indicators through their own institution panel (e.g. "how many hours of foreign language instruction per week?", "is there a camera system?") — we compute the score from these indicators. This data is marked as "Draft" until independent verification is complete.',
    },
    how_current_coverage_note: {
        tr: '<b>Dürüstçe belirtelim:</b> Platform henüz erken aşamada olduğu için çoğu kurumun skoru şu an 9 kriterden sadece 1-3 tanesiyle hesaplanıyor — bu yüzden birçok kurum sayfasında "Düşük Güven" rozetini göreceksiniz. Bu, kurumun kalitesiz olduğu anlamına gelmez; sadece o kurum hakkında henüz yeterli doğrulanmış veri toplayamadığımız anlamına gelir. Veri kapsamımız sürekli genişliyor.',
        en: '<b>To be honest:</b> Since the platform is still in an early stage, most institutions\' scores are currently calculated from only 1-3 of the 9 criteria — which is why you\'ll see a "Low Confidence" badge on many institution pages. This does not mean the institution is low-quality; it simply means we haven\'t yet gathered enough verified data about it. Our data coverage is continuously expanding.',
    },

    // --- nasil-calisir.html: Eksik çeviriler (section başlıkları, kartlar, tablo, CTA) ---
    how_section1_title: { tr: "1. Arama Nasıl Çalışır", en: "1. How Search Works" },
    how_section3_title: { tr: "3. Verilerimiz Nereden Geliyor", en: "3. Where Our Data Comes From" },
    how_section4_title: { tr: "4. Rozetlerimiz Ne Anlama Gelir", en: "4. What Our Badges Mean" },

    how_step1_title: { tr: "Konum", en: "Location" },
    how_step1_desc: { tr: "Tarayıcı konumunuzu kullanabilir ya da bir il/ilçe/semt yazabilirsiniz.", en: "You can use your browser's location or type a province/district/neighborhood." },
    how_step2_title: { tr: "Ne arıyorsunuz?", en: "What are you looking for?" },
    how_step3_title: { tr: "Sonuçlar", en: "Results" },
    how_step3_desc: { tr: "Kriterlerinize uyan kurumlar, haritada ve liste halinde, kaynak bilgisiyle birlikte gösterilir.", en: "Institutions matching your criteria are displayed on a map and as a list, together with source information." },

    how_trust_quote: { tr: "\"Hiçbir okul, daha yüksek bir EduScor puanı ya da daha iyi bir öneri satın alamaz.\"", en: "\"No school can purchase a higher EduScor score or a better recommendation.\"" },
    how_trust_subtitle: { tr: "Bu, değişmez bir platform ilkemizdir.", en: "This is an immutable platform principle." },

    how_source_meb_title: { tr: "MEB (Milli Eğitim Bakanlığı)", en: "MEB (Ministry of National Education)" },
    how_source_meb_desc: { tr: "Kamu okullarının resmi listesi, adları, türleri — MEB'in kamuya açık sayfalarından.", en: "Official list, names, and types of public schools — from MEB's publicly accessible pages." },
    how_source_lgs_title: { tr: "MEB LGS Yerleştirme Kılavuzu", en: "MEB LGS Placement Guide" },
    how_source_lgs_desc: { tr: "Liselerin akademik başarı ve yabancı dil kriterleri, resmi MEB PDF kılavuzundan.", en: "Academic achievement and foreign language criteria for high schools, from the official MEB PDF guide." },
    how_source_ookgm_title: { tr: "ÖOKGM (Özel Öğretim Kurumları Genel Müdürlüğü)", en: "OOKGM (Directorate General of Private Education Institutions)" },
    how_source_ookgm_desc: { tr: "Özel okullar, kurslar ve merkezlerin resmi kayıt listesi.", en: "Official registration list of private schools, courses, and centers." },
    how_source_osm_title: { tr: "OpenStreetMap", en: "OpenStreetMap" },
    how_source_osm_desc: { tr: "Açık kaynak harita verisi — konum/koordinat bilgisi için.", en: "Open source map data — for location/coordinate information." },
    how_source_kurum_title2: { tr: "Kurumların Kendi Beyanı", en: "Institutions' Own Declarations" },
    how_source_kurum_desc2: {
        tr: 'Onaylı kurum yöneticileri, kendi kurum panellerinden somut göstergeler girer (ör. "haftalık kaç saat yabancı dil dersi var?", "kamera sistemi var mı?") — biz bu göstergelerden skoru hesaplarız. Bu veri, bağımsız doğrulama tamamlanana kadar "Taslak" olarak işaretlenir.',
        en: 'Approved institution admins enter concrete indicators through their own institution panel (e.g. "how many hours of foreign language instruction per week?", "is there a camera system?") — we compute the score from these indicators. This data is marked as "Draft" until independent verification is complete.',
    },

    how_badge_col1: { tr: "Rozet", en: "Badge" },
    how_badge_col2: { tr: "Nasıl elde edildi?", en: "How was it obtained?" },
    how_badge_col3: { tr: "Güvenilirlik", en: "Reliability" },
    how_badge_verified: { tr: "✓ Doğrulanmış", en: "✓ Verified" },
    how_badge_verified_desc: { tr: "Kurumun kendisi (yetkilisi) tarafından teyit edildi ya da birincil resmi bir kaynaktan doğrudan alındı.", en: "Confirmed by the institution itself (authorized representative) or obtained directly from a primary official source." },
    how_badge_verified_rel: { tr: "Yüksek", en: "High" },
    how_badge_draft: { tr: "🔍 Taslak Veri", en: "🔍 Draft Data" },
    how_badge_draft_desc: { tr: "Otomatik olarak resmi kaynaklardan (MEB, ÖOKGM vb.) derlendi, henüz kurum tarafından teyit edilmedi.", en: "Automatically compiled from official sources (MEB, OOKGM, etc.), not yet confirmed by the institution." },
    how_badge_draft_rel: { tr: "Orta — kaynağı resmi ama güncelliği teyitli değil", en: "Medium — source is official but currency is unverified" },

    how_cta: { tr: "Aramaya Başla →", en: "Start Searching →" },

    // --- Ana Sayfa: Manifesto ödeme notu ---
    manifesto_payment_note: { tr: "🔒 Ödeme, hiçbir kurumun EduScor puanını iyileştirmez.", en: "🔒 Payment never improves any institution's EduScor score." },

    // --- Ana Sayfa: Lise Öncelikleri kartı ---
    lise_priority_title: { tr: "Öncelikleriniz", en: "Your Priorities" },
    lise_priority_subtitle: { tr: "(isteğe bağlı — sonraki sayfada da değiştirebilirsiniz)", en: "(optional — you can also change this on the next page)" },

    // --- Ana Sayfa: Segment Dropdown (yakında gelecek kategoriler) ---
    seg_group_higher: { tr: "Yükseköğretim & Dijital", en: "Higher Education & Digital" },
    seg_university: { tr: "05. Üniversiteler / Yükseköğretim Kurumları 🔜", en: "05. Universities / Higher Education Institutions 🔜" },
    seg_distance: { tr: "06. Açık ve Uzaktan Eğitim Kurumları 🔜", en: "06. Open and Distance Education Institutions 🔜" },
    seg_edtech: { tr: "07. EdTech Platformları & Dijital İçerik Sağlayıcılar 🔜", en: "07. EdTech Platforms & Digital Content Providers 🔜" },
    seg_group_courses: { tr: "Özel Kurslar & Gelişim", en: "Private Courses & Development" },
    seg_courses: { tr: "08. Kurslar & Özel Ders Merkezleri 🔜", en: "08. Courses & Private Tutoring Centers 🔜" },
    seg_language: { tr: "09. Dil Okulları & Yurtdışı Eğitim 🔜", en: "09. Language Schools & Study Abroad 🔜" },
    seg_driving: { tr: "10. Sürücü, Ulaştırma & Havacılık Akademileri 🔜", en: "10. Driving, Transportation & Aviation Academies 🔜" },
    seg_sports_arts: { tr: "11. Spor, Sanat & Beceri Akademileri 🔜", en: "11. Sports, Arts & Skills Academies 🔜" },
    seg_group_special: { tr: "Özel Alanlar & Kamplar", en: "Special Areas & Camps" },
    seg_special: { tr: "12. Özel Gereksinim Eğitim Kurumları 🔜", en: "12. Special Needs Education Institutions 🔜" },
    seg_camps: { tr: "13. Eğitim, Bilim & Gelişim Kampları 🔜", en: "13. Education, Science & Development Camps 🔜" },
    seg_summer: { tr: "14. Yaz / Kış Okulları 🔜", en: "14. Summer / Winter Schools 🔜" },
    seg_group_corporate: { tr: "Kurumsal, Profesyonel & Toplumsal", en: "Corporate, Professional & Community" },
    seg_corporate: { tr: "15. Kurumsal Akademiler & Profesyonel Gelişim 🔜", en: "15. Corporate Academies & Professional Development 🔜" },
    seg_lifelong: { tr: "16. Sürekli Eğitim & Yaşam Boyu Öğrenme 🔜", en: "16. Continuing Education & Lifelong Learning 🔜" },
    seg_vocational: { tr: "17. Mesleki & Teknik Eğitim Merkezleri 🔜", en: "17. Vocational & Technical Education Centers 🔜" },
    seg_stk: { tr: "18. STK, Vakıf & Topluluk Eğitimleri 🔜", en: "18. NGO, Foundation & Community Education 🔜" },
    seg_defense: { tr: "19. Savunma, Güvenlik & Askeri Akademiler 🔜", en: "19. Defense, Security & Military Academies 🔜" },
    seg_religious: { tr: "20. Dini & İlahiyat Eğitim Kurumları 🔜", en: "20. Religious & Theological Education Institutions 🔜" },

    // --- Ana Sayfa: Konum izni mesajı ---
    location_denied_msg: { tr: 'Konum izni verilmedi. Sorun yok — aşağıya <b>il veya ilçenizi</b> yazarak da arayabilirsiniz.', en: 'Location permission denied. No problem — you can also search by typing your <b>city or district</b> below.' },

    // --- Site Geneli: Footer ---
    footer_about: { tr: "Hakkımızda", en: "About Us" },
    footer_contact: { tr: "İletişim", en: "Contact" },
    footer_privacy: { tr: "Gizlilik Politikası", en: "Privacy Policy" },

    // --- Ana Sayfa: Başarı Hikayeleri Şeridi (unvanlar) ---
    ticker_title_1: { tr: "Bilim İnsanı, Bilkent Üniversitesi Eski Rektörü", en: "Scientist, Former Rector of Bilkent University" },
    ticker_title_2: { tr: "Mühendis, NASA Mars Projesi", en: "Engineer, NASA Mars Project" },
    ticker_title_3: { tr: "Oyuncu", en: "Actor" },
    ticker_title_4: { tr: "NBA Basketbolcusu (Houston Rockets)", en: "NBA Basketball Player (Houston Rockets)" },
    ticker_title_5: { tr: "Nobel Ödüllü Bilim İnsanı (Kimya, 2015)", en: "Nobel Laureate Scientist (Chemistry, 2015)" },
    ticker_title_6: { tr: "Sanatçı, Türkiye Cumhuriyeti Devlet Sanatçısı", en: "Artist, State Artist of the Republic of Türkiye" },
    ticker_title_7: { tr: "Matematikçi, \"Arf Değişmezi\" Teorisinin Bulucusu", en: "Mathematician, Discoverer of the \"Arf Invariant\" Theory" },
    ticker_title_8: { tr: "Müzisyen, Besteci, Moğollar Grubu Kurucusu", en: "Musician, Composer, Founder of Moğollar Band" },
    ticker_title_9: { tr: "Oyuncu, Uluslararası Yıldız", en: "Actor, International Star" },
    ticker_title_10: { tr: "Fizik Mühendisi, MIT Profesörü", en: "Physics Engineer, MIT Professor" },
    ticker_title_11: { tr: "Astrofizikçi, İlk Kara Delik Fotoğrafı Ekibi Üyesi", en: "Astrophysicist, Member of the First Black Hole Image Team" },
    ticker_title_12: { tr: "Beyin Cerrahı, \"Yüzyılın Beyin Cerrahı\"", en: "Neurosurgeon, \"Neurosurgeon of the Century\"" },
    ticker_title_13: { tr: "Tiyatro Yönetmeni ve Oyuncusu, Devlet Sanatçısı", en: "Theatre Director and Actor, State Artist" },
    ticker_title_14: { tr: "Girişimci, Chobani Kurucusu", en: "Entrepreneur, Founder of Chobani" },
    ticker_title_15: { tr: "İş İnsanı, Finansbank Kurucusu", en: "Businessman, Founder of Finansbank" },
    ticker_title_16: { tr: "Tarihçi, Akademisyen, Yazar", en: "Historian, Academic, Author" },
    ticker_title_17: { tr: "Besteci ve Piyanist", en: "Composer and Pianist" },
    ticker_title_18: { tr: "İş İnsanı, Yıldız Holding Yönetim Kurulu Başkanı", en: "Businessman, Chairman of Yıldız Holding" },
    ticker_title_19: { tr: "1994 ÖYS Fen-Matematik Türkiye Birincisi", en: "1994 ÖYS Science-Mathematics National First Place" },
    ticker_title_20: { tr: "Psikiyatrist, Üsküdar Üniversitesi Kurucu Rektörü", en: "Psychiatrist, Founding Rector of Üsküdar University" },
    ticker_title_21: { tr: "Ekonomist, Dünya Bankası Direktörü", en: "Economist, World Bank Director" },
    ticker_title_22: { tr: "Sanatçı, 2003 Eurovision Şampiyonu", en: "Artist, 2003 Eurovision Champion" },
    ticker_title_23: { tr: "Sporcu, Beşiktaş Onursal Başkanı", en: "Athlete, Honorary President of Beşiktaş" },
    ticker_title_24: { tr: "İş İnsanı, Turkcell Eski CEO'su", en: "Businessman, Former CEO of Turkcell" },
    ticker_title_25: { tr: "İş İnsanı, Koç Holding Kurucusu", en: "Businessman, Founder of Koç Holding" },

    // --- Sayfa Başlığı (tarayıcı sekmesi) ---
    page_title_home: { tr: "EduScor | Eğitim Kararı Şansa Bırakılmaz", en: "EduScor | Education Decisions Shouldn't Be Left to Chance" },

    // --- Okul Detay: Genel Başarı Skoru bloğu (EDU-SCORE-002) ---
    // {degisken} yer tutucuları tf() ile doldurulur. HTML içerir, innerHTML ile kullanılır.
    score_general_title: { tr: "Genel Başarı Skoru", en: "Overall Success Score" },
    score_current_measure: { tr: "Mevcut Ölçüm", en: "Current Measurement" },
    score_evidence_badge: { tr: "Kanıt kapsamı %{kapsam} · {etiket}", en: "Evidence coverage {kapsam}% · {etiket}" },
    score_evidence_broad: { tr: "Geniş Kanıt", en: "Broad Evidence" },
    score_evidence_medium: { tr: "Orta Kanıt", en: "Moderate Evidence" },
    score_evidence_limited: { tr: "Sınırlı Kanıt", en: "Limited Evidence" },
    score_insufficient_badge: { tr: "Genel skor için veri yetersiz", en: "Insufficient data for an overall score" },
    score_explain: {
        tr: "Bu skor, bu kurum türü için uygulanabilir {toplam} kriterden <b>{n} tanesine</b> dayanan ağırlıklı bir ortalamadır. Kriterlerin önem ağırlıkları dikkate alındığında <b>kanıt kapsamı: %{kapsam}</b>. Eksik kriterler için henüz güvenilir bir veri kaynağı bulunamadığından dahil edilmemiş, sıfır da sayılmamıştır. Bu skoru <b>kesin bir sonuç değil, elimizdeki kısmi veriye dayalı bir gösterge</b> olarak değerlendirin.",
        en: "This score is a weighted average based on <b>{n}</b> of the {toplam} criteria applicable to this type of institution. Taking the criteria weights into account, <b>evidence coverage: {kapsam}%</b>. Missing criteria are neither included nor counted as zero, because no reliable data source has been found for them yet. Treat this score <b>as an indicator based on partial data, not a definitive result</b>."
    },
    score_insufficient_explain: {
        tr: "Bu kurum için şu an uygulanabilir {toplam} kriterden yalnızca {n} kritere ait veri var. Tek bir ölçüm okulun genel durumunu yansıtmadığı için <b>Genel Başarı Skoru hesaplanmamıştır</b>; genel skor için kanıt kapsamının en az %{esik} olması gerekir. Yukarıdaki değer yalnızca kendi kriterini ifade eder. Yeni veriler eklendikçe genel skor otomatik olarak hesaplanacaktır.",
        en: "Data is currently available for only {n} of the {toplam} criteria applicable to this institution. Since a single measurement does not reflect the school's overall picture, <b>no Overall Success Score has been calculated</b>; an overall score requires evidence coverage of at least {esik}%. The value above refers only to its own criterion. The overall score will be calculated automatically as new data is added."
    },
    // --- Okul Detay sayfasi arayuz metinleri (od_) ---
    od_match_title: { tr: "Sizin Kriterlerinize Göre", en: "Based on Your Criteria" },
    od_match_note: { tr: "EduScor, kurumun genel değerlendirmesini gösterir — sizin için en uygun seçim, kendi önceliklerinize göre değişebilir.", en: "EduScor shows the institution's overall assessment — the best choice for you may vary according to your own priorities." },
    od_match_info_title: { tr: "Skor nasıl hesaplandı?", en: "How was the score calculated?" },
    od_match_text: { tr: "%{s} Uyumlu (Kişisel Skor: {s})", en: "{s}% Match (Personal Score: {s})" },
    od_match_general: { tr: "Genel EduScor (Mevcut Verilere Göre)", en: "Overall EduScor (Based on Available Data)" },
    od_loading: { tr: "Kurum bilgileri yükleniyor...", en: "Loading institution details..." },
    od_not_found: { tr: "Kurum bulunamadı", en: "Institution not found" },
    od_not_found_hint: { tr: "Bağlantı geçersiz olabilir. <a href=\"explorer.html\" class=\"text-brandRed underline\">Genel aramaya</a> dönebilirsiniz.", en: "The link may be invalid. You can return to the <a href=\"explorer.html\" class=\"text-brandRed underline\">general search</a>." },
    od_fav_add: { tr: "Listeme Ekle", en: "Add to My List" },
    od_fav_added: { tr: "Listemde", en: "In My List" },
    od_view_google: { tr: "Google'da görüntüle →", en: "View on Google →" },
    od_website: { tr: "Web sitesi →", en: "Website →" },
    od_distance_btn: { tr: "📍 Buradan Ne Kadar Uzak?", en: "📍 How Far Is It From Here?" },
    od_getting_location: { tr: "⏳ Konumunuz alınıyor...", en: "⏳ Getting your location..." },
    od_distance_result: { tr: "📏 Kuş uçuşu ~{km} km uzakta", en: "📏 About {km} km away as the crow flies" },
    od_location_denied: { tr: "Konumunuza erişilemedi. Tarayıcı ayarlarından konum iznini kontrol edin.", en: "We couldn't access your location. Please check the location permission in your browser settings." },
    od_institution: { tr: "Kurum", en: "Institution" },
    od_badge_public: { tr: "🏛️ Kamu", en: "🏛️ Public" },
    od_badge_private: { tr: "🎓 Özel", en: "🎓 Private" },
    od_badge_verified: { tr: "✓ Doğrulanmış", en: "✓ Verified" },
    od_badge_draft: { tr: "🔍 Taslak Veri", en: "🔍 Draft Data" },
    od_tab_general: { tr: "📋 Genel Bilgi", en: "📋 General Info" },
    od_tab_gallery: { tr: "🖼️ Galeri", en: "🖼️ Gallery" },
    od_gal_sports: { tr: "Spor Kulübü", en: "Sports Club" },
    od_gal_theatre: { tr: "Tiyatro", en: "Theatre" },
    od_gal_robotics: { tr: "Robotik", en: "Robotics" },
    od_gal_music: { tr: "Müzik", en: "Music" },
    od_gal_note: { tr: "Gerçek fotoğraflar, kurum \"Profilini Sahiplen\"dikçe burada görünecek.", en: "Real photos will appear here once the institution claims its profile." },
    od_contact_btn: { tr: "📞 Okuldan Bilgi / Randevu Talep Et", en: "📞 Request Info / an Appointment" },
    od_contact_title: { tr: "Bilgi / Randevu Talep Et", en: "Request Info / an Appointment" },
    od_contact_note: { tr: "Talebiniz, kurumun EduScor profilindeki iletişim bilgilerine iletilir.", en: "Your request will be forwarded to the contact details on the institution's EduScor profile." },
    od_f_name: { tr: "Ad Soyad", en: "Full Name" },
    od_f_contact: { tr: "Telefon ya da E-posta", en: "Phone or Email" },
    od_f_message: { tr: "Mesajınız", en: "Your Message" },
    od_ph_message: { tr: "örn. Kayıt koşulları hakkında bilgi almak istiyorum.", en: "e.g. I would like information about enrollment requirements." },
    od_send: { tr: "Gönder", en: "Send" },
    od_request_sent: { tr: "✓ Talebiniz iletildi!", en: "✓ Your request has been sent!" },
    od_err_retry: { tr: "Bir hata oluştu, lütfen tekrar deneyin.", en: "An error occurred, please try again." },
    od_cost_title: { tr: "Yıllık Toplam Maliyet (Tahmini)", en: "Estimated Total Annual Cost" },
    od_total: { tr: "Toplam", en: "Total" },
    od_cost_note: { tr: "Bu rakamlar kurum tarafından \"Profilini Sahiplen\" üzerinden bildirilmiştir, yıldan yıla değişebilir.", en: "These figures were reported by the institution via \"Claim Your Profile\" and may change from year to year." },
    od_cost_period: { tr: "📅 {y1}-{y2} Eğitim Dönemi Verisidir", en: "📅 Data for the {y1}-{y2} School Year" },
    od_c_tuition: { tr: "Eğitim", en: "Tuition" },
    od_c_meals: { tr: "Yemek", en: "Meals" },
    od_c_bus: { tr: "Servis", en: "School Bus" },
    od_c_books: { tr: "Kitap", en: "Books" },
    od_c_uniform: { tr: "Kıyafet", en: "Uniform" },
    od_c_tutoring: { tr: "Etüt/Kurs", en: "Tutoring/Courses" },
    od_c_other: { tr: "Diğer", en: "Other" },
    od_i_phone: { tr: "Telefon", en: "Phone" },
    od_i_email: { tr: "E-posta", en: "Email" },
    od_i_age: { tr: "Yaş Aralığı", en: "Age Range" },
    od_i_students: { tr: "👥 Öğrenci Sayısı", en: "👥 Number of Students" },
    od_i_class: { tr: "Ort. Sınıf Mevcudu", en: "Avg. Class Size" },
    od_i_fee: { tr: "Ücret", en: "Fees" },
    od_i_transport: { tr: "Ulaşım", en: "Transport" },
    od_i_bus: { tr: "Servis", en: "School Bus" },
    od_i_security: { tr: "Güvenlik", en: "Security" },
    od_i_social: { tr: "Sosyal & Sportif", en: "Social & Sports" },
    od_i_capacity: { tr: "Kontenjan", en: "Capacity" },
    od_i_teacher_exp: { tr: "Öğretmen Deneyimi", en: "Teacher Experience" },
    od_fact_lab: { tr: "🔬 Laboratuvar", en: "🔬 Laboratory" },
    od_fact_gym: { tr: "🏀 Kapalı Spor Salonu", en: "🏀 Indoor Sports Hall" },
    od_fact_library: { tr: "📚 Kütüphane", en: "📚 Library" },
    od_fact_cafeteria: { tr: "🍽️ Yemekhane", en: "🍽️ Cafeteria" },
    od_criteria_title: { tr: "Kriter Puanları", en: "Criteria Scores" },
    od_no_criteria: { tr: "Bu kurum için henüz kriter bazlı puan verisi yok.", en: "There is no criteria-based score data for this institution yet." },
    od_no_criteria_middle: { tr: "Bu kurum için henüz kriter bazlı puan verisi yok. <b>Not:</b> Ortaokullar için akademik başarı kriteri bilerek eklenmemiştir — MEB, ortaokulların mezun öğrencilerinin LGS başarısını okul bazında kamuya açık yayınlamamaktadır (araştırdık, merkezi/güvenilir bir kaynak bulunmuyor). Diğer kriterler \"Profilini Sahiplen\" ile okul yöneticisi tarafından doldurulabilir.", en: "There is no criteria-based score data for this institution yet. <b>Note:</b> The academic achievement criterion is intentionally not included for middle schools — the Ministry of Education (MEB) does not publicly publish middle schools' graduates' LGS results on a per-school basis (we researched this; no central, reliable source exists). Other criteria can be filled in by the school administrator via \"Claim Your Profile\"." },
    od_criterion: { tr: "Kriter", en: "Criterion" },
    od_no_breakdown: { tr: "Kırılım için yeterli kriter verisi yok.", en: "Not enough criteria data for a breakdown." },
    od_b_base_pct: { tr: "Taban Yüzdelik Dilimi", en: "Minimum Percentile" },
    od_b_base_score: { tr: "Taban Puanı", en: "Minimum Score" },
    od_b_data_year: { tr: "Veri Yılı", en: "Data Year" },
    od_b_total_placed: { tr: "Toplam Yerleşen (4 Yıl)", en: "Total Placed (4 Years)" },
    od_b_first_year: { tr: "İlk Sene Yerleşme Başarısı", en: "First-Year Placement Rate" },
    od_b_unis: { tr: "Farklı Üniversite", en: "Different Universities" },
    od_b_duration: { tr: "Program Süresi", en: "Program Duration" },
    od_years: { tr: "{n} yıl", en: "{n} years" },
    od_src_akademik: { tr: "Kaynak: MEB LGS Yerleştirme Kılavuzu · Yıllık güncellenir", en: "Source: MEB LGS Placement Guide · Updated annually" },
    od_src_dil: { tr: "Kaynak: MEB LGS Kılavuzu · Yıllık güncellenir", en: "Source: MEB LGS Guide · Updated annually" },
    od_src_uni: { tr: "Kaynak: Okul sitesi / sinavizcisi.com (YKS sonuçları) · Düzensiz güncellenir", en: "Source: School website / sinavizcisi.com (YKS results) · Updated irregularly" },
    od_src_default: { tr: "Kaynak: Henüz merkezi kaynak yok — okul yöneticileri \"Profilini Sahiplen\" ile girebilir", en: "Source: No central source yet — school administrators can enter it via \"Claim Your Profile\"" },
    od_location: { tr: "Konum", en: "Location" },
    od_programs: { tr: "Programlar", en: "Programs" },
    od_similar: { tr: "Benzer Kurumlar", en: "Similar Institutions" },
    od_th_school: { tr: "Okul", en: "School" },
    od_th_percentile: { tr: "Yüzdelik Dilim", en: "Percentile" },
    od_th_type: { tr: "Tür", en: "Type" },
    od_public: { tr: "Devlet", en: "Public" },
    od_private: { tr: "Özel", en: "Private" },
    od_success_stories: { tr: "Bu okuldan çıkan başarı hikayeleri", en: "Success stories from this school" },
    od_edunode_cta: { tr: "EduNode'da yolculuklarını keşfedin →", en: "explore their journeys on EduNode →" },
    od_reviews_title: { tr: "Kullanıcı Değerlendirmeleri", en: "User Reviews" },
    od_no_reviews: { tr: "Henüz kullanıcı değerlendirmesi yok — ilk yorumu siz yapın.", en: "No user reviews yet — be the first to write one." },
    od_login_to_review: { tr: "Yorum yapmak için giriş yapın.", en: "Log in to write a review." },
    od_your_rating: { tr: "Genel Puanınız", en: "Your Overall Rating" },
    od_detailed: { tr: "Detaylı Değerlendirme <span class=\"font-normal\">(isteğe bağlı - doldurdukça değerlendirmemiz daha güvenilir olur)</span>", en: "Detailed Assessment <span class=\"font-normal\">(optional - the more you fill in, the more reliable our assessment becomes)</span>" },
    od_ph_review: { tr: "Deneyiminizi paylaşın (opsiyonel)...", en: "Share your experience (optional)..." },
    od_submit_review: { tr: "Yorumu Gönder", en: "Submit Review" },
    od_reviews_count: { tr: "{n} veli değerlendirdi", en: "{n} parents reviewed" },
    od_anonymous: { tr: "Anonim Kullanıcı", en: "Anonymous User" },
    od_pick_rating: { tr: "Lütfen bir puan seçin.", en: "Please select a rating." },
    od_err_retry2: { tr: "Bir hata oluştu, tekrar deneyin.", en: "An error occurred, please try again." },
    od_review_saved: { tr: "Yorumunuz kaydedildi, teşekkürler!", en: "Your review has been saved, thank you!" },
    od_trust_high: { tr: "Güven Seviyesi: Yüksek", en: "Confidence Level: High" },
    od_trust_medium: { tr: "Güven Seviyesi: Orta", en: "Confidence Level: Medium" },
    od_trust_initial: { tr: "Güven Seviyesi: Başlangıç", en: "Confidence Level: Initial" },
    od_r_teacher: { tr: "Öğretmen Kalitesi", en: "Teacher Quality" },
    od_r_guidance: { tr: "Rehberlik", en: "Guidance" },
    od_r_management: { tr: "Yönetim", en: "Management" },
    od_r_social: { tr: "Sosyal Yaşam", en: "Social Life" },
    od_r_pressure: { tr: "Akademik Baskı", en: "Academic Pressure" },
    od_r_safety: { tr: "Güvenlik", en: "Safety" },
    od_r_food: { tr: "Yemek", en: "Food" },
    od_r_transport: { tr: "Ulaşım", en: "Transport" },
    od_r_uniprep: { tr: "Üniversite Hazırlığı", en: "University Preparation" },
    od_claim_title: { tr: "Bu Sizin Kurumunuz mu?", en: "Is This Your Institution?" },
    od_claim_login: { tr: "Kurum bilgilerini güncellemek için önce giriş yapmanız gerekiyor.", en: "You need to log in first to update the institution's details." },
    od_claim_intro: { tr: "Bu kurumun yöneticisi/öğretmeniyseniz profili sahiplenip bilgileri güncelleyebilirsiniz.", en: "If you are an administrator or teacher at this institution, you can claim the profile and update its details." },
    od_role_admin: { tr: "Okul Yöneticisiyim", en: "I am a School Administrator" },
    od_role_teacher: { tr: "Öğretmenim", en: "I am a Teacher" },
    od_ph_verify: { tr: "Kendinizi nasıl doğrularsınız? (örn. resmi okul e-postanız, göreviniz)", en: "How can you verify yourself? (e.g. your official school email, your role)" },
    od_claim_submit: { tr: "Sahiplenme Talebi Gönder", en: "Submit Claim Request" },
    od_claim_pending: { tr: "⏳ Sahiplenme talebiniz inceleniyor.", en: "⏳ Your claim request is under review." },
    od_claim_ok: { tr: "✓ Bu kurumu sahiplendiniz. Bilgileri aşağıdan güncelleyebilirsiniz.", en: "✓ You have claimed this institution. You can update its details below." },
    od_e_address: { tr: "Adres", en: "Address" },
    od_e_website: { tr: "Web Sitesi", en: "Website" },
    od_e_age: { tr: "Yaş Aralığı (Min-Max)", en: "Age Range (Min-Max)" },
    od_e_campus: { tr: "Yerleşke Özellikleri", en: "Campus Features" },
    od_ph_area: { tr: "Yerleşke alanı (m²)", en: "Campus area (m²)" },
    od_e_fee: { tr: "Ücret Bilgisi (genel not)", en: "Fee Information (general note)" },
    od_ph_fee: { tr: "örn. 15.000-25.000 TL/yıl", en: "e.g. 15,000-25,000 TL/year" },
    od_e_transport: { tr: "Ulaşım Notu", en: "Transport Note" },
    od_ph_transport: { tr: "örn. Metro 400m", en: "e.g. Metro 400m" },
    od_e_cost_items: { tr: "Yıllık Maliyet Kalemleri (TL) — opsiyonel, doldurursanız toplam otomatik hesaplanır", en: "Annual Cost Items (TL) — optional; if filled in, the total is calculated automatically" },
    od_e_bus: { tr: "Servis Bilgisi", en: "School Bus Information" },
    od_ph_bus: { tr: "örn. Ücretli servis, 5 hat", en: "e.g. Paid school bus, 5 routes" },
    od_e_security: { tr: "Güvenlik Bilgisi", en: "Security Information" },
    od_ph_security: { tr: "örn. Turnike, 7/24 güvenlik", en: "e.g. Turnstiles, 24/7 security" },
    od_e_social: { tr: "Sosyal & Sportif Olanaklar", en: "Social & Sports Facilities" },
    od_ph_social: { tr: "örn. 12 aktif kulüp, kapalı yüzme havuzu", en: "e.g. 12 active clubs, indoor swimming pool" },
    od_e_capacity: { tr: "Kontenjan Bilgisi", en: "Capacity Information" },
    od_ph_capacity: { tr: "örn. 160 kontenjan, 145 dolu", en: "e.g. 160 places, 145 filled" },
    od_e_teacher_exp: { tr: "Öğretmen Deneyimi", en: "Teacher Experience" },
    od_ph_teacher_exp: { tr: "örn. Ortalama 8 yıl kıdem", en: "e.g. 8 years of experience on average" },
    od_e_description: { tr: "Açıklama", en: "Description" },
    od_save: { tr: "Bilgileri Kaydet", en: "Save Details" },
    od_err_prefix: { tr: "Bir hata oluştu:", en: "An error occurred:" },
    od_note_original: { tr: "Orijinal not (Türkçe):", en: "Original note (Turkish):" },
    od_no_data: { tr: "Veri yok", en: "No data" },
    od_saved_reload: { tr: "Bilgiler kaydedildi! Sayfa yenileniyor...", en: "Details saved! Reloading the page..." },
};

function getLang() {
    return localStorage.getItem("eduscor_lang") || "tr";
}

function setLang(lang) {
    localStorage.setItem("eduscor_lang", lang);
    applyI18n();
    document.documentElement.setAttribute("lang", lang);
    // applyI18n() yalnızca data-i18n etiketli öğeleri günceller. JavaScript ile
    // üretilen içerik (örn. okul-detay skor bloğu) bu olayı dinleyip kendini
    // yeni dilde yeniden çizebilir.
    document.dispatchEvent(new CustomEvent("eduscor:langchange", { detail: { lang } }));
}

// Değişken içeren çeviriler: tf("anahtar", { n: 4 }) -> metindeki {n} yerine 4
function tf(key, vars) {
    let s = t(key);
    Object.keys(vars || {}).forEach((k) => { s = s.split("{" + k + "}").join(vars[k]); });
    return s;
}

function toggleLang() {
    setLang(getLang() === "tr" ? "en" : "tr");
}

function t(key) {
    const entry = I18N_DICT[key];
    if (!entry) {
        console.warn(`i18n: bilinmeyen anahtar "${key}"`);
        return key;
    }
    const lang = getLang();
    // ÖNEMLİ: boş string ("") geçerli bir çeviri olabilir (ör. "Alın" fiilinin
    // İngilizce'de karşılığı yok). `||` operatörü boş string'i "değer yok"
    // sayıp yanlışlıkla Türkçe'ye geri düşüyordu - bunun yerine tip kontrolü yapıyoruz.
    return typeof entry[lang] === "string" ? entry[lang] : entry.tr;
}

function applyI18n() {
    const lang = getLang();
    document.documentElement.setAttribute("lang", lang);

    document.querySelectorAll("[data-i18n]").forEach((el) => {
        el.textContent = t(el.getAttribute("data-i18n"));
    });
    // data-i18n-html: çeviri HTML içeriyorsa (ör. <b>kalın</b>) innerHTML kullanılır.
    // Sadece sözlükteki sabit, geliştirici tarafından yazılan metinler için -
    // asla kullanıcı girdisiyle doldurulmaz (XSS riski yok).
    document.querySelectorAll("[data-i18n-html]").forEach((el) => {
        el.innerHTML = t(el.getAttribute("data-i18n-html"));
    });
    document.querySelectorAll("[data-i18n-title]").forEach((el) => {
        el.setAttribute("title", t(el.getAttribute("data-i18n-title")));
    });
    document.querySelectorAll("[data-i18n-placeholder]").forEach((el) => {
        el.setAttribute("placeholder", t(el.getAttribute("data-i18n-placeholder")));
    });
    // data-i18n-label: <optgroup label="..."> gibi textContent/innerHTML
    // kullanamayan elemanların label attribute'unu çevirir.
    document.querySelectorAll("[data-i18n-label]").forEach((el) => {
        el.setAttribute("label", t(el.getAttribute("data-i18n-label")));
    });

    const toggleBtn = document.getElementById("langToggleBtn");
    if (toggleBtn) toggleBtn.textContent = t("lang_toggle_label");
    const footerBtn = document.getElementById("footerLangBtn");
    if (footerBtn) footerBtn.textContent = t("lang_toggle_label");
}

document.addEventListener("DOMContentLoaded", applyI18n);

// Paylaşılan hamburger menü mantığı - id="menuToggle" / id="mobileNavLinks"
// bulunan HERHANGİ bir sayfada otomatik çalışır, yoksa sessizce hiçbir şey yapmaz.
document.addEventListener("DOMContentLoaded", () => {
    const menuToggle = document.getElementById("menuToggle");
    const mobileLinks = document.getElementById("mobileNavLinks");
    if (!menuToggle || !mobileLinks) return;

    // ÖNEMLİ: Dropdown'ın üst konumu SABİT piksel yerine GERÇEK header
    // yüksekliğinden hesaplanır - aksi halde header'ın kendi padding'i
    // sayfadan sayfaya farklı olduğunda dropdown header'la çakışır ("kayma").
    const header = document.querySelector("header");
    function positionMobileMenu() {
        if (header) mobileLinks.style.top = header.offsetHeight + "px";
        // NOT: Tam ekran yükseklik KASITLI OLARAK kaldırıldı - menü sadece
        // link kadar yer kaplasın, alttaki sayfa içeriği (kartlar vb.) görünür kalsın.
    }
    positionMobileMenu();
    window.addEventListener("resize", positionMobileMenu);

    menuToggle.addEventListener("click", () => {
        positionMobileMenu();
        menuToggle.classList.toggle("active");
        mobileLinks.classList.toggle("active");
    });

    document.addEventListener("click", (e) => {
        if (!mobileLinks.contains(e.target) && !menuToggle.contains(e.target) && mobileLinks.classList.contains("active")) {
            menuToggle.classList.remove("active");
            mobileLinks.classList.remove("active");
        }
    });
});
