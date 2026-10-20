select
    cast(numSessao as integer) as session_number,
    cast(dataInicio as date) as start_date,
    cast(dataFim as date) as end_date,
    {legislature} as legislature,
    {source_file} as source_file
from read_json(
    '{data_dir}/informacao_base/*/sessoes_legislativas*.ndjson',
    format = 'newline_delimited',
    filename = true,
    columns = {numSessao: 'VARCHAR', dataInicio: 'VARCHAR', dataFim: 'VARCHAR'}
)
