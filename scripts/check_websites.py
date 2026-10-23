"""Kurumlara kayıtlı web sitelerinin gerçekten o kuruma ait olup olmadığını denetler.

Salt okunur denetim: institutions tablosuna YAZMAZ. Sonuçlar
public.website_dogrulama tablosuna yazılır; düzeltme ayrı bir onaylı adımdır.

Yöntem: sitenin ana sayfası indirilir, <title> ve og:site_name okunur,
okul adındaki ayırt edici sözcüklerle (il/ilçe öneki ve tür sözcükleri hariç)
karşılaştırılır.
- eslesiyor   : ayırt edici sözcüklerin en az %60'ı başlıkta geçiyor ve başlık
                başka bir il adı içermiyor
- eslesmiyor  : hiçbir ayırt edici sözcük geçmiyor ya da başlıkta okulun ili
                dışında bir il adı var (okul adında geçmiyorsa)
- belirsiz    : arada kalanlar, başlıksız sayfalar
- erisilemedi : HTTP hatası / zaman aşımı
Saniyede en fazla 1 istek; açıklayıcı User-Agent.

Ortam değişkenleri: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
"""
import argparse
import html
import json
import os
import re
import sys
import time
from collections import Counter
from datetime import datetime, timezone

import requests

from eduscor_data_utils import normalize_turkish

USER_AGENT = "EduScor-Crawler/1.0 (+destek@eduscor.com; egitim karsilastirma platformu)"
GENEL = {
    "ozel", "okulu", "okul", "lisesi", "lise", "ilkokulu", "ortaokulu", "anaokulu", "anadolu", "mesleki",
    "teknik", "ve", "imam", "hatip", "kolej", "koleji", "fen", "sosyal", "bilimler", "meslek", "egitim",
    "merkezi", "halk", "kiz", "ticaret", "turizm", "saglik", "cok", "programli", "t", "c", "mudurlugu",
    "sehit", "ilk", "orta", "uygulama", "kademe", "i", "ii", "iii", "yil", "ataturk", "cumhuriyet",
}
ILLER = ["adana", "adiyaman", "afyonkarahisar", "agri", "aksaray", "amasya", "ankara", "antalya", "ardahan",
         "artvin", "aydin", "balikesir", "bartin", "batman", "bayburt", "bilecik", "bingol", "bitlis", "bolu",
         "burdur", "bursa", "canakkale", "cankiri", "corum", "denizli", "diyarbakir", "duzce", "edirne",
         "elazig", "erzincan", "erzurum", "eskisehir", "gaziantep", "giresun", "gumushane", "hakkari", "hatay",
         "igdir", "isparta", "istanbul", "izmir", "kahramanmaras", "karabuk", "karaman", "kars", "kastamonu",
         "kayseri", "kilis", "kirikkale", "kirklareli", "kirsehir", "kocaeli", "konya", "kutahya", "malatya",
         "manisa", "mardin", "mersin", "mugla", "mus", "nevsehir", "nigde", "ordu", "osmaniye", "rize",
         "sakarya", "samsun", "sanliurfa", "siirt", "sinop", "sivas", "sirnak", "tekirdag", "tokat", "trabzon",
         "tunceli", "usak", "van", "yalova", "yozgat", "zonguldak"]
TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)
OG_RE = re.compile(r"<meta[^>]+property=[\"']og:site_name[\"'][^>]+content=[\"']([^\"']+)", re.I)


def ascii_tr(s: str) -> str:
    s = normalize_turkish(s or "")
    return s.translate(str.maketrans("çğıöşüâîû", "cgiosuaiu"))


def tokens(s: str) -> list[str]:
    return [w for w in re.split(r"[^a-z0-9]+", ascii_tr(s)) if w]


def fetch_all(base: str, h: dict, path: str, page: int = 1000) -> list[dict]:
    rows, offset = [], 0
    sep = "&" if "?" in path else "?"
    while True:
        r = requests.get(f"{base}{path}{sep}limit={page}&offset={offset}", headers=h, timeout=60)
        r.raise_for_status()
        chunk = r.json()
        rows.extend(chunk)
        if len(chunk) < page:
            return rows
        offset += page


def host_of(url: str) -> str:
    return re.sub(r"^https?://(www\.)?", "", url.strip().lower()).split("/")[0]


