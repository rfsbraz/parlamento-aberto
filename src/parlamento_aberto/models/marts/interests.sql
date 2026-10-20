-- One row per declared item from either source, keyed like interest_declarations. The first
-- columns are those of the AR-only mart, in the same order; paid_raw and the EpT-only
-- columns follow. EpT cadastro_id comes from seed_ept_holders and EpT rows are
-- kept for XVI and XVII only, as in interest_declarations.
with ar as (
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
        date_raw,
        'ar_open_data' as source,
        paid_raw,
        null::varchar as entity_nipc,
        null::varchar as beneficiary,
        null::varchar as beneficiary_company,
        null::varchar as share_value_eur,
        null::varchar as share_pct,
        null::varchar as share_holder,
        null::boolean as is_professional_secrecy,
        null::varchar as observation
    from stg_registo_interesses__items
    join stg_registo_interesses__declarations using (declaration_key, legislature)
),

ept as (
    select
        i.legislature,
        i.declaration_key,
        i.item_number,
        h.cadastro_id,
        i.category,
        i.source_list,
        i.item_id,
        i.type_code,
        i.description,
        i.entity,
        i.nature,
        i.activity_area,
        i.location,
        i.share,
        i.is_paid,
        i.start_date,
        i.end_date,
        i.start_date_raw,
        i.end_date_raw,
        i.date_raw,
        i.source,
        i.paid_raw,
        i.entity_nipc,
        i.beneficiary,
        i.beneficiary_company,
        i.share_value_eur,
        i.share_pct,
        i.share_holder,
        i.is_professional_secrecy,
        i.observation
    from stg_ept_registo_interesses__items as i
    join stg_ept_registo_interesses__declarations as d using (declaration_key, legislature)
    left join seed_ept_holders as h using (ept_holder_id)
    where i.legislature in ('XVI', 'XVII')
)

select * from ar
union all
select * from ept
order by legislature, cadastro_id, declaration_key, item_number
