-- One row per event (phase) of an initiative. oev_id is unique; EvtId repeats within an
-- initiative. phase drops the trailing newline a few AR phase names carry.
select
    i.legislature,
    i.initiative_id,
    e.event_id,
    e.oev_id,
    e.phase_code,
    rtrim(e.phase, e' \n\r\t') as phase,
    e.phase_date,
    row_number() over (
        partition by i.legislature, i.initiative_id order by e.phase_date, e.oev_id
    ) as event_order,
    e.observation
from stg_iniciativas__initiatives i, unnest(i.events) as u(e)
order by i.legislature, i.initiative_id, event_order
