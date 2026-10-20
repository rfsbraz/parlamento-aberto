-- Dates are parsed only when published as a full ISO date (V5 adds T00:00:00); the
-- published text stays in the _raw columns of stg_registo_interesses__declarations.
select
    legislature,
    declaration_key,
    cadastro_id,
    format_version,
    declaration_id,
    position,
    try_cast(regexp_extract(position_start_raw, '^(\d{4}-\d{2}-\d{2})(T00:00:00)?$', 1) as date)
        as position_start_date,
    try_cast(regexp_extract(position_changed_raw, '^(\d{4}-\d{2}-\d{2})(T00:00:00)?$', 1) as date)
        as position_changed_date,
    try_cast(regexp_extract(position_end_raw, '^(\d{4}-\d{2}-\d{2})(T00:00:00)?$', 1) as date)
        as position_end_date,
    position_start_raw,
    try_cast(regexp_extract(version_date_raw, '^(\d{4}-\d{2}-\d{2})$', 1) as date) as version_date,
    is_exclusive,
    items
from stg_registo_interesses__declarations
order by legislature, cadastro_id, declaration_key
