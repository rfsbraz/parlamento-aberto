-- Deputies named in a vote detail, usually because they voted apart from their group,
-- and deputies named as absent in ausencias on votes without a detail.
-- Matched to cadastro_id by parliamentary name (ignoring case and spacing) and group
-- within the vote's legislature, accepting the published code or its alias. Indep and Ninsc are not groups, so those names are
-- matched on the name alone. A name with no match, or more than one, stays null.
with named as (
    select distinct v.vote_id, v.legislature, v.body, i.position, i.name, i.group_acronym
    from votes v
    join stg_votes__detail_items i on i.detail = v.detail
    where i.kind = 'deputy'
    union
    -- Votes without a detail can name absent deputies in ausencias as "Name (GROUP)".
    select
        v.vote_id,
        v.legislature,
        v.body,
        'absent' as position,
        trim(regexp_extract(g, '^(.+) \([^()]+\)$', 1)) as name,
        regexp_extract(g, '^.+ \(([^()]+)\)$', 1) as group_acronym
    from votes v, unnest(v.absent_groups) as u(g)
    where v.detail is null and regexp_matches(g, '^.+ \([^()]+\)$')
),
aliased as (
    select n.*, coalesce(a.group_code, n.group_acronym) as group_code
    from named n
    left join seed_group_aliases a
      on a.legislature = n.legislature and a.alias = n.group_acronym
),
candidates as (
    select n.*, d.cadastro_id as candidate
    from aliased n
    left join stg_informacao_base__deputies d
      on d.legislature = n.legislature
     and lower(regexp_replace(trim(d.parliamentary_name), '\s+', ' ', 'g'))
         = lower(regexp_replace(trim(n.name), '\s+', ' ', 'g'))
     and (
         n.group_acronym in ('Indep', 'Ninsc')
         or list_has_any(
             list_transform(d.groups, g -> g.group_acronym), [n.group_acronym, n.group_code]
         )
     )
)
select
    vote_id,
    legislature,
    body,
    position,
    name,
    group_code,
    group_acronym as group_code_raw,
    case when count(distinct candidate) = 1 then any_value(candidate) end as cadastro_id,
    count(distinct candidate)::integer as candidates
from candidates
group by vote_id, legislature, body, position, name, group_code, group_acronym
order by vote_id, name
