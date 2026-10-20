select distinct
    vote_id,
    initiative_id,
    legislature as initiative_legislature,
    event_id,
    phase,
    phase_date
from stg_iniciativas__votes
order by vote_id, initiative_id, event_id
