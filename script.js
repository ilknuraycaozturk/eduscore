// EduScor — arama sihirbazı: yazılabilir combobox davranışı
document.addEventListener('DOMContentLoaded', function () {

  var dropdowns = document.querySelectorAll('.dropdown');

  function closeAll(except) {
    dropdowns.forEach(function (d) {
      if (d !== except) d.classList.remove('open');
    });
  }

  dropdowns.forEach(function (dropdown) {
    var input = dropdown.querySelector('.dt-input');
    var chevron = dropdown.querySelector('.chev');
    var panel = dropdown.querySelector('.dropdown-panel');
    var options = dropdown.querySelectorAll('.dropdown-option');

    function openPanel() {
      var isOpen = dropdown.classList.contains('open');
      closeAll();
      if (!isOpen) dropdown.classList.add('open');
    }

    // Input'a tıklayınca veya odaklanınca paneli aç
    input.addEventListener('click', function (e) {
      e.stopPropagation();
      closeAll(dropdown);
      dropdown.classList.add('open');
    });
    input.addEventListener('focus', function () {
      closeAll(dropdown);
      dropdown.classList.add('open');
    });

    // Ok ikonuna tıklayınca aç/kapa
    chevron.addEventListener('click', function (e) {
      e.stopPropagation();
      openPanel();
      if (dropdown.classList.contains('open')) input.focus();
    });

    // Yazarken seçenekleri filtrele (kelime bazlı, sıra önemsiz)
    input.addEventListener('input', function () {
      var tokens = input.value.trim().toLocaleLowerCase('tr').split(/\s+/).filter(Boolean);
      options.forEach(function (opt) {
        var text = opt.textContent.trim().toLocaleLowerCase('tr');
        var match = tokens.length === 0 || tokens.every(function (t) {
          return text.indexOf(t) !== -1;
        });
        opt.style.display = match ? '' : 'none';
      });
      if (!dropdown.classList.contains('open')) {
        closeAll(dropdown);
        dropdown.classList.add('open');
      }
    });

    // Seçenek tıklanınca input'a yaz, paneli kapat
    options.forEach(function (opt) {
      opt.addEventListener('click', function () {
        input.value = opt.dataset.value;
        dropdown.classList.remove('open');
      });
    });

    // Panel içine tıklamanın dışarı tıklama sayılmaması için
    panel.addEventListener('click', function (e) {
      e.stopPropagation();
    });
  });

  // Dışarı tıklanınca tüm dropdown'ları kapat ve filtreleri sıfırla
  document.addEventListener('click', function () {
    closeAll();
    dropdowns.forEach(function (dropdown) {
      dropdown.querySelectorAll('.dropdown-option').forEach(function (opt) {
        opt.style.display = '';
      });
    });
  });

  // Ara butonu — basit demo davranışı
  var searchBtn = document.querySelector('.btn-search');
  if (searchBtn) {
    searchBtn.addEventListener('click', function () {
      var konum = document.querySelector('[data-dropdown="konum"] .dt-input').value;
      var kategori = document.querySelector('[data-dropdown="kategori"] .dt-input').value;
      var yas = document.querySelector('[data-dropdown="yas"] .dt-input').value;
      console.log('Arama yapılıyor:', { konum: konum, kategori: kategori, yas: yas });
      // TODO: gerçek arama/yönlendirme mantığı burada devreye girecek
    });
  }

  // AI ile Yardım Al — basit demo davranışı
  var aiBtn = document.querySelector('.btn-ai');
  if (aiBtn) {
    aiBtn.addEventListener('click', function () {
      console.log('AI destekli öneri akışı başlatıldı');
      // TODO: AI öneri modalı / yönlendirmesi burada devreye girecek
    });
  }

  // Dil değiştirici (EN / TR) — basit toggle placeholder
  var langSwitch = document.getElementById('langSwitch');
  if (langSwitch) {
    var spans = langSwitch.querySelectorAll('span');
    langSwitch.addEventListener('click', function () {
      spans.forEach(function (s) { s.classList.toggle('lang-active'); });
      var current = langSwitch.querySelector('.lang-active').textContent.trim();
      console.log('Dil değiştirildi:', current);
      // TODO: gerçek i18n / dil değiştirme mantığı burada devreye girecek
    });
  }

});
