-- One row per vote, group and position. group_code_raw is the code as published;
-- group_code applies seed_group_aliases for the vote's legislature.
-- deputies is null when the group as a whole took the position (apart from any of
-- its deputies listed under another position), otherwise the number of its deputies
-- who did: the count in the detail ("2-PS") or, without a count, the named deputies.
-- Votes without a detail take absent groups and deputies from the ausencias field.
-- Unanimous votes that list no favour, against or abstention position get a favour
-- row for every other group seated on the vote date, with inferred = true. For a
-- plenary vote, seated follows the same rule as the seated_on(d) macro. For a committee
-- vote, it means the groups with an active effective member of that committee on the
-- day (ComposicaoOrgaos: sioDes Ativo, sioTipMem Efetivo; on overlapping situation
-- periods the latest-starting wins, then the longer one).
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
listed_raw as (
    select * from from_detail
    union
    select * from from_absences
),
listed as (
    select l.*, coalesce(a.group_code, l.group_acronym) as group_code
    from listed_raw l
    left join seed_group_aliases a
      on a.legislature = l.legislature and a.alias = l.group_acronym
),
to_infer as (
    select v.vote_id, v.legislature, v.date, v.committee_id
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
    from (select distinct legislature, date as day from to_infer where committee_id is null) d
    join mandates m
      on m.legislature = d.legislature
     and m.start_date <= d.day
     and (m.end_date is null or m.end_date >= d.day)
),
seated_groups as (
    select distinct
        c.legislature,
        c.day,
        g.group_acronym,
        coalesce(a.group_code, g.group_acronym) as group_code
    from covering c
    join group_memberships g
      on g.legislature = c.legislature
     and g.cadastro_id = c.cadastro_id
     and g.start_date <= c.day
     and (g.end_date is null or g.end_date >= c.day)
    left join seed_group_aliases a
      on a.legislature = g.legislature and a.alias = g.group_acronym
    where c.rn = 1 and c.is_effective
),
committee_covering as (
    select
        d.committee_id,
        d.day,
        m.cadastro_id,
        m.groups,
        s.status,
        s.membership,
        row_number() over (
            partition by d.committee_id, d.day, m.cadastro_id, m.legislature
            order by s.start_date desc, coalesce(s.end_date, date '9999-12-31') desc
        ) as rn
    from (select distinct committee_id, date as day from to_infer) d
    join stg_composicao_orgaos__committee_members m on m.committee_id = d.committee_id,
        unnest(m.situations) as u(s)
    where s.start_date <= d.day and (s.end_date is null or s.end_date >= d.day)
),
committee_groups as (
    select distinct c.committee_id, c.day, g.group_acronym
    from committee_covering c, unnest(c.groups) as u(g)
    where c.rn = 1
      and c.status = 'Ativo'
      and c.membership = 'Efetivo'
      and g.start_date <= c.day
      and (g.end_date is null or g.end_date >= c.day)
),
present_groups as (
    select t.vote_id, t.legislature, s.group_acronym, s.group_code
    from to_infer t
    join seated_groups s on s.legislature = t.legislature and s.day = t.date
    where t.committee_id is null
    union all
    select
        t.vote_id,
        t.legislature,
        g.group_acronym,
        coalesce(a.group_code, g.group_acronym) as group_code
    from to_infer t
    join committee_groups g on g.committee_id = t.committee_id and g.day = t.date
    left join seed_group_aliases a
      on a.legislature = t.legislature and a.alias = g.group_acronym
),
inferred as (
    select
        s.vote_id,
        s.legislature,
        s.group_acronym,
        'favour' as position,
        null::integer as deputies,
        true as inferred,
        s.group_code
    from present_groups s
    where not exists (
        select 1 from listed l
        where l.vote_id = s.vote_id and l.group_code = s.group_code
    )
),
all_rows as (
    select * from listed
    union all
    select * from inferred
)
select
    r.vote_id,
    r.legislature,
    v.body,
    r.group_code,
    r.group_acronym as group_code_raw,
    r.position,
    r.deputies,
    r.inferred
from all_rows r
join votes v using (vote_id)
order by r.vote_id, r.group_code, r.position, r.group_acronym
