-- The extract date is the end date AR writes on open group memberships.
select
    l.legislature,
    l.legislature_id,
    l.start_date,
    l.end_date,
    (
        select max(g.end_date)
        from stg_informacao_base__deputies d, unnest(d.groups) as u(g)
        where d.legislature = l.legislature
    ) as extract_date
from stg_informacao_base__legislatures l
order by l.start_date
