select
    cast(CadId as bigint) as cadastro_id,
    CadNomeCompleto as full_name,
    cast(CadDtNascimento as date) as birth_date,
    CadSexo as sex,
    CadProfissao as profession,
    {legislature} as legislature,
    {source_file} as source_file
from read_json(
    '{data_dir}/registo_biografico/*/*/*.json',
    format = 'auto',
    filename = true,
    columns = {
        CadId: 'DOUBLE',
        CadNomeCompleto: 'VARCHAR',
        CadDtNascimento: 'VARCHAR',
        CadSexo: 'VARCHAR',
        CadProfissao: 'VARCHAR'
    }
)
