-- One row per intervention. AR publishes some records with every key null; they are
-- counted in staging and dropped here.
select
    legislature,
    intervention_id,
    session_number,
    meeting_date,
    intervention_type,
    session_phase,
    debate_id,
    debate,
    debate_phase,
    activity_id,
    summary,
    abstract,
    case
        when cadastro_id is not null then 'deputy'
        when government_member_name is not null then 'government'
        when guest_name is not null then 'guest'
    end as speaker_kind,
    cadastro_id,
    speaker_name,
    group_acronym,
    speaker_role,
    government_member_name,
    government_member_role,
    government,
    guest_name,
    guest_role,
    publication_type,
    publication_number,
    publication_date,
    pages,
    diary_url
from stg_intervencoes__interventions
where intervention_id is not null
order by legislature, intervention_id
