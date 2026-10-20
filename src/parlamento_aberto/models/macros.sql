-- seated_on(d): deputies holding a seat at the end of day d.
-- AR situation periods can overlap on a handover day (for example an Efetivo period
-- and a Suspenso period that both cover 2025-06-05). The latest-starting period
-- covering d wins; on a tie, the longer one.
create or replace macro seated_on(d) as table
with covering as (
    select
        m.*,
        row_number() over (
            partition by m.legislature, m.cadastro_id
            order by m.start_date desc, coalesce(m.end_date, date '9999-12-31') desc
        ) as rn
    from mandates m
    where m.start_date <= d and (m.end_date is null or m.end_date >= d)
)
select legislature, cadastro_id, deputy_id, circle_id, situation
from covering
where rn = 1 and is_effective;
