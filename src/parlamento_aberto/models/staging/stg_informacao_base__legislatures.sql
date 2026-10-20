select
    cast(id as integer) as legislature_id,
    cast(dtini as date) as start_date,
    cast(dtfim as date) as end_date,
    {legislature} as legislature,
    {source_file} as source_file
from read_json(
    '{data_dir}/informacao_base/*/detalhe_legislatura*.ndjson',
    format = 'newline_delimited',
    filename = true,
    columns = {id: 'VARCHAR', sigla: 'VARCHAR', dtini: 'VARCHAR', dtfim: 'VARCHAR'}
)
