select
    legislature,
    declaration_key,
    item_number,
    cadastro_id,
    category,
    source_list,
    item_id,
    type_code,
    description,
    entity,
    nature,
    activity_area,
    location,
    share,
    case paid_raw when 'S' then true when 'N' then false end as is_paid,
    try_cast(regexp_extract(start_date_raw, '^(\d{4}-\d{2}-\d{2})(T00:00:00)?$', 1) as date)
        as start_date,
    try_cast(regexp_extract(end_date_raw, '^(\d{4}-\d{2}-\d{2})(T00:00:00)?$', 1) as date)
        as end_date,
    start_date_raw,
    end_date_raw,
    date_raw
from stg_registo_interesses__items
join stg_registo_interesses__declarations using (declaration_key, legislature)
order by legislature, cadastro_id, declaration_key, item_number
