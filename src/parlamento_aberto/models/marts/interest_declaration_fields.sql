-- One row per visible cell of tabs 2 and 3 of an EpT declaration of the XVI and the XVII
-- (#148), by position. The holder NIF is never stored and any 9-digit number is [removido].
select
    f.legislature,
    f.declaration_key,
    h.cadastro_id,
    f.field_number,
    f.tab,
    f.path,
    f.section,
    f.column_name,
    f.label,
    f.value,
    f.source
from stg_ept_registo_interesses__fields as f
join stg_ept_registo_interesses__declarations as d using (declaration_key, legislature)
left join seed_ept_holders as h using (ept_holder_id)
where f.legislature in ('XVI', 'XVII')
order by f.legislature, h.cadastro_id, f.declaration_key, f.field_number
