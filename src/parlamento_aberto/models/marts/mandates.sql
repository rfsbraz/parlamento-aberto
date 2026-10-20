select
    d.legislature,
    d.cadastro_id,
    d.deputy_id,
    d.circle_id,
    s.situation,
    s.situation like 'Efetivo%' as is_effective,
    s.start_date,
    s.end_date
from stg_informacao_base__deputies d, unnest(d.situations) as u(s)
order by d.legislature, d.cadastro_id, s.start_date, s.situation
