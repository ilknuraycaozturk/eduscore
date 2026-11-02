// Canlı sitede "Yakınımda Ara" ve kademe filtresini dener; sonucu Supabase'e yazar.
const { chromium } = require('playwright');
const SENARYO = [
  { ad: 'istanbul_ilkokul_5km', q: 'category=okul-oncesi-k12&kademe=ilkokul&lat=41.0082&lng=28.9784&radius=5' },
  { ad: 'ankara_lise_10km', q: 'category=okul-oncesi-k12&kademe=lise&lat=39.9208&lng=32.8541&radius=10' },
  { ad: 'izmir_anaokulu_sinirsiz', q: 'category=okul-oncesi-k12&kademe=anaokulu&lat=38.4237&lng=27.1428' },
];
(async () => {
  const browser = await chromium.launch();
  const sonuc = {};
  for (const s of SENARYO) {
    const page = await browser.newPage();
    await page.goto('https://eduscor.com/explorer.html?' + s.q, { waitUntil: 'networkidle', timeout: 60000 });
    await page.waitForTimeout(4000);
    sonuc[s.ad] = await page.evaluate(() => ({
      baslik: (document.getElementById('resultsTitle') || {}).innerText || null,
      kartlar: Array.from(document.querySelectorAll('h3, h2')).map(e => e.innerText.trim()).filter(t => / - |ÖZEL|Özel/.test(t)).slice(0, 8),
    }));
    await page.close();
  }
  await browser.close();
  const r = await fetch(process.env.SUPABASE_URL + '/rest/v1/scrape_progress?on_conflict=key', {
    method: 'POST', headers: { apikey: process.env.SUPABASE_SERVICE_ROLE_KEY, Authorization: 'Bearer ' + process.env.SUPABASE_SERVICE_ROLE_KEY,
      'Content-Type': 'application/json', Prefer: 'resolution=merge-duplicates,return=minimal' },
    body: JSON.stringify({ key: 'site_test_yakinimda', value: JSON.stringify(sonuc) }) });
  console.log(r.status, JSON.stringify(sonuc, null, 1));
})();
