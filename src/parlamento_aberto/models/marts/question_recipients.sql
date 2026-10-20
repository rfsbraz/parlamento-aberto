select
    q.legislature,
    q.question_id,
    r.recipient,
    r.sent_date,
    coalesce(r.is_extended, false) as is_extended,
    coalesce(r.is_returned, false) as is_returned,
    coalesce(r.is_withdrawn, false) as is_withdrawn,
    coalesce(len(r.answer_dates), 0) as answer_count,
    list_min(r.answer_dates) as first_answer_date
from stg_perguntas_requerimentos__questions q, unnest(q.recipients) as u(r)
order by q.legislature, q.question_id, r.recipient
