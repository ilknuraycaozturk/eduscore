"""
load_tabanpuan_to_supabase.py
================================
EduScor — scrape_tabanpuanlari.py çıktısını (tabanpuanlari.net'ten çekilen
il bazlı LGS taban puanı / kontenjan verisi) Supabase'e yükler.

ÖNEMLİ: Bu script SADECE MEVCUT kurumları günceller, yeni kurum EKLEMEZ.
Kurumlar zaten MEB taramasından/2022 LGS yüklemesinden veritabanında olmalı.
Eşleşme bulunamayan okullar atlanır ve raporlanır (elle incelenebilir).

Mantık:
1. Aynı okul birden fazla program için ayrı satırlarda gelir -> okul adına
   göre gruplanıp yüzdelik dilim ortalaması alınır, en yüksek 2026 kontenjanı
   toplanır.
2. Okul, mevcut institutions tablosunda aranır (isim + Türkçe İ/i düzeltmeli
   karşılaştırma). Bulunamazsa atlanır (dry-run'da raporlanır).
3. institutions.kontenjan_bilgisi alanı güncellenir.
4. institution_criteria_scores.akademik_basari güncellenir
   (skor = 100 - ortalama_yüzdelik_dilim).
5. institution_criteria_scores.yabanci_dil güncellenir (5 yıllık program
   = hazırlık sınıfı var = yoğunlaştırılmış yabancı dil eğitimi sinyali).

Kullanım:
    export SUPABASE_URL="..."
    export SUPABASE_SERVICE_ROLE_KEY="..."
    python load_tabanpuan_to_supabase.py --input data/tabanpuan_raw.json --dry-run
"""

import argparse
import re
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

import requests


TYPE_KEYWORDS = [
    # ÖNEMLİ: Sıralama önemli - daha spesifik olanlar önce gelmeli.
    ("fen-lisesi", ["fen lisesi"]),
    ("sosyal-bilimler-lisesi", ["sosyal bilimler lisesi"]),
    ("anadolu-imam-hatip-lisesi", ["imam hatip lisesi", "imam-hatip lisesi"]),
    ("mesleki-teknik-anadolu-lisesi", [
        "mesleki ve teknik anadolu lisesi", "ticaret mesleki",
        "teknik anadolu lisesi", "meslek lisesi",
    ]),
    ("anadolu-lisesi", ["anadolu lisesi"]),
    ("lise", ["lisesi", " lise "]),
]


def turkish_lower(s: str) -> str:
    return s.replace("İ", "i").replace("I", "ı").lower()


from eduscor_data_utils import normalize_name  # EDU-DATA-001 - bu script içinde çağrılmıyor (ölü kod temizlendi), sadece tutarlılık için import edildi


def normalize_name_lenient(name: str) -> str:
    """normalize_name gibi ama İ/I ayrımını YOK SAYAR (ikisini de 'i' yapar).
    tabanpuanlari.net kaynağında bazı kelimeler yanlış büyük/küçük harfle
    geliyor (örn. 'İleri' yerine 'Ileri') - bu, standart Türkçe karşılaştırmayı
    bozuyor. Eşleştirme (matching) İÇİN, bu daha toleranslı versiyonu kullanıyoruz."""
    n = name.strip().replace("İ", "i").replace("I", "i").lower()
    n = n.replace("özel", "").strip()
    return " ".join(n.split())


def guess_type(name: str) -> str:
    lower = turkish_lower(name)
    for slug, keywords in TYPE_KEYWORDS:
        if any(k in lower for k in keywords):
            return slug
    return "lise"  # bu script sadece LGS liste sayfasından geliyor, hepsi lise türevi


ALAN_SOZCUKLERI = {"kiz", "ticaret", "turizm", "tarim", "saglik", "denizcilik", "ve", "erkek"}


def ad_sozcukleri(name: str) -> list[str]:
    """'İL - İLÇE - Ad' / 'İL - Ad' önekini atar, Türkçe harfleri sadeleştirir. 'Özel' sözcüğü
    KORUNUR: özel okul aynı adlı resmî okulla eşleşmemeli."""
    parts = [p.strip() for p in name.split(" - ")]
    core = parts[-1] if len(parts) >= 2 else name
    n = core.replace("İ", "i").replace("I", "i").lower().translate(str.maketrans("çğıöşüâîû", "cgiosuaiu"))
    return [w for w in re.split(r"[^a-z0-9]+", n.replace(".", " ")) if w]


