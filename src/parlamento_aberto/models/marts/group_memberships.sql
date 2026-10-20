-- AR writes the extract date as the end date of open memberships, so an end date
-- on or after the extract date of a legislature that has not ended means open.
with m as (
    select
        d.legislature,
        d.cadastro_id,
        g.group_id,
        g.group_acronym,
        g.start_date,
        g.end_date,
        l.end_date is null and g.end_date >= l.extract_date as is_open
    from stg_informacao_base__deputies d
    cross join unnest(d.groups) as u(g)
    join legislatures l on l.legislature = d.legislature
)
select
    legislature,
    cadastro_id,
    group_id,
    group_acronym,
    start_date,
    case when is_open then null else end_date end as end_date,
    is_open
from m
order by legislature, cadastro_id, start_date
