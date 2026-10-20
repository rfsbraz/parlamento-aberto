-- One row per person. Names come from the most recent legislature they appear in;
-- RegistoBiografico wins for the full name when present. The biography fields come
-- from the latest legislature with a RegistoBiografico record for the person, named
-- in biography_legislature.
with latest as (
    select
        d.cadastro_id,
        arg_max(d.full_name, l.start_date) as full_name,
        arg_max(d.parliamentary_name, l.start_date) as parliamentary_name
    from stg_informacao_base__deputies d
    join stg_informacao_base__legislatures l using (legislature)
    group by d.cadastro_id
),
bio as (
    select
        b.cadastro_id,
        arg_max(b.full_name, l.start_date) as full_name,
        arg_max(b.birth_date, l.start_date) as birth_date,
        arg_max(b.sex, l.start_date) as sex,
        arg_max(b.profession, l.start_date) as profession,
        arg_max(b.legislature, l.start_date) as biography_legislature
    from stg_registo_biografico__biographies b
    join stg_informacao_base__legislatures l using (legislature)
    group by b.cadastro_id
)
select
    latest.cadastro_id,
    coalesce(bio.full_name, latest.full_name) as full_name,
    latest.parliamentary_name,
    bio.sex,
    bio.birth_date,
    bio.profession,
    bio.biography_legislature
from latest
left join bio using (cadastro_id)
order by latest.cadastro_id
