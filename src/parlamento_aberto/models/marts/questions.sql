select
    legislature,
    question_id,
    question_type,
    recipient_category,
    number,
    session_number,
    subject,
    entry_date,
    sent_date,
    document_url,
    coalesce(len(authors), 0) as author_count,
    coalesce(len(recipients), 0) as recipient_count,
    cast(
        coalesce(list_sum(list_transform(recipients, r -> coalesce(len(r.answer_dates), 0))), 0)
        + coalesce(question_level_answers, 0) as bigint
    ) as answer_count
from stg_perguntas_requerimentos__questions
order by legislature, question_id
