-- Constituinte, II and III come from the older XML-shaped files (camelCase keys, string ids);
-- every other legislature uses the current shape (PascalCase keys).
select
    cast(cast(coalesce(json ->> 'CadId', json ->> 'cadId') as double) as bigint) as cadastro_id,
    coalesce(json ->> 'CadNomeCompleto', json ->> 'cadNomeCompleto') as full_name,
    cast(coalesce(json ->> 'CadDtNascimento', json ->> 'cadDtNascimento') as date) as birth_date,
    coalesce(json ->> 'CadSexo', json ->> 'cadSexo') as sex,
    coalesce(json ->> 'CadProfissao', json ->> 'cadProfissao') as profession,
    {legislature} as legislature,
    {source_file} as source_file
from read_json_objects(
    '{data_dir}/registo_biografico/*/*/*.json',
    format = 'auto',
    filename = true
)
