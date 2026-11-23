select
    legislature,
    event_id,
    start_date,
    start_time,
    end_date,
    end_time,
    all_day,
    section,
    theme,
    body,
    group_code,
    title,
    subtitle,
    location,
    text,
    link,
    meeting_number
from stg_agenda_parlamentar__events
where legislature = (select legislature from legislatures where end_date is null)
order by start_date, start_time, event_id
