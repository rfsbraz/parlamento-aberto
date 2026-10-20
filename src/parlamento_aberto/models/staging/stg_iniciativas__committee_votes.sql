-- One row per committee vote record (Votacao inside IniEventos[].Comissao[]).
select
    cast(v.id as bigint) as vote_id,
    i.initiative_id,
    e.event_id,
    e.phase,
    e.phase_date,
    c.committee_id,
    c.committee_name,
    cast(v.data as date) as date,
    v.resultado as result,
    v.reuniao as meeting,
    coalesce(v.unanime = 'unanime', false) as unanimous,
    v.descricao as description,
    nullif(v.detalhe, '') as detail,
    v.ausencias as absent_groups,
    i.legislature,
    i.source_file
from stg_iniciativas__initiatives i,
    unnest(i.events) as u(e),
    unnest(e.committees) as k(c),
    unnest(c.votes) as w(v)
order by cast(v.id as bigint), i.initiative_id, e.event_id
