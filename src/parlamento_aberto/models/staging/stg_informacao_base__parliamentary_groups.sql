select
    sigla as group_acronym,
    nome as name,
    {legislature} as legislature,
    {source_file} as source_file
from read_json(
    '{data_dir}/informacao_base/*/grupos_parlamentares*.ndjson',
    format = 'newline_delimited',
    filename = true,
    columns = {sigla: 'VARCHAR', nome: 'VARCHAR'}
)
