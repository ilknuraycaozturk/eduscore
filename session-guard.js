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

        const { data: profile } = await sbGuardClient
            .from('profiles').select('role').eq('id', session.user.id).maybeSingle();
        if (!profile || profile.role !== 'school_admin') return; // sadece B2B (kurum yöneticisi)

        ['mousemove', 'keydown', 'click', 'scroll', 'touchstart'].forEach(evt => {
            document.addEventListener(evt, resetTimer, { passive: true });
        });
        resetTimer();
    }

    document.addEventListener('DOMContentLoaded', init);
})();
