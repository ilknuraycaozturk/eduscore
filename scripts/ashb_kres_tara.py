"""Aile ve Sosyal Hizmetler Bakanlığı il müdürlüklerinin sitelerindeki özel kreş /
gündüz bakımevi listelerini bulur ve ARA tablolara yazar (ashb_kres_sayfalari, ashb_kres_ham).
Okul kayıtlarına (institutions) hiçbir şey yazmaz.

Akış: her il için https://www.aile.gov.tr/{il}/ ana sayfasındaki bağlantılardan
kreş/gündüz bakımevi/özel kuruluş sayfaları seçilir; robots.txt'e uyulur; saniyede en fazla
1 istek. Sayfadaki tablolardan kurum satırları ayrıştırılır, ham hücreler de saklanır.
Her çalıştırma önce bu iki tabloyu boşaltır (salt ölçüm).

Ortam: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
"""
import json
import os
import re
import sys
import time
import unicodedata
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup

KOK = "https://www.aile.gov.tr"
UA = "EduScor-Crawler/1.0 (+destek@eduscor.com; egitim karsilastirma platformu)"
ILLER = ["Adana", "Adıyaman", "Afyonkarahisar", "Ağrı", "Amasya", "Ankara", "Antalya", "Artvin", "Aydın",
         "Balıkesir", "Bilecik", "Bingöl", "Bitlis", "Bolu", "Burdur", "Bursa", "Çanakkale", "Çankırı", "Çorum",
         "Denizli", "Diyarbakır", "Edirne", "Elazığ", "Erzincan", "Erzurum", "Eskişehir", "Gaziantep", "Giresun",
         "Gümüşhane", "Hakkari", "Hatay", "Isparta", "Mersin", "İstanbul", "İzmir", "Kars", "Kastamonu", "Kayseri",
         "Kırklareli", "Kırşehir", "Kocaeli", "Konya", "Kütahya", "Malatya", "Manisa", "Kahramanmaraş", "Mardin",
         "Muğla", "Muş", "Nevşehir", "Niğde", "Ordu", "Rize", "Sakarya", "Samsun", "Siirt", "Sinop", "Sivas",
         "Tekirdağ", "Tokat", "Trabzon", "Tunceli", "Şanlıurfa", "Uşak", "Van", "Yozgat", "Zonguldak", "Aksaray",
         "Bayburt", "Karaman", "Kırıkkale", "Batman", "Şırnak", "Bartın", "Ardahan", "Iğdır", "Yalova", "Karabük",
         "Kilis", "Osmaniye", "Düzce"]
SABIT_KALIPLAR = ["kuruluslarimiz/ozel-kresler/", "ozel-kuruluslar/ozel-kres-gunduz-bakimevleri/",
                  "kuruluslarimiz/ozelkuruluslar/ozelkresvebakim/", "kresler/",
                  "kuruluslarimiz/ozel-kuruluslarimiz/ozel-kres-gunduz-bakimevi-ve-cocuk-kulupleri/",
                  "kuruluslarimiz/ozel-kuruluslar/", "kuruluslarimiz/ozel-kuruluslarimiz/"]
ADAY_RE = re.compile(r"kres|gunduz|bakimev|ozel-?kurulus|ozelkres|cocuk-?kulub", re.I)
KURUM_RE = re.compile(r"kreş|kres|gündüz|bakımev|bakimev|çocuk kulüb|cocuk kulub|kulübü", re.I)
TEL_RE = re.compile(r"^[\d\s()+\-/.]{7,}$|^\+?9?0?\s*\(?\d{3}\)?[\s\d]{7,}")
ADRES_RE = re.compile(r"\b(mah|mh|cad|cd|sok|sk|bulv|no\s*:|no:|blv)\b", re.I)
GUNCEL_RE = re.compile(r"(son\s+g[üu]ncelleme[^0-9]{0,30}\d{1,2}[./]\d{1,2}[./]\d{2,4})", re.I)


def slug(il: str) -> str:
    s = il.replace("ı", "i").replace("İ", "I")
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z]", "", s)


def tur_of(ad: str) -> str:
    a = ad.lower()
    if "kulüb" in a or "kulub" in a:
        return "cocuk_kulubu" if not re.search(r"kreş|kres|gündüz|bakımev", a) else "karma"
    if re.search(r"kreş|kres", a) and re.search(r"gündüz|bakımev", a):
        return "kres_ve_gunduz_bakimevi"
    if re.search(r"kreş|kres", a):
        return "kres"
    if re.search(r"gündüz|bakımev|bakimev", a):
        return "gunduz_bakimevi"
    return "belirsiz"


def satir_ayir(hucreler: list[str]) -> dict:
    kalan = [c for c in hucreler if c and not re.fullmatch(r"\d{1,4}\.?", c)]  # sıra no
    ad = next((c for c in kalan if KURUM_RE.search(c)), None)
    tel = next((c for c in kalan if c != ad and TEL_RE.search(c) and sum(ch.isdigit() for ch in c) >= 7), None)
    adres_ad = [c for c in kalan if c not in (ad, tel)]
    adres = max((c for c in adres_ad if ADRES_RE.search(c)), key=len, default=None)
    ilce = next((c for c in adres_ad if c != adres and len(c) <= 25 and not any(ch.isdigit() for ch in c)
                 and c.upper() not in {x.upper() for x in ILLER}), None)
    return {"ad": ad, "telefon": tel, "adres": adres, "ilce": ilce}


