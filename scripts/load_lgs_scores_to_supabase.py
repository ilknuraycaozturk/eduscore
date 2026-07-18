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


def turkish_lower(s: str) -> str:
    return s.replace("İ", "i").replace("I", "ı").lower()


def normalize_name(name: str) -> str:
    n = turkish_lower(name.strip())
    n = n.replace("özel", "").strip()
    return " ".join(n.split())


def find_existing_match(new_name: str, existing: list[dict]) -> dict | None:
    target = normalize_name(new_name)
    for row in existing:
        existing_norm = normalize_name(row["name"])
        if target == existing_norm or target in existing_norm or existing_norm in target:
            return row
    return None


def get_lookup(base_url: str, headers: dict, table: str, key_field: str = "slug") -> dict[str, str]:
    resp = requests.get(f"{base_url}/rest/v1/{table}?select=id,{key_field}", headers=headers)
    resp.raise_for_status()
    return {r[key_field]: r["id"] for r in resp.json()}


def get_or_create_location(base_url: str, headers: dict, ilce_adi: str, ankara_id: str,
                            location_cache: dict, dry_run: bool) -> str | None:
    key = ilce_adi.title()
    if key in location_cache:
        return location_cache[key]

    resp = requests.get(
        f"{base_url}/rest/v1/locations?select=id,name&parent_id=eq.{ankara_id}&name=eq.{key}",
        headers=headers,
    )
    resp.raise_for_status()
    rows = resp.json()
    if rows:
        location_cache[key] = rows[0]["id"]
        return rows[0]["id"]

    if dry_run:
        print(f"[DRY-RUN] Yeni ilçe konumu oluşturulacaktı: {key}")
        return None

    payload = {"parent_id": ankara_id, "level": "district", "name": key}
    resp = requests.post(f"{base_url}/rest/v1/locations", headers={**headers, "Prefer": "return=representation"}, json=payload)
    resp.raise_for_status()
    new_id = resp.json()[0]["id"]
    location_cache[key] = new_id
    print(f"Yeni ilçe konumu oluşturuldu: {key}")
    return new_id


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
        schools.append({
            "name": rows[0]["il"] + " - " + rows[0]["ilce"] + " - " + name,
            "ilce": rows[0]["ilce"],
            "institution_type_slug": rows[0]["institution_type_slug"],
            "avg_taban_yuzde": round(avg_yuzde, 2),
            "program_count": len(rows),
        })

    print(f"{len(schools)} benzersiz okul (program bazında gruplanmış).")

    if args.dry_run:
        print(json.dumps(schools[:5], ensure_ascii=False, indent=2))
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

    # Ankara il kaydını bul
    resp = requests.get(f"{supabase_url}/rest/v1/locations?select=id,name&name=eq.Ankara", headers=headers)
    resp.raise_for_status()
    ankara_rows = resp.json()
    if not ankara_rows:
        print("HATA: 'Ankara' locations tablosunda bulunamadı.")
        sys.exit(1)
    ankara_id = ankara_rows[0]["id"]

    location_cache: dict[str, str] = {}
    inserted_inst, enriched_inst, updated_scores, inserted_scores = 0, 0, 0, 0

    # ÖNEMLİ: Dedup kontrolü ilçe bazlı değil, TÜM Ankara kurumları arasında
    # GLOBAL yapılır. Aksi halde farklı konum granülerliğinde (mahalle vs ilçe)
    # kaydedilmiş aynı okul, farklı location_id'lere sahip olduğu için
    # eşleşmeyip mükerrer kayıt olarak eklenebilir (bu bug'ı canlı ortamda
    # yaşadık: Bağlıca'da mahalle düzeyinde kayıtlı bir okul, ilçe düzeyinde
    # arama yapan bu script tarafından bulunamayıp tekrar eklenmişti).
    all_institutions = requests.get(
        f"{supabase_url}/rest/v1/institutions?select=id,name", headers=headers,
    ).json()
    print(f"Global dedup kontrolü için {len(all_institutions)} mevcut kurum yüklendi.")

    for school in schools:
        location_id = get_or_create_location(supabase_url, headers, school["ilce"], ankara_id, location_cache, args.dry_run)
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

    print(f"Tamamlandı: {inserted_inst} yeni kurum, {enriched_inst} mevcut kurumla eşleşti, {inserted_scores} akademik başarı skoru yazıldı.")


if __name__ == "__main__":
    main()
