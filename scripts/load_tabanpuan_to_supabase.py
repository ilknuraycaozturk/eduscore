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


def normalize_name(name: str) -> str:
    n = turkish_lower(name.strip())
    n = n.replace("özel", "").strip()
    return " ".join(n.split())


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


def find_existing_match(new_name: str, existing: list[dict]) -> dict | None:
    target = normalize_name_lenient(new_name)
    best = None
    for row in existing:
        existing_norm = normalize_name_lenient(row["name"])
        if target == existing_norm:
            return row  # tam eşleşme - hemen dön
        if (target in existing_norm or existing_norm in target) and best is None:
            best = row
    return best


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
    parser = argparse.ArgumentParser(description="tabanpuanlari.net verisini Supabase'e yükler (sadece mevcut kurumları günceller).")
    parser.add_argument("--input", required=True)
    parser.add_argument("--il", default="Ankara", help="Yeni eklenecek (eşleşmeyen) kurumlar için il adı")
    parser.add_argument("--category-slug", default="okul-oncesi-k12")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    supabase_url = os.environ.get("SUPABASE_URL")
    service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not args.dry_run and (not supabase_url or not service_key):
        print("HATA: SUPABASE_URL ve SUPABASE_SERVICE_ROLE_KEY gerekli.")
        sys.exit(1)

    raw = json.loads(Path(args.input).read_text(encoding="utf-8"))
    print(f"{len(raw)} ham program satırı okundu.")

    grouped: dict[str, list[dict]] = defaultdict(list)
    for r in raw:
        grouped[r["okul_adi"]].append(r)

    schools = []
    for name, rows in grouped.items():
        yuzdelikler = [r["yuzdelik_2026"] if r.get("yuzdelik_2026") is not None else r.get("yuzdelik_2025")
                       for r in rows]
        yuzdelikler = [y for y in yuzdelikler if y is not None]
        veri_yili = "2026" if any(r.get("yuzdelik_2026") is not None for r in rows) else "2025"
        avg_yuzdelik = round(sum(yuzdelikler) / len(yuzdelikler), 2) if yuzdelikler else None
        toplam_kontenjan_2026 = sum(r["kontenjan_2026"] for r in rows if r["kontenjan_2026"])
        toplam_kontenjan_2025 = sum(r["kontenjan_2025"] for r in rows if r["kontenjan_2025"])
        hazirlik_var = any((r.get("sure") or "").strip() == "5 yıl" for r in rows)
        schools.append({
            "name": name,
            "avg_yuzdelik": avg_yuzdelik,
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

    # Yeni kurum eklenecekse hangi il/konum altına ekleneceğini bul (ilçe bilgisi
    # bu kaynakta yok, bu yüzden İL DÜZEYİNDE konumlandırılıyor - "Profilini
    # Sahiplen" ya da bir sonraki MEB taramasıyla ilçe bilgisi netleşebilir).
    resp = requests.get(f"{supabase_url}/rest/v1/locations?select=id,name&name=eq.{args.il.title()}", headers=headers)
    resp.raise_for_status()
    il_rows = resp.json()
    il_location_id = il_rows[0]["id"] if il_rows else None
    if not il_location_id:
        print(f"UYARI: '{args.il}' il konumu bulunamadı - eşleşmeyen okullar eklenemeyecek, sadece atlanacak.")

    all_institutions = fetch_all_paginated(supabase_url, headers, "/rest/v1/institutions?select=id,name")
    print(f"Eşleştirme için {len(all_institutions)} mevcut kurum yüklendi.")

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
            source_note = (
                f"Kaynak: tabanpuanlari.net (MEB resmi LGS yerleştirme verilerinden derlenmiştir, {school['veri_yili']} verisi). "
                f"{school['program_count']} programın ortalama yüzdelik dilimi ({school['avg_yuzdelik']}) "
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

    for school in schools:
        match = find_existing_match(school["name"], all_institutions)

        if match:
            write_scores_and_kontenjan(match["id"], school)
            updated += 1
            continue

        if not il_location_id:
            skipped.append(school["name"])
            continue

        type_slug = guess_type(school["name"])
        type_id = type_lookup.get(type_slug)
        full_name = f"{args.il.upper()} - {school['name']}"
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
                f"şimdilik il düzeyinde ({args.il}) konumlandırılmıştır; kesin ilçe/koordinat bilgisi "
                "MEB taramasıyla veya 'Profilini Sahiplen' ile netleşecektir."
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
        all_institutions.append({"id": new_institution_id, "name": full_name})
        write_scores_and_kontenjan(new_institution_id, school)
        inserted += 1

    print(f"\nTamamlandı: {updated} kurum güncellendi, {inserted} yeni kurum eklendi, {len(skipped)} okul atlandı.")
    if skipped:
        print("--- Atlanan okullar ---")
        for name in skipped[:20]:
            print(f"  ? {name}")


if __name__ == "__main__":
    main()
