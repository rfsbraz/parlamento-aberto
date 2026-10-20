-- One row per vote, group and position.
-- deputies is null when the group as a whole took the position (apart from any of
-- its deputies listed under another position), otherwise the number of its deputies
-- who did: the count in the detail ("2-PS") or, without a count, the named deputies.
-- Votes without a detail take absent groups and deputies from the ausencias field.
-- Unanimous votes that list no favour, against or abstention position get a favour
-- row for every other group seated on the vote date, with inferred = true. Seated
-- follows the same rule as the seated_on(d) macro.
with items as (
    select v.vote_id, v.legislature, i.kind, i.group_acronym, i.position, i.deputies
    from votes v
    join stg_votes__detail_items i on i.detail = v.detail
    where i.error is null
),
from_detail as (
    select
        vote_id,
        legislature,
        group_acronym,
        position,
        case
            when bool_or(kind = 'group') then null
            when bool_or(kind = 'count') then sum(deputies) filter (where kind = 'count')
            else count(*) filter (where kind = 'deputy')
        end::integer as deputies,
        false as inferred
    from items
    group by all
),
absence_items as (
    -- ausencias holds group codes and, for deputies, "Name (GROUP)".
    select
        v.vote_id,
        v.legislature,
        regexp_matches(g, '^.+ \([^()]+\)$') as is_deputy,
        coalesce(nullif(regexp_extract(g, '^.+ \(([^()]+)\)$', 1), ''), trim(g)) as group_acronym
    from votes v, unnest(v.absent_groups) as u(g)
    where v.detail is null
),
from_absences as (
    select
        vote_id,
        legislature,
        group_acronym,
        'absent' as position,
        case when bool_or(not is_deputy) then null else count(*) end::integer as deputies,
        false as inferred
    from absence_items
    group by all
),
listed as (
    select * from from_detail
    union
    select * from from_absences
),
to_infer as (
    select v.vote_id, v.legislature, v.date
    from votes v
    where v.unanimous
      and not exists (
          select 1 from listed l where l.vote_id = v.vote_id and l.position <> 'absent'
      )
),
covering as (
    select
        d.legislature,
        d.day,
        m.cadastro_id,
        m.is_effective,
        row_number() over (
            partition by d.legislature, d.day, m.cadastro_id
            order by m.start_date desc, coalesce(m.end_date, date '9999-12-31') desc
        ) as rn
    from (select distinct legislature, date as day from to_infer) d
    join mandates m
      on m.legislature = d.legislature
     and m.start_date <= d.day
     and (m.end_date is null or m.end_date >= d.day)
),
seated_groups as (
    select distinct c.legislature, c.day, g.group_acronym
    from covering c
    join group_memberships g
      on g.legislature = c.legislature
     and g.cadastro_id = c.cadastro_id
     and g.start_date <= c.day
     and (g.end_date is null or g.end_date >= c.day)
    where c.rn = 1 and c.is_effective
),
inferred as (
    select
        t.vote_id,
        t.legislature,
        s.group_acronym,
        'favour' as position,
        null::integer as deputies,
        true as inferred
    from to_infer t
    join seated_groups s on s.legislature = t.legislature and s.day = t.date
    where not exists (
        select 1 from listed l
        where l.vote_id = t.vote_id and l.group_acronym = s.group_acronym
    )
)
select * from listed
union all
select * from inferred
order by vote_id, group_acronym, position
