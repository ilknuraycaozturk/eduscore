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
    search_near_me: { tr: "📍 Yakınımda Ara", en: "📍 Search Near Me" },

    // --- Genel Butonlar ---
    btn_view_details: { tr: "Detayları Gör", en: "View Details" },
    btn_show_more: { tr: "Daha Fazla Göster", en: "Show More" },
    btn_save: { tr: "Kaydet", en: "Save" },
    btn_cancel: { tr: "İptal", en: "Cancel" },

    // --- Footer / Genel ---
    footer_tagline: { tr: "Şeffaf, bağımsız eğitim karar zekası platformu.", en: "A transparent, independent education decision intelligence platform." },
    lang_toggle_label: { tr: "EN", en: "TR" }, // buton hep "diğer dile geç" yazar

    // --- Ortak nav linkleri (emoji dahil, tüm sayfalarda tekrarlanan) ---
    nav_home_emoji: { tr: "🏠 Ana Sayfa", en: "🏠 Home" },
    nav_explorer_emoji: { tr: "🔍 Genel Arama", en: "🔍 Explore" },
    nav_lise_skoru_emoji: { tr: "🎓 Lise Skoru", en: "🎓 School Score" },
    nav_tercih_sihirbazi_emoji: { tr: "🧭 Tercih Sihirbazı", en: "🧭 Preference Wizard" },
    nav_edunode_emoji: { tr: "🕸️ EduNode", en: "🕸️ EduNode" },
    nav_favorilerim_emoji: { tr: "★ Favorilerim", en: "★ My Favorites" },
    nav_giris_yap: { tr: "Giriş Yap", en: "Log In" },
    nav_zaten_hesabim_var: { tr: "Zaten hesabım var", en: "I already have an account" },
    nav_giris_sayfasina_don: { tr: "← Giriş sayfasına dön", en: "← Back to login" },
    nav_hesabim_yok: { tr: "Hesabım yok, kayıt ol", en: "No account, sign up" },
    nav_okulunuzu_sahiplenin_cta: { tr: "Okulunuzu Sahiplenin →", en: "Claim Your School →" },
    nav_geri_don: { tr: "← Geri dön", en: "← Go back" },
    nav_genel_aramaya_git: { tr: "Genel Aramaya Git →", en: "Go to Explore →" },
    nav_genel_aramaya: { tr: "Genel aramaya", en: "to explore" },

    // --- Sayfa başlıkları (H1) ---
    h1_edunode: { tr: "🕸️ EduNode — Okulların Kariyer Ağı", en: "🕸️ EduNode — Career Network of Schools" },
    h1_favorilerim: { tr: "★ Favorilerim", en: "★ My Favorites" },
    h1_giris: { tr: "Giriş Yap", en: "Log In" },
    h1_gizlilik: { tr: "Gizlilik Politikası", en: "Privacy Policy" },
    h1_istatistikler: { tr: "📊 Platform İstatistikleri", en: "📊 Platform Statistics" },
    h1_kayit: { tr: "Kayıt Ol", en: "Sign Up" },
    h1_kurum_paneli: { tr: "🏫 Kurum Paneli", en: "🏫 Institution Panel" },
    h1_kurumlar_icin: { tr: "Kurumunuzun Profilini Sahiplenin", en: "Claim Your Institution's Profile" },
    h1_lise_skoru: { tr: "🎓 Lise Skoru Hesaplayıcı", en: "🎓 High School Score Calculator" },
    h1_nasil_calisir: { tr: "EduScor Nasıl Çalışır?", en: "How EduScor Works" },
    h1_tercih_sihirbazi: { tr: "🧭 Lise Tercih Sihirbazı", en: "🧭 High School Preference Wizard" },

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
};

function getLang() {
    return localStorage.getItem("eduscor_lang") || "tr";
}

function setLang(lang) {
    localStorage.setItem("eduscor_lang", lang);
    applyI18n();
    document.documentElement.setAttribute("lang", lang);
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
    document.querySelectorAll("[data-i18n-placeholder]").forEach((el) => {
        el.setAttribute("placeholder", t(el.getAttribute("data-i18n-placeholder")));
    });

    const toggleBtn = document.getElementById("langToggleBtn");
    if (toggleBtn) toggleBtn.textContent = t("lang_toggle_label");
}

document.addEventListener("DOMContentLoaded", applyI18n);
