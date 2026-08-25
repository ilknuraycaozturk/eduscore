// assets/footer.js — loads the unified footer into pages by replacing any existing <footer> element
(function(){
  function insertFooter(html){
    try{
      const parser = new DOMParser();
      const doc = parser.parseFromString(html, 'text/html');
      const footerEl = doc.querySelector('footer');
      if(!footerEl) return;

      // Replace all existing footer elements with the unified footer
      const existingFooters = document.querySelectorAll('footer');
      if(existingFooters.length){
        existingFooters.forEach(f => f.replaceWith(footerEl.cloneNode(true)));
      } else {
        // append at end of body
        document.body.appendChild(footerEl.cloneNode(true));
      }

      // Ensure the page-shortcut link points to current path
      const shortcut = document.getElementById('page-shortcut');
      if(shortcut) shortcut.setAttribute('href', window.location.pathname || '/');

      // Wire up footer-lang-btn to existing toggleLang if available
      const fl = document.getElementById('footer-lang-btn');
      if(fl && typeof window.toggleLang === 'function'){
        fl.addEventListener('click', function(e){ e.preventDefault(); window.toggleLang(); });
      }

    }catch(e){ console.error('footer inject error', e); }
  }

  function loadAndInsert(){
    // If footer already injected by previous run, quit
    if(window.__eduscor_footer_injected) return; window.__eduscor_footer_injected = true;

    // Add stylesheet to head if missing
    const cssHref = '/assets/footer.css';
    if(!document.querySelector('link[href="'+cssHref+'"]')){
      const l = document.createElement('link'); l.rel = 'stylesheet'; l.href = cssHref; document.head.appendChild(l);
    }

    fetch('/assets/footer.html', {cache: 'no-cache'}).then(r=>r.text()).then(html=>insertFooter(html)).catch(err=>{
      // As a fallback create a very small footer
      const fallback = `<footer style="width:100%;border-top:1px solid #F3EFEA;padding:16px;text-align:center;color:#8A7A72;font-size:13px">© 2026 EduScor · <a href="/gizlilik-politikasi.html">Gizlilik Politikası</a></footer>`;
      insertFooter(fallback);
      console.error('Could not load unified footer:', err);
    });
  }

  if(document.readyState === 'loading') document.addEventListener('DOMContentLoaded', loadAndInsert); else loadAndInsert();
})();
