select
    cast(cast(Id as double) as bigint) as question_id,
    Tipo as question_type,
    ReqTipo as recipient_category,
    Nr as number,
    cast(Sessao as integer) as session_number,
    Assunto as subject,
    cast(DtEntrada as date) as entry_date,
    DataEnvio as sent_date_raw,
    Ficheiro as document_url,
    list_transform(
        Autores,
        a -> {
            'cadastro_id': cast(cast(a.idCadastro as double) as bigint),
            'name': a.nome,
            'group_acronym': a.GP
        }
    ) as authors,
    list_transform(
        Destinatarios,
        d -> {
            'recipient': d.nomeEntidade,
            'sent_date': cast(d.dataEnvio as date),
            'is_extended': d.prorrogado = 'S',
            'is_returned': d.devolvido = 'S',
            'is_withdrawn': d.retirado = 'S',
            'answer_dates': list_transform(d.respostas, r -> cast(r.dataResposta as date))
        }
    ) as recipients,
    len(RespostasSPerguntas) as question_level_answers,
    {legislature} as legislature,
    {source_file} as source_file
from read_json(
    '{data_dir}/perguntas_requerimentos/*/records*.ndjson',
    format = 'newline_delimited',
    filename = true,
    maximum_object_size = 100000000,
    columns = {
        Id: 'VARCHAR',
        Tipo: 'VARCHAR',
        ReqTipo: 'VARCHAR',
        Nr: 'VARCHAR',
        Sessao: 'VARCHAR',
        Assunto: 'VARCHAR',
        DtEntrada: 'VARCHAR',
        DataEnvio: 'VARCHAR',
        Ficheiro: 'VARCHAR',
        Autores: 'STRUCT(idCadastro VARCHAR, nome VARCHAR, GP VARCHAR)[]',
        Destinatarios: 'STRUCT(nomeEntidade VARCHAR, dataEnvio VARCHAR, prorrogado VARCHAR, devolvido VARCHAR, retirado VARCHAR, respostas STRUCT(dataResposta VARCHAR)[])[]',
        RespostasSPerguntas: 'STRUCT(dataResposta VARCHAR)[]'
    }
)
