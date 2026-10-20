select
    cast(cpId as integer) as circle_id,
    cpDes as name,
    {legislature} as legislature,
    {source_file} as source_file
from read_json(
    '{data_dir}/informacao_base/*/circulos_eleitorais*.ndjson',
    format = 'newline_delimited',
    filename = true,
    columns = {cpId: 'DOUBLE', cpDes: 'VARCHAR'}
)
