"""
load_lgs_scores_to_supabase.py
================================
EduScor — scrape_lgs_taban_puanlari.py çıktısını (Ankara'daki LGS ile
öğrenci alan tüm liseler) Supabase'e yükler.

Mantık:
1. Aynı okul birden fazla ALAN/program için ayrı satırlarda gelebilir
   (örn. Fen ve Sosyal Bilimler Programı, farklı yabancı diller vb.) ->
   okul adına göre gruplanıp taban_yüzde ortalaması alınır.
2. Okul zaten institutions tablosunda var mı kontrol edilir (isim +
   Türkçe İ/i düzeltmeli karşılaştırma). Yoksa yeni kurum olarak eklenir.
3. İlçe seviyesinde locations kaydı yoksa otomatik oluşturulur (Ankara
   altında).
4. institution_criteria_scores.akademik_basari alanı yazılır/güncellenir.
   Skor = 100 - ortalama_taban_yüzde (düşük yüzdelik dilim = daha başarılı).

Kullanım:
    export SUPABASE_URL="..."
    export SUPABASE_SERVICE_ROLE_KEY="..."
    python load_lgs_scores_to_supabase.py --input data/ankara_lgs_taban_puanlari.json --pdf-url "https://..." --dry-run
"""

import argparse
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

import requests


from eduscor_data_utils import normalize_name, find_existing_match  # EDU-DATA-001


def get_lookup(base_url: str, headers: dict, table: str, key_field: str = "slug") -> dict[str, str]:
    resp = requests.get(f"{base_url}/rest/v1/{table}?select=id,{key_field}", headers=headers)
    resp.raise_for_status()
    return {r[key_field]: r["id"] for r in resp.json()}


def get_or_create_province(base_url: str, headers: dict, il_adi: str, turkiye_id: str,
                            location_cache: dict, dry_run: bool) -> str | None:
    key = ("__il__", il_adi.title())
    if key in location_cache:
        return location_cache[key]

    resp = requests.get(
        f"{base_url}/rest/v1/locations?select=id,name&parent_id=eq.{turkiye_id}&name=eq.{il_adi.title()}",
        headers=headers,
    )
    resp.raise_for_status()
    rows = resp.json()
    if rows:
        location_cache[key] = rows[0]["id"]
        return rows[0]["id"]

    if dry_run:
        print(f"[DRY-RUN] Yeni il konumu oluşturulacaktı: {il_adi.title()}")
        return None

    payload = {"parent_id": turkiye_id, "level": "province", "name": il_adi.title()}
    resp = requests.post(f"{base_url}/rest/v1/locations", headers={**headers, "Prefer": "return=representation"}, json=payload)
    resp.raise_for_status()
    new_id = resp.json()[0]["id"]
    location_cache[key] = new_id
    print(f"Yeni il konumu oluşturuldu: {il_adi.title()}")
    return new_id


def get_or_create_location(base_url: str, headers: dict, il_adi: str, ilce_adi: str, turkiye_id: str,
                            location_cache: dict, dry_run: bool) -> str | None:
    # ÖNEMLİ: Cache anahtarı (il, ilçe) ikilisi olmalı - aynı ilçe adı
    # (örn. "Merkez") birden fazla ilde tekrar edebilir.
    key = (il_adi.title(), ilce_adi.title())
    if key in location_cache:
        return location_cache[key]

    il_id = get_or_create_province(base_url, headers, il_adi, turkiye_id, location_cache, dry_run)
    if not il_id:
        return None

    resp = requests.get(
        f"{base_url}/rest/v1/locations?select=id,name&parent_id=eq.{il_id}&name=eq.{ilce_adi.title()}",
        headers=headers,
    )
    resp.raise_for_status()
    rows = resp.json()
    if rows:
        location_cache[key] = rows[0]["id"]
        return rows[0]["id"]

    if dry_run:
        print(f"[DRY-RUN] Yeni ilçe konumu oluşturulacaktı: {il_adi.title()} / {ilce_adi.title()}")
        return None

    payload = {"parent_id": il_id, "level": "district", "name": ilce_adi.title()}
    resp = requests.post(f"{base_url}/rest/v1/locations", headers={**headers, "Prefer": "return=representation"}, json=payload)
    resp.raise_for_status()
    new_id = resp.json()[0]["id"]
    location_cache[key] = new_id
    print(f"Yeni ilçe konumu oluşturuldu: {il_adi.title()} / {ilce_adi.title()}")
    return new_id


