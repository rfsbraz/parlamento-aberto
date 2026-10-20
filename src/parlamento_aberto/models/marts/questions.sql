-- sent_date is null and sent_date_invalid true when the published DataEnvio does not
-- parse or its year falls outside the legislature's years (an open legislature runs
-- to today). The published value stays in sent_date_raw.
with checked as (
    select
        q.*,
        try_cast(q.sent_date_raw as date) as parsed,
        q.sent_date_raw is not null and coalesce(
            year(try_cast(q.sent_date_raw as date)) not between year(l.start_date)
                and year(coalesce(l.end_date, current_date)),
            true
        ) as is_invalid
    from stg_perguntas_requerimentos__questions q
    left join legislatures l using (legislature)
)
select
    legislature,
    question_id,
    question_type,
    recipient_category,
    number,
    session_number,
    subject,
    entry_date,
    case when not is_invalid then parsed end as sent_date,
    sent_date_raw,
    is_invalid as sent_date_invalid,
    document_url,
    coalesce(len(authors), 0) as author_count,
    coalesce(len(recipients), 0) as recipient_count,
    cast(
        coalesce(list_sum(list_transform(recipients, r -> coalesce(len(r.answer_dates), 0))), 0)
        + coalesce(question_level_answers, 0) as bigint
    ) as answer_count
from checked
order by legislature, question_id
