-- One row per plenary meeting and person in its attendance list (#71).
-- Matched to cadastro_id on legislature, exact parliamentary name and group: the group
-- as published or its alias must be one of the person's groups (DepGP) in that
-- legislature. Never across legislatures, because some names belong to different people
-- in different legislatures. A row matching no one, or more than one person, keeps a
-- null cadastro_id, and the tests fail on it.
-- category comes from seed_attendance_codes. A code with pending_days (FA) is pending while
-- the meeting is less than pending_days old on source_updated, the date the AR file was
-- last fetched with changes (sources.lock.json), and unclassified after that, never
-- unjustified. An unseeded code, or a pending code without a fetched date, stops the build.
with fetched as (
    select
        split_part(key, '/', 2) as legislature,
        cast(value ->> 'fetched' as date) as source_updated
    from read_text('{data_dir}/_meta/sources.lock.json'), json_each(content)
    where key like 'composicao_orgaos/%'
),
aliased as (
    select s.*, coalesce(a.group_code, s.group_acronym) as group_code
    from stg_composicao_orgaos__plenary_attendance s
    left join seed_group_aliases a
      on a.legislature = s.legislature and a.alias = s.group_acronym
),
candidates as (
    select s.*, d.cadastro_id as candidate
    from aliased s
    left join stg_informacao_base__deputies d
      on d.legislature = s.legislature
     and d.parliamentary_name = s.parliamentary_name
     and list_has_any(
         list_transform(d.groups, g -> g.group_acronym), [s.group_acronym, s.group_code]
     )
),
matched as (
    select
        legislature,
        meeting_id,
        meeting_number,
        session_number,
        meeting_date,
        meeting_type,
        parliamentary_name,
        group_code,
        group_acronym,
        code,
        case when count(distinct candidate) = 1 then any_value(candidate) end as cadastro_id
    from candidates
    group by all
),
classified as (
    select
        m.*,
        case
            when c.code is null
                then error('attendance code not in seed_attendance_codes: ' || m.code)
            when c.pending_days is null then c.category
            when f.source_updated is null
                then error(
                    'no fetched date in sources.lock.json for composicao_orgaos/' || m.legislature
                )
            when f.source_updated - m.meeting_date < c.pending_days then c.category
            else 'unclassified'
        end as category,
        f.source_updated
    from matched m
    left join seed_attendance_codes c on c.code = m.code
    left join fetched f on f.legislature = m.legislature
)
select
    legislature,
    meeting_id,
    meeting_number,
    session_number,
    meeting_date,
    meeting_type,
    meeting_type in ('Solene', 'Comemorativa') as is_ceremonial,
    cadastro_id,
    parliamentary_name,
    group_code,
    group_acronym as group_code_raw,
    code,
    category,
    category = 'pending' as is_pending,
    source_updated
from classified
order by legislature, meeting_date, meeting_id, cadastro_id