def degerlendir(ad: str, il: str | None, ilce: str | None, baslik: str) -> tuple[str, float | None]:
    if not baslik.strip():
        return "belirsiz", None
    cekirdek = re.sub(r"^.* - ", "", ad)
    ad_tok = tokens(cekirdek)
    ayirt = {w for w in ad_tok if w not in GENEL and len(w) > 1}
    b_tok = set(tokens(baslik))
    il_n = ascii_tr(il or "")
    ilce_n = ascii_tr(ilce or "")
    baska_il = [x for x in ILLER if x in b_tok and x != il_n and x != ilce_n and x not in ad_tok]
    if not ayirt:
        ayirt = {w for w in ad_tok if len(w) > 1}
    if not ayirt:
        return "belirsiz", None
    oran = len(ayirt & b_tok) / len(ayirt)
    b_ayirt = {w for w in b_tok if w not in GENEL and len(w) > 1
               and w not in {"meb", "milli", "egitimi", "bakanligi", "gov", "tr", "k12", "anasayfa", "hos", "geldiniz", "web", "sitesi", "resmi"}}
    if baska_il:
        return "eslesmiyor", round(oran, 2)
    ozel_ad, ozel_baslik = "ozel" in ad_tok, "ozel" in b_tok
    if oran >= 0.6:
        # Özel okul ile aynı adlı resmî okul aynı başlığı paylaşabilir; başlık bunu ayırt etmiyorsa karar verme.
        if ozel_ad != ozel_baslik:
            return "belirsiz", round(oran, 2)
        return "eslesiyor", round(oran, 2)
    if oran == 0:
        # Başlık genel bir MEB/şablon başlığıysa (ayırt edici sözcük yok) karar verilmez.
        return ("eslesmiyor", 0.0) if len(b_ayirt) >= 2 else ("belirsiz", 0.0)
    return "belirsiz", round(oran, 2)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--kapsam", choices=["paylasilan", "hepsi"], default="paylasilan",
                    help="paylasilan: birden çok kurumda geçen siteler; hepsi: tüm siteler")
    ap.add_argument("--limit", type=int, default=5000)
    ap.add_argument("--yeniden-gun", type=int, default=30, help="Bu kadar gün içinde denetlenenleri atla")
    args = ap.parse_args()

    base, skey = os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not base or not skey:
        print("HATA: SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY gerekli.")
        return 1
    h = {"apikey": skey, "Authorization": f"Bearer {skey}", "Content-Type": "application/json"}

    locs = {l["id"]: l for l in fetch_all(base, h, "/rest/v1/locations?select=id,parent_id,level,name")}

    def yer(loc_id):
        il = ilce = None
        loc = locs.get(loc_id)
        while loc:
            if loc["level"] == "district" and ilce is None:
                ilce = loc["name"]
            if loc["level"] == "province":
                il = loc["name"]
                break
            loc = locs.get(loc.get("parent_id"))
        return il, ilce

    kurumlar = fetch_all(base, h, "/rest/v1/institutions?select=id,name,website,location_id&website=not.is.null&order=id")
    kurumlar = [k for k in kurumlar if (k.get("website") or "").strip()]
    if args.kapsam == "paylasilan":
        sayac = Counter(host_of(k["website"]) for k in kurumlar)
        kurumlar = [k for k in kurumlar if sayac[host_of(k["website"])] > 1]
    son = datetime.now(timezone.utc).timestamp() - args.yeniden_gun * 86400
    yakin = {r["institution_id"] for r in fetch_all(base, h, "/rest/v1/website_dogrulama?select=institution_id,kontrol_tarihi")
             if datetime.fromisoformat(r["kontrol_tarihi"].replace("Z", "+00:00")).timestamp() > son}
    todo = [k for k in kurumlar if k["id"] not in yakin][: args.limit]
    print(f"Kapsam {args.kapsam}: {len(kurumlar)} kurum; bu çalıştırmada {len(todo)}.")

    s = requests.Session()
    s.headers["User-Agent"] = USER_AGENT
    cache: dict[str, tuple] = {}
    stats = Counter()
    for n, k in enumerate(todo, 1):
        url = k["website"].strip()
        if not url.startswith("http"):
            url = "https://" + url
        host = host_of(url)
        if host in cache:
            kod, son_url, baslik = cache[host]
        else:
            kod, son_url, baslik = None, None, ""
            try:
                r = s.get(url, timeout=20, allow_redirects=True)
                kod, son_url = r.status_code, r.url
                if r.status_code == 200:
                    r.encoding = r.apparent_encoding if not r.encoding or r.encoding.lower() == "iso-8859-1" else r.encoding
                    t = r.text[:200000]
                    parcalar = [html.unescape(m.strip()) for m in TITLE_RE.findall(t)[:1] + OG_RE.findall(t)[:1]]
                    baslik = " | ".join(p for p in parcalar if p)[:500]
            except Exception as e:
                baslik = ""
                kod = None
                print(f"  erişilemedi {host}: {str(e)[:80]}")
            cache[host] = (kod, son_url, baslik)
            time.sleep(1.0)
        if kod is None:
            durum, oran = "erisilemedi", None
        elif kod != 200:
            durum, oran = "erisilemedi", None
        else:
            il, ilce = yer(k.get("location_id"))
            durum, oran = degerlendir(k["name"], il, ilce, baslik)
        stats[durum] += 1
        requests.post(f"{base}/rest/v1/website_dogrulama?on_conflict=institution_id",
                      headers={**h, "Prefer": "resolution=merge-duplicates,return=minimal"},
                      json={"institution_id": k["id"], "url": k["website"], "durum": durum, "sayfa_basligi": baslik or None,
                            "ortusme": oran, "http_kodu": kod, "son_url": son_url,
                            "kontrol_tarihi": datetime.now(timezone.utc).isoformat()},
                      timeout=20).raise_for_status()
        if n % 250 == 0:
            print(f"  {n} işlendi: {dict(stats)}")

    ozet = {**stats, "kapsam": args.kapsam, "islenen": len(todo), "tarih": datetime.now(timezone.utc).isoformat()}
    print("SITE_DOGRULAMA_OZETI " + json.dumps(ozet, ensure_ascii=False))
    requests.post(f"{base}/rest/v1/scrape_progress?on_conflict=key",
                  headers={**h, "Prefer": "resolution=merge-duplicates,return=minimal"},
                  json={"key": "site_dogrulama_son_ozet", "value": json.dumps(ozet, ensure_ascii=False)}, timeout=20)
    return 0


if __name__ == "__main__":
    sys.exit(main())