def find_existing_match(new_name: str, existing: list[dict]) -> tuple[dict | None, str]:
    """30.10.2026: Eski kural (alt dize, ilk bulunan) "Atatürk Anadolu Lisesi"ni aynı ildeki
    "Kepez Atatürk Anadolu Lisesi"ne bağlayabiliyordu; kayıt adları "İL - İLÇE - Ad" biçimine
    geçince birebir eşleşme hiç tutmuyordu. Yeni kural (aynı il içinde):
    1) adı (önek hariç) birebir aynı tek kurum; 2) yoksa adı yalnızca alan sözcüğüyle
    (Kız, Ticaret, Turizm...) ayrılan tek kurum. Birden çok aday varsa (aynı il, farklı
    ilçede aynı ad; kaynakta ilçe yok) eşleştirme YAPILMAZ."""
    hedef = ad_sozcukleri(new_name)
    tam = [r for r in existing if ad_sozcukleri(r["name"]) == hedef]
    if len(tam) == 1:
        return tam[0], "tam"
    if len(tam) > 1:
        return None, "belirsiz_ayni_ad"
    hs = set(hedef)
    yakin = [r for r in existing
             if not (hs - set(ad_sozcukleri(r["name"]))) and (set(ad_sozcukleri(r["name"])) - hs) <= ALAN_SOZCUKLERI]
    if len(yakin) == 1:
        return yakin[0], "alan_sozcugu"
    return None, ("belirsiz_yakin" if yakin else "bulunamadi")


def get_lookup(base_url: str, headers: dict, table: str, key_field: str = "slug") -> dict[str, str]:
    resp = requests.get(f"{base_url}/rest/v1/{table}?select=id,{key_field}", headers=headers)
    resp.raise_for_status()
    return {r[key_field]: r["id"] for r in resp.json()}


def fetch_all_paginated(base_url: str, headers: dict, path_with_query: str, page_size: int = 1000) -> list[dict]:
    all_rows: list[dict] = []
    offset = 0
    sep = "&" if "?" in path_with_query else "?"
    while True:
        resp = requests.get(
            f"{base_url}{path_with_query}{sep}limit={page_size}&offset={offset}",
            headers=headers,
        )
        resp.raise_for_status()
        page = resp.json()
        all_rows.extend(page)
        if len(page) < page_size:
            break
        offset += page_size
    return all_rows


