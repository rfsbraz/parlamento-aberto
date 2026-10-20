-- seated_by_period(d): for each person, the period that decides whether they are seated
-- at the end of day d, before swap days are handled. AR situation periods can overlap on
-- a handover day (for example an Efetivo and a Suspenso period that both cover
-- 2025-06-05). The latest-starting period covering d wins; on a tie, the longer one; on a
-- tie in both dates, the effective one (swap days below then decide who holds the seat).
create or replace macro seated_by_period(d) as table
select * exclude (rn)
from (
    select
        m.*,
        row_number() over (
            partition by m.legislature, m.cadastro_id
            order by
                m.start_date desc,
                coalesce(m.end_date, date '9999-12-31') desc,
                m.is_effective desc
        ) as rn
    from mandates m
    where m.start_date <= d and (m.end_date is null or m.end_date >= d)
)
where rn = 1 and is_effective;

-- seated_on(d): deputies holding a seat at the end of day d.
-- Swap days: AR dates are inclusive, so on the day one deputy hands a seat to another,
-- both periods cover d and the circle shows one deputy too many. At the end of d the
-- incoming deputy holds the seat. A period is outgoing on d when it ends on d and the
-- person has no effective period starting on d + 1. Incoming means starting an effective
-- period on d after not being seated on d - 1. A swap shows as a one-day spike: the
-- circle has more deputies on d than on both d - 1 and d + 1. In each circle, outgoing
-- periods do not count, up to the smaller of that spike and the number of incoming
-- people, earliest start first. A circle that fills a vacancy on d has no spike, so its
-- outgoing periods still count. Who replaced whom is not used, because the source does
-- not record it.
create or replace macro seated_on(d) as table
with today as (select * from seated_by_period(d)),
yesterday as (select * from seated_by_period(d - 1)),
tomorrow as (select * from seated_by_period(d + 1)),

circle_counts as (
    select legislature, circle_id, day, count(*) as n
    from (
        select legislature, circle_id, 0 as day from yesterday
        union all select legislature, circle_id, 1 from today
        union all select legislature, circle_id, 2 from tomorrow
    )
    group by all
),

-- How far each circle's count on d rises above both d - 1 and d + 1.
spike as (
    select
        t.legislature,
        t.circle_id,
        least(t.n - coalesce(y.n, 0), t.n - coalesce(n.n, 0)) as n
    from circle_counts t
    left join circle_counts y
      on y.legislature = t.legislature and y.circle_id = t.circle_id and y.day = 0
    left join circle_counts n
      on n.legislature = t.legislature and n.circle_id = t.circle_id and n.day = 2
    where t.day = 1
),

incoming as (
    select t.legislature, t.circle_id, count(*) as n
    from today t
    where t.start_date = d
      and not exists (
          select 1 from yesterday y
          where y.legislature = t.legislature and y.cadastro_id = t.cadastro_id
      )
    group by all
),

outgoing as (
    select
        t.legislature,
        t.cadastro_id,
        t.circle_id,
        row_number() over (
            partition by t.legislature, t.circle_id order by t.start_date, t.cadastro_id
        ) as k
    from today t
    where t.end_date = d
      and not exists (
          select 1 from mandates n
          where n.legislature = t.legislature
            and n.cadastro_id = t.cadastro_id
            and n.is_effective
            and n.start_date = d + 1
      )
),

dropped as (
    select o.legislature, o.cadastro_id
    from outgoing o
    join spike g using (legislature, circle_id)
    join incoming i using (legislature, circle_id)
    where o.k <= least(g.n, i.n)
)

select t.legislature, t.cadastro_id, t.deputy_id, t.circle_id, t.situation
from today t
anti join dropped x using (legislature, cadastro_id);
