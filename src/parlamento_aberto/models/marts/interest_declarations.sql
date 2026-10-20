-- One row per declaration from either source: the AR open data (XI to XV) and the EpT
-- (XVI and XVII). The first columns are those of the AR-only mart, in the same order; the
-- EpT columns follow and are null on AR rows. No cross-source dedup: EpT rows are kept only
-- for XVI and XVII, where the AR publishes no register.
-- AR dates are parsed only when published as a full ISO date (V5 adds T00:00:00); the
-- published text stays in the _raw columns of stg_registo_interesses__declarations. EpT
-- dates are already the Lisbon day in staging.
with ar as (
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
        try_cast(regexp_extract(version_date_raw, '^(\d{4}-\d{2}-\d{2})$', 1) as date)
            as version_date,
        is_exclusive,
        items,
        'ar_open_data' as source,
        format_version as source_format,
        declaration_id as source_declaration_id,
        null::bigint as ept_holder_id,
        null::varchar as declaration_nature,
        null::varchar as declaration_state,
        null::bigint as supersedes_declaration_id,
        null::bigint as superseded_by_declaration_id,
        null::bigint as chain_root_declaration_id,
        null::varchar as submitted_at,
        null::date as submitted_date,
        null::boolean as is_current
    from stg_registo_interesses__declarations
),

ept as (
    select
        d.legislature,
        d.declaration_key,
        h.cadastro_id,
        d.format_version,
        d.declaration_id,
        d.position,
        d.position_start_date,
        d.position_changed_date,
        d.position_end_date,
        d.position_start_raw,
        d.version_date,
        d.is_exclusive,
        d.items,
        d.source,
        d.source_format,
        d.source_declaration_id,
        d.ept_holder_id,
        d.declaration_nature,
        d.declaration_state,
        d.supersedes_declaration_id,
        d.superseded_by_declaration_id,
        d.chain_root_declaration_id,
        d.submitted_at,
        d.submitted_date,
        d.is_current
    from stg_ept_registo_interesses__declarations as d
    left join seed_ept_holders as h using (ept_holder_id)
    where d.legislature in ('XVI', 'XVII')
)

select * from ar
union all
select * from ept
order by legislature, cadastro_id, declaration_key
