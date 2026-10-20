-- Deputies and groups as listed on the initiative. Initiatives from anyone else
-- (Governo, regional assemblies, committees, citizens) get one 'other' row.
with deputy_authors as (
    select
        i.legislature,
        i.initiative_id,
        'deputy' as author_type,
        a.cadastro_id,
        a.group_acronym,
        a.name
    from stg_iniciativas__initiatives i, unnest(i.author_deputies) as u(a)
),
group_authors as (
    select
        i.legislature,
        i.initiative_id,
        'group' as author_type,
        null::bigint as cadastro_id,
        g as group_acronym,
        null::varchar as name
    from stg_iniciativas__initiatives i, unnest(i.author_groups) as u(g)
),
other_authors as (
    select
        legislature,
        initiative_id,
        'other' as author_type,
        null::bigint as cadastro_id,
        null::varchar as group_acronym,
        coalesce(author_committee, author_kind) as name
    from stg_iniciativas__initiatives
    where author_kind_code not in ('D', 'G')
)
select * from deputy_authors
union all
select * from group_authors
union all
select * from other_authors
order by legislature, initiative_id, author_type, cadastro_id, group_acronym
