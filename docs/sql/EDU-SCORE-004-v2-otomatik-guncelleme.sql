-- EDU-SCORE-004: success_score_v2 / evidence_coverage_v2'yi otomatik güncel tutma
-- 06.10.2026 - UYGULANDI: proje sahibi Supabase SQL Editor'de EDU-SCORE-004-supabase-sql-editor.sql ile çalıştırdı (kontrol: Kadıköy İstanbul AL 77,5 -> 61,3; boş kapsam 0).
--
-- Sorun: Genel skor (success_score_v2) ve kanıt kapsamı (evidence_coverage_v2) yalnızca
-- elle çalıştırılan bir hesaplamayla dolduruluyordu. Günlük yükleme betikleri kriter satırı
-- ekleyince/değiştirince bu alanlar eski kalıyordu (06.10.2026'da ~75 okulda uyuşmazlık).
--
-- Çözüm: Formül değişmedi (EDU-SCORE-002), yalnızca hesaplamanın NE ZAMAN yapıldığı değişti:
--   success_score_v2  = Σ(skor × varsayılan ağırlık) / Σ(varsayılan ağırlık)   [skoru olan kriterler]
--   evidence_coverage_v2 = 100 × Σ(kullanılan ağırlık) / criteria_available_v2
--   criteria_available_v2 = 100 (lise) | 43 (diğer)  -- lise: tür slug'ı ya da adı "lise" içeriyor
-- Kural, mevcut 14.933 kaydın tamamında birebir doğrulandı (6.337 × 43, 8.596 × 100).

-- 1) Tek bir kurumun v2 alanlarını yeniden hesaplar
create or replace function public.eduscor_recompute_v2(p_institution_id uuid)
returns void
language plpgsql
security definer
set search_path = public
as $$
declare
  v_sum_ws numeric; v_sum_w numeric; v_n int; v_avail numeric;
begin
  select sum(s.score * sc.default_weight), sum(sc.default_weight), count(*)
    into v_sum_ws, v_sum_w, v_n
  from institution_criteria_scores s
  join scoring_criteria sc on sc.id = s.criteria_id
  where s.institution_id = p_institution_id and s.score is not null;

  select criteria_available_v2 into v_avail from institutions where id = p_institution_id;

  update institutions set
    success_score_v2 = case when v_sum_w > 0 then round(v_sum_ws / v_sum_w, 1) end,
    evidence_coverage_v2 = case when v_sum_w > 0 and v_avail > 0 then round(100.0 * v_sum_w / v_avail, 1) end,
    success_score_v2_criteria_count = case when v_sum_w > 0 then v_n end,
    success_score_v2_computed_at = now()
  where id = p_institution_id;
end;
$$;

-- 2) Kriter satırı eklenince / değişince / silinince ilgili kurumu yeniden hesapla
create or replace function public.eduscor_trg_scores_recompute_v2()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  if tg_op in ('INSERT', 'UPDATE') then
    perform eduscor_recompute_v2(new.institution_id);
  end if;
  if tg_op = 'DELETE' or (tg_op = 'UPDATE' and old.institution_id is distinct from new.institution_id) then
    perform eduscor_recompute_v2(old.institution_id);
  end if;
  return null;
end;
$$;

drop trigger if exists trg_scores_recompute_v2 on public.institution_criteria_scores;
create trigger trg_scores_recompute_v2
after insert or delete or update of score, criteria_id, institution_id
on public.institution_criteria_scores
for each row execute function public.eduscor_trg_scores_recompute_v2();

-- 3) Yeni kurum eklenince ya da türü/adı değişince criteria_available_v2'yi ayarla
create or replace function public.eduscor_trg_set_criteria_available_v2()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
declare v_slug text;
begin
  select slug into v_slug from institution_types where id = new.institution_type_id;
  new.criteria_available_v2 := case
    when lower(translate(coalesce(new.name, ''), 'İIıÇçĞğÖöŞşÜü', 'iiiccggoossuu')) like '%lise%'
      or coalesce(v_slug, '') like '%lise%' then 100 else 43 end;
  return new;
end;
$$;

drop trigger if exists trg_set_criteria_available_v2 on public.institutions;
create trigger trg_set_criteria_available_v2
before insert or update of name, institution_type_id
on public.institutions
for each row execute function public.eduscor_trg_set_criteria_available_v2();

-- Not: Bu fonksiyonlar yalnızca trigger'lar tarafından çağrılmalı; dışarıdan RPC ile çağrılmasın.
revoke execute on function public.eduscor_recompute_v2(uuid) from public, anon, authenticated;
