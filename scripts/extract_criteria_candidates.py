"""
extract_criteria_candidates.py
===============================
EduScor — website_crawl_snapshots'taki HAM HTML'den, ana içeriği
(menü/footer temizlenmiş) çıkarıp kriter göstergesi ADAYLARI üretir.

ÖNEMLİ SINIRLAR:
  - Bu script institution_criteria_scores'a HİÇBİR ŞEY YAZMAZ.
  - Sadece criteria_extraction_candidates'a DÜŞÜK GÜVENLİ adaylar yazar.
  - Bu adaylar kurum-paneli.html formunu ÖN-DOLDURMAK için kullanılır —
    kurum yöneticisi onaylar/düzeltirse gerçek beyana (institution_criteria_scores)
    dönüşür. Otomatik çıkarımın en değerli kullanımı budur, "kesin doğru
    veri üretmek" değil.
  - AĞA ÇIKMAZ — sadece daha önce kaydedilmiş snapshot'ları okur. Extraction
    kurallarını geliştirdikçe bu script'i istediğiniz kadar yeniden
    çalıştırabilirsiniz, derive_criteria_from_website.py'yi tekrar
    çalıştırmanıza gerek yok.

BOILERPLATE TEMİZLİĞİ:
  trafilatura kullanılır (menü/header/footer/tekrarlı navigasyon bloklarını
  ayıklar) — TED Ankara Koleji sayfasında "kütüphane" kelimesinin menüde
  20+ kere geçtiği ama gerçek içerikte sadece 1 kez geçtiği gibi durumlar
  için kritik. Ham regex bu ayrımı yapamaz.

GÜVEN SKORU (0.0-1.0):
  Sayısal kanıt varsa (ör. "421 kamera") > sadece kelime varlığı. Birden
  fazla kaynak sayfada tutarlı bulunması güveni artırır (bu script'in
  ileri versiyonunda). 0.6 altındaki adaylar kaydedilmez.

Kullanım:
    export SUPABASE_URL="..."
    export SUPABASE_SERVICE_ROLE_KEY="..."
    pip install trafilatura requests
    python extract_criteria_candidates.py
"""
import os
import re
import sys

import requests
import trafilatura

MIN_CONFIDENCE_TO_SAVE = 0.6
BATCH_SIZE = 200


