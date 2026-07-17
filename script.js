// EduScor — arama sihirbazı dropdown davranışları
document.addEventListener('DOMContentLoaded', function () {

  var dropdowns = document.querySelectorAll('.dropdown');

  function closeAll(except) {
    dropdowns.forEach(function (d) {
      if (d !== except) d.classList.remove('open');
    });
  }

  dropdowns.forEach(function (dropdown) {
    var trigger = dropdown.querySelector('.dropdown-trigger');
    var label = trigger.querySelector('.dt-label');
    var options = dropdown.querySelectorAll('.dropdown-option');

    trigger.addEventListener('click', function (e) {
      e.stopPropagation();
      var isOpen = dropdown.classList.contains('open');
      closeAll();
      if (!isOpen) dropdown.classList.add('open');
    });

    options.forEach(function (opt) {
      opt.addEventListener('click', function () {
        label.textContent = opt.dataset.value;
        dropdown.classList.remove('open');
      });
    });
  });

  // Dışarı tıklanınca tüm dropdown'ları kapat
  document.addEventListener('click', function () {
    closeAll();
  });

  // Ara butonu — basit demo davranışı
  var searchBtn = document.querySelector('.btn-search');
  if (searchBtn) {
    searchBtn.addEventListener('click', function () {
      var konum = document.querySelector('[data-dropdown="konum"] .dt-label').textContent;
      var kategori = document.querySelector('[data-dropdown="kategori"] .dt-label').textContent;
      var yas = document.querySelector('[data-dropdown="yas"] .dt-label').textContent;
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
