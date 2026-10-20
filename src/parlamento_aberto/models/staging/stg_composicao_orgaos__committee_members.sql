-- ComposicaoOrgaos Comissoes, one row per committee member record (HistoricoComposicao).
select
    cast(c.DetalheOrgao.idOrgao as bigint) as committee_id,
    trim(c.DetalheOrgao.nomeSigla) as committee_name,
    cast(m.depCadId as bigint) as cadastro_id,
    list_transform(
        m.depSituacao,
        s -> {
            'status': s.sioDes,
            'membership': s.sioTipMem,
            'start_date': cast(s.sioDtInicio as date),
            'end_date': cast(s.sioDtFim as date)
        }
    ) as situations,
    list_transform(
        m.depGP,
        g -> {
            'group_acronym': g.gpSigla,
            'start_date': cast(g.gpDtInicio as date),
            'end_date': cast(g.gpDtFim as date)
        }
    ) as groups,
    {legislature} as legislature,
    {source_file} as source_file
from read_json(
    '{data_dir}/composicao_orgaos/*/Comissoes*.ndjson',
    format = 'newline_delimited',
    filename = true,
    columns = {
        DetalheOrgao: 'STRUCT(idOrgao DOUBLE, nomeSigla VARCHAR)',
        HistoricoComposicao: 'STRUCT(
            depCadId DOUBLE,
            depSituacao STRUCT(
                sioDes VARCHAR, sioTipMem VARCHAR, sioDtInicio VARCHAR, sioDtFim VARCHAR
            )[],
            depGP STRUCT(gpSigla VARCHAR, gpDtInicio VARCHAR, gpDtFim VARCHAR)[]
        )[]'
    }
) c,
    unnest(c.HistoricoComposicao) as u(m)
order by committee_id, cadastro_id
