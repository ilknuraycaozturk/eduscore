-- EduScor - Supabase SQL Editor'de BİR KEZ çalıştırılacak betik (06.10.2026)
-- Ne yapar:
--   A) Genel skoru (success_score_v2) otomatik güncel tutan tetikleyicileri kurar (EDU-SCORE-004)
--   B) Eski kalmış genel skorları bir kez yeniden hesaplar
--   C) Birleştirilmiş 5 TOZOK kopyasını siler (verileri asıl kayıtlara zaten aktarıldı)
-- Tamamı tek bir işlem (transaction) içinde: bir adım hata verirse hiçbir şey değişmez.

begin;

-- ===== A) Tetikleyiciler =====
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

-- ===== B) Bir kerelik yeniden hesaplama =====
-- criteria_available_v2'si boş olan kurumlar (name=name tetikleyiciyi çalıştırır)
update public.institutions set name = name where criteria_available_v2 is null;
-- Skoru olan ya da genel skoru dolu olan her kurumu yeniden hesapla
select count(*) as yeniden_hesaplanan from (
  select public.eduscor_recompute_v2(i.id) from public.institutions i
  where i.success_score_v2 is not null
     or exists (select 1 from public.institution_criteria_scores s where s.institution_id = i.id)
) x;

-- ===== C) Birleştirilmiş TOZOK kopyalarını sil =====
delete from public.institutions
where created_at::date = '2026-09-16'
  and id in ('55442d6f-8e24-4f8b-9f6a-fb482a763240',  -- ÖZEL İTALYAN LİSESİ
             '7ef7795b-c9a5-4d6a-b995-75e575596ef4',  -- ÖZEL NOTRE DAME DE SION FRANSIZ LİSESİ
             'fa84d7ff-ed5f-4109-b6a6-1553042bd9be',  -- ÖZEL SAINT BENOIT FRANSIZ LİSESİ
             '208099d5-1e9d-469a-ad54-c1ef3d643b71',  -- ÖZEL SAINT MICHEL FRANSIZ LİSESİ
             '6191ae49-8881-4d2c-bb86-b0be3cdc2ca4'); -- ÖZEL SAINTE PULCHERIE FRANSIZ LİSESİ

commit;
