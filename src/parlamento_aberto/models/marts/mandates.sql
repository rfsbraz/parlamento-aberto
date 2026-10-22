-- AR publishes one deputies list for legislature I in both the I-A and I-B folders, with
-- every situation from 1976 to 1982. Each part keeps only the periods that overlap its own
-- dates, with the dates as published (docs/known-gaps.md).
with m as (
    select
        d.legislature,
        d.cadastro_id,
        d.deputy_id,
        d.circle_id,
        s.situation,
        s.situation like 'Efetivo%' as is_effective,
        s.start_date,
        s.end_date
    from stg_informacao_base__deputies d, unnest(d.situations) as u(s)
)
select m.*
from m
left join legislatures l on l.legislature = m.legislature
where m.legislature not in ('I-A', 'I-B')
    or (
        m.start_date <= l.end_date
        and (m.end_date is null or m.end_date >= l.start_date)
    )
order by m.legislature, m.cadastro_id, m.start_date, m.situation
