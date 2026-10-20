-- One row per vote id. A vote on several initiatives voted together is published on
-- each of them; the copies are identical, so the first by source file is kept.
-- The legislature is the one the vote date falls in, which is not always the
-- legislature of the initiative (some initiatives are voted after it ends).
with records as (
    select vote_id, 'iniciativas' as source, date, result, meeting, meeting_type, unanimous,
        description, detail, absent_groups, source_file
    from stg_iniciativas__votes
    union all
    select vote_id, 'atividades' as source, date, result, meeting, meeting_type, unanimous,
        description, detail, absent_groups, source_file
    from stg_atividades__votes
),
ranked as (
    select
        *,
        row_number() over (partition by vote_id order by source_file) as rn,
        count(*) over (partition by vote_id) as source_records
    from records
)
select
    r.vote_id,
    l.legislature,
    r.date,
    r.source,
    r.result,
    r.unanimous,
    r.meeting,
    r.meeting_type,
    r.description,
    r.detail,
    r.absent_groups,
    r.source_records
from ranked r
left join legislatures l
  on r.date >= l.start_date and r.date <= coalesce(l.end_date, date '9999-12-31')
where r.rn = 1
order by r.vote_id