def pg_get(base_url, headers, path):
    resp = requests.get(f"{base_url}{path}", headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.json()


def pg_upsert(base_url, headers, table, rows, on_conflict):
    if not rows:
        return
    up_headers = dict(headers)
    up_headers["Prefer"] = "resolution=merge-duplicates,return=minimal"
    resp = requests.post(
        f"{base_url}/rest/v1/{table}?on_conflict={on_conflict}",
        headers=up_headers, json=rows, timeout=30,
    )
    if resp.status_code >= 300:
        print(f"  ⚠️ Upsert hatası ({table}): {resp.status_code} {resp.text[:200]}")


# ---------------------------------------------------------------------------
# Gösterge kuralları: (criteria_key, field_id, regex_listesi, taban_güven,
# sayısal_kanıt_varsa_ek_güven)
# Her kural, ana-içerik metninde eşleşirse bir aday üretir.
# ---------------------------------------------------------------------------
RULES = [
    ("yabanci_dil", "hazirlik_sinifi", [r"hazırlık sınıf"], 0.7, None),
    ("yabanci_dil", "uluslararasi_program",
     [r"\bIB\b.{0,20}(diploma|program)", r"uluslararası bakalorya"], 0.7, None),
    ("fiziksel_altyapi", "kutuphane", [r"kütüphane\w* (bulun|mevcut|sahip)"], 0.6, None),
    ("fiziksel_altyapi", "akilli_tahta", [r"akıllı tahta"], 0.6, None),
    ("fiziksel_altyapi", "spor_salonu",
     [r"spor salon\w*", r"yüzme havuz\w*", r"kapalı spor"], 0.6, None),
    ("guvenlik_disiplin", "kamera_sistemi",
     [r"(\d+)\s*(adet\s*)?kamera"], 0.5, r"(\d{2,4})\s*(adet\s*)?kamera"),
    ("guvenlik_disiplin", "guvenlik_personeli",
     [r"güvenlik görevlisi", r"özel güvenlik"], 0.6, r"(\d{1,3})\s*(özel\s*)?güvenlik görevlisi"),
    ("burs_ucret", "burs_sistemi_var", [r"\bburs\w*\b.{0,30}(veril|sunul|uygulan)"], 0.6, None),
    ("burs_ucret", "meb_ucretsiz_okuma", [r"MEB ücretsiz okuma"], 0.8, None),
]


def run_rules(main_text: str):
    found = []
    for criteria_key, field_id, patterns, base_conf, numeric_pattern in RULES:
        matched = False
        confidence = base_conf
        evidence = None
        value = "true"

        for pat in patterns:
            m = re.search(pat, main_text, re.IGNORECASE)
            if m:
                matched = True
                evidence = main_text[max(0, m.start() - 60):m.end() + 60].strip()
                break

        if not matched:
            continue

        # Sayısal kanıt varsa güveni artır ve değeri sayı yap
        if numeric_pattern:
            nm = re.search(numeric_pattern, main_text, re.IGNORECASE)
            if nm:
                confidence = min(1.0, confidence + 0.35)
                num = next((g for g in nm.groups() if g and g.strip().isdigit()), None)
                if num:
                    value = "true"  # checkbox alanı - sayısal kanıt sadece güveni artırıyor

        if confidence >= MIN_CONFIDENCE_TO_SAVE:
            found.append({
                "criteria_key": criteria_key,
                "field_id": field_id,
                "candidate_value": value,
                "confidence": round(confidence, 2),
                "evidence_snippet": evidence[:300] if evidence else None,
            })
    return found


def main():
    base_url = os.environ.get("SUPABASE_URL")
    service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not base_url or not service_key:
        print("HATA: SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY ortam değişkenleri eksik.")
        sys.exit(1)

    headers = {
        "apikey": service_key,
        "Authorization": f"Bearer {service_key}",
        "Content-Type": "application/json",
    }

    snapshots = pg_get(base_url, headers,
                        f"/rest/v1/website_crawl_snapshots?select=id,institution_id,url,raw_html&limit={BATCH_SIZE}")

    print(f"{len(snapshots)} snapshot işlenecek.")

    total_candidates = 0
    for snap in snapshots:
        if not snap.get("raw_html"):
            continue

        # trafilatura ile boilerplate (menü/header/footer) temizliği -
        # bu, TED örneğinde "kütüphane" kelimesinin menüde 20+ kere
        # geçmesi ama gerçek içerikte 1 kez geçmesi sorununu çözer.
        main_text = trafilatura.extract(snap["raw_html"]) or ""
        if not main_text:
            continue

        candidates = run_rules(main_text)
        rows = []
        for c in candidates:
            rows.append({
                "institution_id": snap["institution_id"],
                "criteria_key": c["criteria_key"],
                "field_id": c["field_id"],
                "candidate_value": c["candidate_value"],
                "confidence": c["confidence"],
                "evidence_snippet": c["evidence_snippet"],
                "source_url": snap["url"],
            })

        if rows:
            pg_upsert(base_url, headers, "criteria_extraction_candidates", rows,
                      "institution_id,criteria_key,field_id")
            total_candidates += len(rows)
            print(f"  {snap['url']}: {len(rows)} aday bulundu")

    print(f"\nToplam: {total_candidates} aday gösterge kaydedildi (min güven: {MIN_CONFIDENCE_TO_SAVE}).")
    print("NOT: Bunlar institution_criteria_scores'a YAZILMADI - sadece")
    print("kurum-paneli.html formunu ön-dolduracak adaylar olarak saklandı.")


if __name__ == "__main__":
    main()
