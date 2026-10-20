-- ComposicaoOrgaos Plenario Reunioes, one row per person in a plenary meeting's attendance
-- list. Meetings without a list (all of Constituinte to IV, all but one in V) add no rows.
-- The free-text absence reason is never read: the column list below leaves it out (#71).
select
    cast(r.Reuniao.reuId as bigint) as meeting_id,
    cast(r.Reuniao.reuNumero as integer) as meeting_number,
    cast(r.Reuniao.selNumero as integer) as session_number,
    cast(r.Presencas.dtReuniao as date) as meeting_date,
    r.Presencas.tipoReuniao as meeting_type,
    p.nomeDeputado as parliamentary_name,
    p.siglaGrupo as group_acronym,
    p.siglaFalta as code,
    {legislature} as legislature,
    {source_file} as source_file
from read_json(
    '{data_dir}/composicao_orgaos/*/Plenario.Reunioes.ndjson',
    format = 'newline_delimited',
    filename = true,
    columns = {
        Reuniao: 'STRUCT(reuId DOUBLE, reuNumero VARCHAR, selNumero VARCHAR)',
        Presencas: 'STRUCT(
            dtReuniao VARCHAR,
            tipoReuniao VARCHAR,
            presencas STRUCT(nomeDeputado VARCHAR, siglaGrupo VARCHAR, siglaFalta VARCHAR)[]
        )'
    }
) r,
    unnest(r.Presencas.presencas) as u(p)
order by legislature, meeting_date, meeting_id, parliamentary_name
