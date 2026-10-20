select
    cast(DepCadId as bigint) as cadastro_id,
    cast(DepId as bigint) as deputy_id,
    DepNomeCompleto as full_name,
    DepNomeParlamentar as parliamentary_name,
    cast(DepCPId as integer) as circle_id,
    DepCPDes as circle_name,
    list_transform(
        DepSituacao,
        s -> {
            'situation': s.sioDes,
            'start_date': cast(s.sioDtInicio as date),
            'end_date': cast(s.sioDtFim as date)
        }
    ) as situations,
    list_transform(
        DepGP,
        g -> {
            'group_id': cast(g.gpId as bigint),
            'group_acronym': g.gpSigla,
            'start_date': cast(g.gpDtInicio as date),
            'end_date': cast(g.gpDtFim as date)
        }
    ) as groups,
    {legislature} as legislature,
    {source_file} as source_file
from read_json(
    '{data_dir}/informacao_base/*/deputados*.ndjson',
    format = 'newline_delimited',
    filename = true,
    columns = {
        DepCadId: 'DOUBLE',
        DepId: 'DOUBLE',
        DepNomeCompleto: 'VARCHAR',
        DepNomeParlamentar: 'VARCHAR',
        DepCPId: 'DOUBLE',
        DepCPDes: 'VARCHAR',
        DepSituacao: 'STRUCT(sioDes VARCHAR, sioDtInicio VARCHAR, sioDtFim VARCHAR)[]',
        DepGP: 'STRUCT(gpId DOUBLE, gpSigla VARCHAR, gpDtInicio VARCHAR, gpDtFim VARCHAR)[]'
    }
)