def main():
    parser = argparse.ArgumentParser(description="tabanpuanlari.net verisini Supabase'e yükler (mevcut kurumları günceller, eşleşmeyenleri yeni ekler).")
    parser.add_argument("--input", required=True)
    parser.add_argument("--category-slug", default="okul-oncesi-k12")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--denetim", action="store_true",
                        help="Yazmadan: yeni kuralla eşleşmeyi, veritabanında bu okulun puanını şu an taşıyan kurumla karşılaştırır ve lgs_eslesme_denetimi tablosuna yazar")
    parser.add_argument("--yeni-kurum-ekle", action="store_true",
                        help="Eşleşmeyen okulu yeni kurum olarak ekle (varsayılan: ekleme, yalnızca raporla - MEB listesi artık tam)")
    args = parser.parse_args()

    supabase_url = os.environ.get("SUPABASE_URL")
    service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not args.dry_run and (not supabase_url or not service_key):
        print("HATA: SUPABASE_URL ve SUPABASE_SERVICE_ROLE_KEY gerekli.")
        sys.exit(1)

    raw = json.loads(Path(args.input).read_text(encoding="utf-8"))
    print(f"{len(raw)} ham program satırı okundu.")

    # ÖNEMLİ: (il, okul_adi) ikilisine göre grupla - sadece okul_adi'na göre
    # gruplamak, farklı illerdeki aynı isimli okulları (örn. "Atatürk Anadolu
    # Lisesi" onlarca ilde var) yanlışlıkla birleştirirdi.
    grouped: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for r in raw:
        grouped[(r.get("il_adi", "Ankara"), r["okul_adi"])].append(r)

    schools = []
    for (il_adi, name), rows in grouped.items():
        yuzdelikler = [r["yuzdelik_2026"] if r.get("yuzdelik_2026") is not None else r.get("yuzdelik_2025")
                       for r in rows]
        yuzdelikler = [y for y in yuzdelikler if y is not None]
        puanlar = [r["lgs_puani_2026"] if r.get("lgs_puani_2026") is not None else r.get("lgs_puani_2025")
                   for r in rows]
        puanlar = [p for p in puanlar if p is not None]
        avg_puan = round(sum(puanlar) / len(puanlar), 2) if puanlar else None
        veri_yili = "2026" if any(r.get("yuzdelik_2026") is not None for r in rows) else "2025"
        avg_yuzdelik = round(sum(yuzdelikler) / len(yuzdelikler), 2) if yuzdelikler else None
        toplam_kontenjan_2026 = sum(r["kontenjan_2026"] for r in rows if r["kontenjan_2026"])
        toplam_kontenjan_2025 = sum(r["kontenjan_2025"] for r in rows if r["kontenjan_2025"])
        hazirlik_var = any((r.get("sure") or "").strip() == "5 yıl" for r in rows)
        schools.append({
            "name": name,
            "il_adi": il_adi,
            "avg_yuzdelik": avg_yuzdelik,
            "avg_puan": avg_puan,
            "veri_yili": veri_yili,
            "kontenjan_2026": toplam_kontenjan_2026 or None,
            "kontenjan_2025": toplam_kontenjan_2025 or None,
            "hazirlik_var": hazirlik_var,
            "program_count": len(rows),
        })

    print(f"{len(schools)} benzersiz okul (program bazında gruplanmış).")

    if args.dry_run:
        print("--- İlk 5 örnek ---")
        print(json.dumps(schools[:5], ensure_ascii=False, indent=2))
        print("... (dry-run, Supabase'e yazılmadı)")
        return

    headers = {
        "apikey": service_key,
        "Authorization": f"Bearer {service_key}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }

    criteria_lookup = get_lookup(supabase_url, headers, "scoring_criteria", "key")
    type_lookup = get_lookup(supabase_url, headers, "institution_types", "slug")
    category_lookup = get_lookup(supabase_url, headers, "categories", "slug")

    # Tüm il konumlarını çek (yeni kurum eklerken hangi ile bağlanacağını
    # bulmak için). İlçe bilgisi bu kaynakta yok, bu yüzden yeni kurumlar
    # İL DÜZEYİNDE konumlandırılıyor.
    all_locations = fetch_all_paginated(supabase_url, headers, "/rest/v1/locations?select=id,name,parent_id,level")
    location_by_id = {l["id"]: l for l in all_locations}
    # Basitleştirilmiş: parent'ı 'Türkiye' olan satırlar il'dir
    turkiye_id = next((l["id"] for l in all_locations if l["name"] == "Türkiye"), None)
    province_id_by_name = {l["name"]: l["id"] for l in all_locations if l.get("parent_id") == turkiye_id}

    def province_of_institution(inst: dict) -> str | None:
        # Mahalle düzeyine bağlı kayıtlar için de ile kadar yukarı çıkılır (önceden ilçe adı dönüyordu).
        loc = location_by_id.get(inst.get("location_id"))
        while loc:
            if loc.get("level") == "province" or loc.get("parent_id") == turkiye_id:
                return loc["name"]
            loc = location_by_id.get(loc.get("parent_id"))
        return None

    all_institutions = fetch_all_paginated(supabase_url, headers, "/rest/v1/institutions?select=id,name,location_id")
    print(f"Eşleştirme için {len(all_institutions)} mevcut kurum yüklendi.")
    for inst in all_institutions:
        inst["_province"] = province_of_institution(inst)

    def write_scores_and_kontenjan(institution_id: str, school: dict):
        kontenjan_parts = []
        if school["kontenjan_2026"]:
            kontenjan_parts.append(f"2026: {school['kontenjan_2026']}")
        if school["kontenjan_2025"]:
            kontenjan_parts.append(f"2025: {school['kontenjan_2025']}")
        kontenjan_bilgisi = ", ".join(kontenjan_parts) if kontenjan_parts else None

        if kontenjan_bilgisi:
            resp = requests.patch(
                f"{supabase_url}/rest/v1/institutions?id=eq.{institution_id}",
                headers=headers, json={"kontenjan_bilgisi": kontenjan_bilgisi},
            )
            if resp.status_code not in (200, 204):
                print(f"UYARI: '{school['name']}' kontenjan bilgisi yazılamadı -> {resp.status_code} {resp.text[:200]}")

        if school["avg_yuzdelik"] is not None:
            academic_score = round(100 - school["avg_yuzdelik"], 2)
            puan_kismi = f"Ortalama taban puanı ({school['avg_puan']}) ve " if school.get("avg_puan") is not None else ""
            source_note = (
                f"Kaynak: tabanpuanlari.net (MEB resmi LGS yerleştirme verilerinden derlenmiştir, {school['veri_yili']} verisi). "
                f"{school['program_count']} programın {puan_kismi}ortalama yüzdelik dilimi ({school['avg_yuzdelik']}) "
                f"üzerinden hesaplanmıştır (skor = 100 - yüzdelik dilim)."
            )
            resp = requests.post(
                f"{supabase_url}/rest/v1/institution_criteria_scores?on_conflict=institution_id,criteria_id",
                headers={**headers, "Prefer": "resolution=merge-duplicates"},
                json={
                    "institution_id": institution_id,
                    "criteria_id": criteria_lookup.get("akademik_basari"),
                    "score": academic_score,
                    "source_note": source_note,
                    "is_verified": False,
                },
            )
            if resp.status_code not in (200, 201, 204):
                print(f"UYARI: '{school['name']}' akademik başarı skoru yazılamadı -> {resp.status_code} {resp.text[:200]}")

        yabanci_dil_score = 100 if school["hazirlik_var"] else 40
        yabanci_dil_note = (
            "Kaynak: tabanpuanlari.net. "
            + ("Programın süresi 5 yıl (hazırlık sınıfı dahil, yoğunlaştırılmış yabancı dil eğitimi)."
               if school["hazirlik_var"] else
               "Programın süresi 4 yıl (hazırlık sınıfı yok, standart müfredat yabancı dil dersi).")
        )
        resp2 = requests.post(
            f"{supabase_url}/rest/v1/institution_criteria_scores?on_conflict=institution_id,criteria_id",
            headers={**headers, "Prefer": "resolution=merge-duplicates"},
            json={
                "institution_id": institution_id,
                "criteria_id": criteria_lookup.get("yabanci_dil"),
                "score": yabanci_dil_score,
                "source_note": yabanci_dil_note,
                "is_verified": False,
            },
        )
        if resp2.status_code not in (200, 201, 204):
            print(f"UYARI: '{school['name']}' yabancı dil skoru yazılamadı -> {resp2.status_code} {resp2.text[:200]}")

    updated, inserted, skipped = 0, 0, []
    sayac = defaultdict(int)
    by_province = defaultdict(list)
    for i in all_institutions:
        by_province[i.get("_province")].append(i)

    if args.denetim:
        # Bu okulun puanını şu an hangi kurum(lar) taşıyor? Not metnindeki ortalama yüzdelik + program sayısı izi.
        akad = fetch_all_paginated(supabase_url, headers,
                                   f"/rest/v1/institution_criteria_scores?select=institution_id,source_note&criteria_id=eq.{criteria_lookup.get('akademik_basari')}&source_note=ilike.*tabanpuanlari.net%20(MEB*")
        iz = defaultdict(list)
        for a in akad:
            m = re.search(r"(\d+) programın .*?ortalama yüzdelik dilimi \(([\d.]+)\)", a["source_note"] or "")
            if m:
                iz[(m.group(1), m.group(2))].append(a["institution_id"])
        satirlar = []
        for school in schools:
            match, neden = find_existing_match(school["name"], by_province.get(school["il_adi"], []))
            simdiki = [x for x in iz.get((str(school["program_count"]), str(school["avg_yuzdelik"])), [])
                       if x in {i["id"] for i in by_province.get(school["il_adi"], [])}] if school["avg_yuzdelik"] is not None else []
            durum = ("dogru" if match and match["id"] in simdiki else
                     "yanlis_kurumda" if match and simdiki else
                     "eksik" if match and not simdiki else
                     "eslesmiyor_ama_puanli" if simdiki else "eslesmiyor")
            sayac[durum] += 1
            satirlar.append({"il": school["il_adi"], "okul_adi": school["name"], "yeni_eslesme": match["id"] if match else None,
                             "eslesme_nedeni": neden, "simdiki_kurumlar": simdiki, "durum": durum,
                             "ort_yuzdelik": school["avg_yuzdelik"], "program_sayisi": school["program_count"]})
        for k in range(0, len(satirlar), 500):
            requests.post(f"{supabase_url}/rest/v1/lgs_eslesme_denetimi",
                          headers={**headers, "Prefer": "return=minimal"}, json=satirlar[k:k + 500]).raise_for_status()
        print("LGS_DENETIM " + json.dumps(dict(sayac), ensure_ascii=False))
        return

    for school in schools:
        same_province = by_province.get(school["il_adi"], [])
        match, neden = find_existing_match(school["name"], same_province) if same_province else (None, "il_yok")
        sayac[neden] += 1

        if match:
            write_scores_and_kontenjan(match["id"], school)
            updated += 1
            continue
        if not args.yeni_kurum_ekle:
            skipped.append(f"{school['il_adi']} / {school['name']} ({neden})")
            continue

        il_location_id = province_id_by_name.get(school["il_adi"])
        if not il_location_id:
            print(f"UYARI: '{school['il_adi']}' il konumu bulunamadı - '{school['name']}' atlanıyor.")
            skipped.append(school["name"])
            continue

        type_slug = guess_type(school["name"])
        type_id = type_lookup.get(type_slug)
        full_name = f"{school['il_adi'].upper()} - {school['name']}"
        payload = {
            "name": full_name,
            "institution_type_id": type_id,
            "category_id": category_lookup.get(args.category_slug),
            "location_id": il_location_id,
            "is_public": True,
            "is_verified": False,
            "description": (
                "Bu kurum tabanpuanlari.net kaynağından (MEB resmi LGS verilerinden derlenmiştir) "
                "otomatik olarak eklenmiştir. Not: Bu kaynakta ilçe bilgisi bulunmadığı için kurum "
                f"şimdilik il düzeyinde ({school['il_adi']}) konumlandırılmıştır; kesin ilçe/koordinat "
                "bilgisi MEB taramasıyla veya 'Profilini Sahiplen' ile netleşecektir."
            ),
        }
        resp = requests.post(
            f"{supabase_url}/rest/v1/institutions",
            headers={**headers, "Prefer": "return=representation"}, json=payload,
        )
        if resp.status_code not in (200, 201):
            print(f"UYARI: '{full_name}' eklenemedi -> {resp.status_code} {resp.text[:200]}")
            skipped.append(school["name"])
            continue

        new_institution_id = resp.json()[0]["id"]
        all_institutions.append({"id": new_institution_id, "name": full_name, "_province": school["il_adi"]})
        write_scores_and_kontenjan(new_institution_id, school)
        inserted += 1

    print(f"\nTamamlandı: {updated} kurum güncellendi, {inserted} yeni kurum eklendi, {len(skipped)} okul atlandı.")
    print("ESLESME_OZETI " + json.dumps(dict(sayac), ensure_ascii=False))
    requests.post(f"{supabase_url}/rest/v1/scrape_progress?on_conflict=key",
                  headers={**headers, "Prefer": "resolution=merge-duplicates,return=minimal"},
                  json={"key": "tabanpuan_son_yukleme_ozeti",
                        "value": json.dumps({"guncellendi": updated, "eklendi": inserted, "atlandi": len(skipped),
                                             **sayac, "atlanan_ornek": skipped[:40]}, ensure_ascii=False)})
    if skipped:
        print("--- Atlanan okullar ---")
        for name in skipped[:20]:
            print(f"  ? {name}")


if __name__ == "__main__":
    main()
