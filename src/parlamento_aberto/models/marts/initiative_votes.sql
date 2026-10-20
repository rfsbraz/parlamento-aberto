-- Plenary and committee votes, with the body they were held in.
select distinct
    vote_id,
    initiative_id,
    initiative_legislature,
    body,
    event_id,
    phase,
    phase_date
from (
    select vote_id, initiative_id, legislature as initiative_legislature, 'plenary' as body,
        event_id, phase, phase_date
    from stg_iniciativas__votes
    union all
    select vote_id, initiative_id, legislature as initiative_legislature,
        committee_name as body, event_id, phase, phase_date
    from stg_iniciativas__committee_votes
)
order by vote_id, initiative_id, event_id
