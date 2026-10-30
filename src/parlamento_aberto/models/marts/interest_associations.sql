-- One row per line of the EpT associations section (#148), for the XVI and the XVII, with
-- the item columns of the EpT rows of interests. Kept out of interests so it can be dropped
-- on its own.
select
    i.legislature,
    i.declaration_key,
    h.cadastro_id,
    i.item_number,
    i.category,
    i.source_list,
    i.description,
    i.entity,
    i.activity_area,
    i.location,
    i.paid_raw,
    i.start_date,
    i.end_date,
    i.start_date_raw,
    i.end_date_raw,
    i.entity_nipc,
    i.source
from stg_ept_registo_interesses__associations as i
join stg_ept_registo_interesses__declarations as d using (declaration_key, legislature)
left join seed_ept_holders as h using (ept_holder_id)
where i.legislature in ('XVI', 'XVII')
order by i.legislature, h.cadastro_id, i.declaration_key, i.item_number
