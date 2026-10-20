select
    q.legislature,
    q.question_id,
    a.cadastro_id,
    a.name as author_name,
    a.group_acronym
from stg_perguntas_requerimentos__questions q, unnest(q.authors) as u(a)
order by q.legislature, q.question_id, a.cadastro_id