def main() -> int:
    base, key = os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    h = {"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    for t in ("ashb_kres_ham", "ashb_kres_sayfalari"):
        requests.delete(f"{base}/rest/v1/{t}?il=not.is.null", headers=h, timeout=60).raise_for_status()

    s = requests.Session()
    s.headers["User-Agent"] = UA
    rp = RobotFileParser()
    try:
        r = s.get(KOK + "/robots.txt", timeout=20)
        rp.parse(r.text.splitlines() if r.status_code == 200 else [])
    except Exception:
        rp.parse([])

    def al(url):
        if not rp.can_fetch(UA, url):
            return None, "robots_izin_yok"
        time.sleep(1.0)
        try:
            r = s.get(url, timeout=30)
            return (r.text if r.status_code == 200 else None), f"http_{r.status_code}"
        except Exception as e:
            return None, f"hata:{str(e)[:60]}"

    ozet = {"il": 0, "sayfa_bulunan_il": 0, "satir": 0}
    for il in ILLER:
        ozet["il"] += 1
        sl = slug(il)
        ana, d = al(f"{KOK}/{sl}/")
        sayfalar = []
        if ana:
            soup = BeautifulSoup(ana, "html.parser")
            linkler = set()
            for a in soup.find_all("a", href=True):
                u = urljoin(f"{KOK}/{sl}/", a["href"]).split("#")[0]
                p = urlparse(u)
                if p.netloc.endswith("aile.gov.tr") and p.path.startswith(f"/{sl}/") and \
                        (ADAY_RE.search(p.path) or KURUM_RE.search(a.get_text(" ", strip=True))):
                    linkler.add(u)
            # Menü bağlantıları ana sayfada her zaman yok: "kuruluşlarımız" sayfalarını da gez ve
            # il sitelerinde görülen sabit adres kalıplarını dene.
            for alt in ("kuruluslarimiz/", "kuruluslarimiz/ozel-kuruluslar/", "kuruluslarimiz/ozel-kuruluslarimiz/",
                        "kuruluslarimiz/ozelkuruluslar/", "ozel-kuruluslar/"):
                h2, _ = al(f"{KOK}/{sl}/{alt}")
                if not h2:
                    continue
                for a in BeautifulSoup(h2, "html.parser").find_all("a", href=True):
                    u = urljoin(f"{KOK}/{sl}/{alt}", a["href"]).split("#")[0]
                    p = urlparse(u)
                    if p.netloc.endswith("aile.gov.tr") and p.path.startswith(f"/{sl}/") and \
                            (ADAY_RE.search(p.path) or KURUM_RE.search(a.get_text(" ", strip=True))):
                        linkler.add(u)
            for kalip in SABIT_KALIPLAR:
                linkler.add(f"{KOK}/{sl}/{kalip}")
            linkler = {u.replace("http://", "https://").rstrip("/") + "/" for u in linkler
                       if not re.search(r"/(haberler|duyurular|galeri|etkinlikler)/", u)}
            sayfalar = sorted(linkler)[:15]
        else:
            requests.post(f"{base}/rest/v1/ashb_kres_sayfalari", headers=h, timeout=30,
                          json={"il": il, "url": f"{KOK}/{sl}/", "durum": f"ana_sayfa_{d}"}).raise_for_status()
            continue
        if not sayfalar:
            requests.post(f"{base}/rest/v1/ashb_kres_sayfalari", headers=h, timeout=30,
                          json={"il": il, "url": f"{KOK}/{sl}/", "durum": "aday_bag_yok"}).raise_for_status()
            continue
        il_satir = 0
        for u in sayfalar:
            html, d = al(u)
            if not html and d == "http_404":
                continue
            if not html:
                requests.post(f"{base}/rest/v1/ashb_kres_sayfalari", headers=h, timeout=30,
                              json={"il": il, "url": u, "durum": d}).raise_for_status()
                continue
            soup = BeautifulSoup(html, "html.parser")
            metin = soup.get_text(" ", strip=True)
            gm = GUNCEL_RE.search(metin)
            baslik = (soup.title.get_text(strip=True) if soup.title else "")[:200]
            satirlar = []
            for tr in soup.find_all("tr"):
                hucre = [c.get_text(" ", strip=True) for c in tr.find_all(["td", "th"])]
                if len(hucre) >= 2 and any(KURUM_RE.search(c) for c in hucre):
                    satirlar.append(hucre)
            kayitlar = []
            for n, hc in enumerate(satirlar, 1):
                a = satir_ayir(hc)
                if not a["ad"] or re.fullmatch(r"(kuruluş|kurum|kreş)\s*ad[ıi]?", a["ad"], re.I):
                    continue
                kayitlar.append({"il": il, "url": u, "satir_no": n, **a, "tur": tur_of(a["ad"]), "hucreler": hc})
            if kayitlar:
                requests.post(f"{base}/rest/v1/ashb_kres_ham", headers=h, json=kayitlar, timeout=60).raise_for_status()
            il_satir += len(kayitlar)
            requests.post(f"{base}/rest/v1/ashb_kres_sayfalari", headers=h, timeout=30,
                          json={"il": il, "url": u, "durum": "tablo" if kayitlar else "tablo_yok",
                                "satir_sayisi": len(kayitlar), "guncelleme_metni": gm.group(1) if gm else None,
                                "baslik": baslik}).raise_for_status()
        ozet["satir"] += il_satir
        if il_satir:
            ozet["sayfa_bulunan_il"] += 1
        print(f"{il}: {len(sayfalar)} aday sayfa, {il_satir} satır")
    print("ASHB_OZET " + json.dumps(ozet, ensure_ascii=False))
    requests.post(f"{base}/rest/v1/scrape_progress?on_conflict=key",
                  headers={**h, "Prefer": "resolution=merge-duplicates,return=minimal"},
                  json={"key": "ashb_kres_son_ozet", "value": json.dumps(ozet)}, timeout=20)
    return 0


if __name__ == "__main__":
    sys.exit(main())
