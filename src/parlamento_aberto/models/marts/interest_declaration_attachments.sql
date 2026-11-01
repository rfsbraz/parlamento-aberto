-- One row per attachment of an EpT declaration of the XVI and the XVII (#148). Metadata
-- only: the public API serves no file.
select
    a.legislature,
    a.declaration_key,
    h.cadastro_id,
    a.attachment_number,
    a.name,
    a.size_bytes,
    a.format,
    a.section_type,
    a.observations,
    a.source
from stg_ept_registo_interesses__attachments as a
join stg_ept_registo_interesses__declarations as d using (declaration_key, legislature)
left join seed_ept_holders as h using (ept_holder_id)
where a.legislature in ('XVI', 'XVII')
order by a.legislature, h.cadastro_id, a.declaration_key, a.attachment_number
