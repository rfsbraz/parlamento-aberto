-- One row per vote record in an initiative event. The same vote id can appear on
-- several initiatives voted together; votes deduplicates.
select
    cast(v.id as bigint) as vote_id,
    i.initiative_id,
    e.event_id,
    e.phase,
    e.phase_date,
    cast(v.data as date) as date,
    v.resultado as result,
    v.reuniao as meeting,
    v.tipoReuniao as meeting_type,
    coalesce(v.unanime = 'unanime', false) as unanimous,
    v.descricao as description,
    nullif(v.detalhe, '') as detail,
    v.ausencias as absent_groups,
    i.legislature,
    i.source_file
from stg_iniciativas__initiatives i,
    unnest(i.events) as u(e),
    unnest(e.votes) as w(v)
order by cast(v.id as bigint), i.initiative_id, e.event_id
