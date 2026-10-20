select
    legislature,
    initiative_id,
    number,
    type_code,
    type,
    session_number,
    title,
    author_kind,
    (select min(e.phase_date) from unnest(events) as u(e)) as first_event_date,
    text_url
from stg_iniciativas__initiatives
order by legislature, initiative_id
