-- Ordered: a plain insert-ordered read of every record file runs out of memory.
select
    cast(IniId as bigint) as initiative_id,
    cast(IniNr as integer) as number,
    IniTipo as type_code,
    IniDescTipo as type,
    cast(IniSel as integer) as session_number,
    IniTitulo as title,
    IniLinkTexto as text_url,
    IniAutorOutros.sigla as author_kind_code,
    IniAutorOutros.nome as author_kind,
    IniAutorOutros.iniAutorComissao as author_committee,
    list_transform(
        IniAutorDeputados,
        a -> {
            'cadastro_id': cast(a.idCadastro as bigint),
            'name': a.nome,
            'group_acronym': a.GP
        }
    ) as author_deputies,
    list_transform(IniAutorGruposParlamentares, a -> a.GP) as author_groups,
    list_transform(
        IniEventos,
        e -> {
            'event_id': cast(e.EvtId as bigint),
            'phase': e.Fase,
            'phase_date': cast(e.DataFase as date),
            'votes': e.Votacao,
            'committees': list_transform(
                e.Comissao,
                c -> {
                    'committee_id': cast(c.IdComissao as bigint),
                    'committee_name': trim(c.Nome),
                    'votes': c.Votacao
                }
            )
        }
    ) as events,
    {legislature} as legislature,
    {source_file} as source_file
from read_json(
    '{data_dir}/iniciativas/*/*/*.json',
    format = 'auto',
    filename = true,
    columns = {
        IniId: 'VARCHAR',
        IniNr: 'VARCHAR',
        IniTipo: 'VARCHAR',
        IniDescTipo: 'VARCHAR',
        IniSel: 'VARCHAR',
        IniTitulo: 'VARCHAR',
        IniLinkTexto: 'VARCHAR',
        IniAutorOutros: 'STRUCT(sigla VARCHAR, nome VARCHAR, iniAutorComissao VARCHAR)',
        IniAutorDeputados: 'STRUCT(idCadastro VARCHAR, nome VARCHAR, GP VARCHAR)[]',
        IniAutorGruposParlamentares: 'STRUCT(GP VARCHAR)[]',
        IniEventos: 'STRUCT(
            EvtId VARCHAR,
            Fase VARCHAR,
            DataFase VARCHAR,
            Votacao STRUCT(
                id VARCHAR,
                data VARCHAR,
                resultado VARCHAR,
                reuniao VARCHAR,
                tipoReuniao VARCHAR,
                unanime VARCHAR,
                descricao VARCHAR,
                detalhe VARCHAR,
                ausencias VARCHAR[]
            )[],
            Comissao STRUCT(
                IdComissao VARCHAR,
                Nome VARCHAR,
                Votacao STRUCT(
                    id VARCHAR,
                    data VARCHAR,
                    resultado VARCHAR,
                    reuniao VARCHAR,
                    unanime VARCHAR,
                    descricao VARCHAR,
                    detalhe VARCHAR,
                    ausencias VARCHAR[]
                )[]
            )[]
        )[]'
    }
)
order by initiative_id
