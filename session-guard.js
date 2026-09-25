// ===== EduScor B2B Oturum Güvenliği =====
// school_admin rolündeki kullanıcılar için 60 dakika inaktivite sonrası
// otomatik oturum kapatma. Diğer roller (parent_student, alumni, giriş
// yapmamış ziyaretçiler) için bu mekanizma devreye girmez - performans/UX
// açısından zararsızdır.
(function () {
    const INAKTIVITE_LIMIT_MS = 60 * 60 * 1000; // 60 dakika
    let timer = null;
    let sbGuardClient = null;

    function resetTimer() {
        if (timer) clearTimeout(timer);
        timer = setTimeout(handleTimeout, INAKTIVITE_LIMIT_MS);
    }

    async function handleTimeout() {
        if (!sbGuardClient) return;
        await sbGuardClient.auth.signOut();
        alert('Güvenlik nedeniyle 60 dakika işlem yapılmadığı için oturumunuz sonlandırıldı. Lütfen tekrar giriş yapın.');
        window.location.href = 'giris.html';
    }

    // Giriş yapmış kullanıcı için header'daki "Giriş Yap" bağlantısını
    // "Çıkış Yap"a çevirir. Header'lar statik HTML olduğu için (12 sayfada
    // data-i18n="nav_login"), tek merkezi yerde burada yapılıyor.
    // data-i18n etiketi de değiştiriliyor ki i18n.js dil değişiminde metni
    // tekrar "Giriş Yap"a çevirmesin.
    function showLogoutLink() {
        const links = document.querySelectorAll('a[data-i18n="nav_login"]');
        if (!links.length) return;
        let label = 'Çıkış Yap';
        if (typeof t === 'function') {
            const translated = t('nav_logout');
            // Önbellekteki eski i18n.js anahtarı bilmiyorsa anahtarın kendisini döndürür
            if (translated && translated !== 'nav_logout') label = translated;
        }
        links.forEach((a) => {
            a.setAttribute('data-i18n', 'nav_logout');
            a.textContent = label;
            a.setAttribute('href', '#');
            a.addEventListener('click', async (e) => {
                e.preventDefault();
                // Aynı proje için tüm client'lar aynı oturum kaydını paylaşır,
                // bu yüzden buradaki signOut sayfanın kendi client'ını da kapatır.
                await sbGuardClient.auth.signOut();
                window.location.href = 'index.html';
            });
        });
    }

    async function init() {
        if (typeof supabase === 'undefined') return;
        // ÖNEMLİ: Her sayfa kendi Supabase client'ını ayrı bir değişkende
        // oluşturuyor (genelde 'sb'), bu script ise BAĞIMSIZ, salt-okunur
        // bir client kullanır - sayfa scriptleriyle çakışmaz.
        sbGuardClient = supabase.createClient(
            "https://piyxmmzteyygwlurdawi.supabase.co",
            "sb_publishable_6WIxgR9-dgumpgAFgZtn5A_iuBG8llL"
        );

        const { data: { session } } = await sbGuardClient.auth.getSession();
        if (!session) return; // giriş yapmamış ziyaretçi - mekanizma gerekmiyor

        showLogoutLink(); // her rol için (profil/rol kontrolünden ÖNCE)

        const { data: profile } = await sbGuardClient
            .from('profiles').select('role').eq('id', session.user.id).maybeSingle();

        if (!profile) {
            // ÖNEMLİ: Profil hiç yoksa (özellikle Google OAuth ile ilk kez giriş
            // yapan kullanıcılarda oluşan boşluk - giris.html'deki email/password
            // akışı kendi profilini oluşturuyordu, ama OAuth akışı doğrudan
            // index.html'e yönlendirdiği için o kontrol hiç çalışmıyordu) burada
            // oluşturuyoruz. user_metadata alan adları provider'a göre değişebildiği
            // için (full_name/name, avatar_url/picture) ikisi de deneniyor.
            const meta = session.user.user_metadata || {};
            await sbGuardClient.from('profiles').insert({
                id: session.user.id,
                full_name: meta.full_name || meta.name || null,
                avatar_url: meta.avatar_url || meta.picture || null,
            });
            return; // yeni kullanıcı varsayılan rolde (parent_student) - B2B takibi gerekmiyor
        }

        if (profile.role !== 'school_admin') return; // sadece B2B (kurum yöneticisi)

        ['mousemove', 'keydown', 'click', 'scroll', 'touchstart'].forEach(evt => {
            document.addEventListener(evt, resetTimer, { passive: true });
        });
        resetTimer();
    }

    document.addEventListener('DOMContentLoaded', init);
})();