def fetch_all_paginated(base_url: str, headers: dict, path_with_query: str, page_size: int = 1000) -> list[dict]:
    """PostgREST varsayılan olarak isteği 1000 satırla sınırlıyor - tüm
    satırları almak için limit/offset ile sayfalama yapıyoruz."""
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
    parser = argparse.ArgumentParser(description="Ankara LGS taban puan verisini Supabase'e yükler.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--pdf-url", required=True, help="Kaynak gösterimi için PDF URL'i")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    supabase_url = os.environ.get("SUPABASE_URL")
    service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not args.dry_run and (not supabase_url or not service_key):
        print("HATA: SUPABASE_URL ve SUPABASE_SERVICE_ROLE_KEY gerekli.")
        sys.exit(1)

    raw = json.loads(Path(args.input).read_text(encoding="utf-8"))
    print(f"{len(raw)} ham satır okundu.")

    # Okul adına göre grupla (birden fazla ALAN/program aynı okulda olabilir)
    grouped: dict[str, list[dict]] = defaultdict(list)
    for r in raw:
        grouped[r["okul_adi"]].append(r)

    schools = []
    for name, rows in grouped.items():
        avg_yuzde = sum(r["taban_yuzde"] for r in rows) / len(rows)
        hazirlik_var = any(r.get("hazirlik_var") for r in rows)
        schools.append({
            "name": rows[0]["il"] + " - " + rows[0]["ilce"] + " - " + name,
            "il": rows[0]["il"],
            "ilce": rows[0]["ilce"],
            "institution_type_slug": rows[0]["institution_type_slug"],
            "avg_taban_yuzde": round(avg_yuzde, 2),
            "hazirlik_var": hazirlik_var,
            "program_count": len(rows),
        })

    print(f"{len(schools)} benzersiz okul (program bazında gruplanmış).")

    if args.dry_run:
        hazirlik_true = sum(1 for s in schools if s["hazirlik_var"])
        by_type: dict[str, int] = defaultdict(int)
        for s in schools:
            by_type[s["institution_type_slug"]] += 1
        print("--- ÖZET ---")
        print(f"Hazırlık Sınıfı olan okul sayısı: {hazirlik_true} / {len(schools)}")
        print("Türe göre dağılım:", dict(by_type))
        print("--- Hazırlık Sınıfı OLAN ilk 5 örnek ---")
        print(json.dumps([s for s in schools if s["hazirlik_var"]][:5], ensure_ascii=False, indent=2))
        print("--- Hazırlık Sınıfı OLMAYAN ilk 3 örnek ---")
        print(json.dumps([s for s in schools if not s["hazirlik_var"]][:3], ensure_ascii=False, indent=2))
        print("... (dry-run, Supabase'e yazılmadı)")
        return

    headers = {
        "apikey": service_key,
        "Authorization": f"Bearer {service_key}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }

    type_lookup = get_lookup(supabase_url, headers, "institution_types", "slug")
    category_lookup = get_lookup(supabase_url, headers, "categories", "slug")
    criteria_lookup = get_lookup(supabase_url, headers, "scoring_criteria", "key")

    # Türkiye kök kaydını bul (tüm iller bunun altında oluşturulur/aranır)
    resp = requests.get(f"{supabase_url}/rest/v1/locations?select=id,name&name=eq.Türkiye", headers=headers)
    resp.raise_for_status()
    turkiye_rows = resp.json()
    if not turkiye_rows:
        print("HATA: 'Türkiye' locations tablosunda bulunamadı.")
        sys.exit(1)
    turkiye_id = turkiye_rows[0]["id"]

    location_cache: dict[str, str] = {}
    inserted_inst, enriched_inst, updated_scores, inserted_scores = 0, 0, 0, 0

    # ÖNEMLİ: Dedup kontrolü ilçe bazlı değil, TÜM Ankara kurumları arasında
    # GLOBAL yapılır. Aksi halde farklı konum granülerliğinde (mahalle vs ilçe)
    # kaydedilmiş aynı okul, farklı location_id'lere sahip olduğu için
    # eşleşmeyip mükerrer kayıt olarak eklenebilir (bu bug'ı canlı ortamda
    # yaşadık: Bağlıca'da mahalle düzeyinde kayıtlı bir okul, ilçe düzeyinde
    # arama yapan bu script tarafından bulunamayıp tekrar eklenmişti).
    all_institutions = fetch_all_paginated(supabase_url, headers, "/rest/v1/institutions?select=id,name")
    print(f"Global dedup kontrolü için {len(all_institutions)} mevcut kurum yüklendi.")

    for school in schools:
        location_id = get_or_create_location(supabase_url, headers, school["il"], school["ilce"], turkiye_id, location_cache, args.dry_run)
        if not location_id:
            continue

        match = find_existing_match(school["name"], all_institutions)
        academic_score = round(100 - school["avg_taban_yuzde"], 2)
        source_note = (
            f"Kaynak: MEB resmi LGS yerleştirme kılavuzu PDF'i ({args.pdf_url}). "
            f"{school['program_count']} programın ortalama taban yüzdelik dilimi ({school['avg_taban_yuzde']}) "
            f"üzerinden hesaplanmıştır (skor = 100 - yüzdelik dilim)."
        )

        if match:
            institution_id = match["id"]
            enriched_inst += 1
        else:
            type_id = type_lookup.get(school["institution_type_slug"])
            payload = {
                "name": school["name"],
                "institution_type_id": type_id,
                "category_id": category_lookup.get("okul-oncesi-k12"),
                "location_id": location_id,
                "is_public": True,
                "is_verified": False,
                "description": "Bu kurum MEB'in resmi LGS yerleştirme kılavuzundan otomatik olarak eklenmiştir.",
            }
            resp = requests.post(
                f"{supabase_url}/rest/v1/institutions",
                headers={**headers, "Prefer": "return=representation"}, json=payload,
            )
            if resp.status_code not in (200, 201):
                print(f"UYARI: '{school['name']}' eklenemedi -> {resp.status_code} {resp.text[:200]}")
                continue
            institution_id = resp.json()[0]["id"]
            inserted_inst += 1
            all_institutions.append({"id": institution_id, "name": school["name"]})

        criteria_id = criteria_lookup.get("akademik_basari")
        score_payload = {
            "institution_id": institution_id,
            "criteria_id": criteria_id,
            "score": academic_score,
            "source_note": source_note,
            "is_verified": False,
        }
        resp = requests.post(
            f"{supabase_url}/rest/v1/institution_criteria_scores",
            headers={**headers, "Prefer": "resolution=merge-duplicates"},
            json=score_payload,
        )
        if resp.status_code in (200, 201, 204):
            inserted_scores += 1
        else:
            print(f"UYARI: '{school['name']}' skoru yazılamadı -> {resp.status_code} {resp.text[:200]}")

        # Yabancı Dil Eğitimi kriteri: PDF'te "Hazırlık Sınıfı Bulunan" türü ayrıca
        # belirtiliyor - hazırlık sınıfı olan okullar yoğunlaştırılmış yabancı dil
        # eğitimi veriyor demektir. Bu basit ama gerçek/kaynaklı bir proxy'dir;
        # IB/ikinci yabancı dil gibi zenginleştirilmiş programları KAPSAMAZ
        # (bu bilgi bu PDF'te yok, source_note'ta açıkça belirtiliyor).
        yabanci_dil_score = 100 if school["hazirlik_var"] else 40
        yabanci_dil_note = (
            f"Kaynak: MEB resmi LGS yerleştirme kılavuzu PDF'i ({args.pdf_url}). "
            f"{'Okulda Hazırlık Sınıfı bulunuyor (yoğunlaştırılmış yabancı dil eğitimi).' if school['hazirlik_var'] else 'Okulda Hazırlık Sınıfı bulunmuyor, standart müfredat yabancı dil dersi var.'} "
            "NOT: Bu skor sadece 'hazırlık sınıfı var mı' bilgisine dayanır; IB, ikinci yabancı dil "
            "gibi zenginleştirilmiş programlar hakkında bilgi içermez (ayrı kaynak gerekir)."
        )
        resp2 = requests.post(
            f"{supabase_url}/rest/v1/institution_criteria_scores",
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

    print(f"Tamamlandı: {inserted_inst} yeni kurum, {enriched_inst} mevcut kurumla eşleşti, {inserted_scores} akademik başarı skoru yazıldı.")


if __name__ == "__main__":
    main()
