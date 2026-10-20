-- One row per vote record (VotacaoDebate) on an activity, such as a vote of
-- condolence (VOT) or a motion (MOC).
select
    cast(v.id as bigint) as vote_id,
    a.Tipo as activity_type,
    a.DescTipo as activity_type_description,
    a.Numero as activity_number,
    a.Assunto as activity_subject,
    cast(v.data as date) as date,
    v.resultado as result,
    v.reuniao as meeting,
    v.tipoReuniao as meeting_type,
    coalesce(v.unanime = 'unanime', false) as unanimous,
    v.descricao as description,
    nullif(v.detalhe, '') as detail,
    v.ausencias as absent_groups,
    {legislature} as legislature,
    {source_file} as source_file
from read_json(
    '{data_dir}/atividades/*/AtividadesGerais.Atividades*.ndjson',
    format = 'newline_delimited',
    filename = true,
    columns = {
        Tipo: 'VARCHAR',
        DescTipo: 'VARCHAR',
        Numero: 'VARCHAR',
        Assunto: 'VARCHAR',
        VotacaoDebate: 'STRUCT(
            id VARCHAR,
            data VARCHAR,
            resultado VARCHAR,
            reuniao VARCHAR,
            tipoReuniao VARCHAR,
            unanime VARCHAR,
            descricao VARCHAR,
            detalhe VARCHAR,
            ausencias VARCHAR[]
        )[]'
    }
) a,
    unnest(a.VotacaoDebate) as u(v)
order by vote_id
