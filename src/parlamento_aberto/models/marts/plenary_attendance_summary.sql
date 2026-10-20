-- One row per legislature, person, group and kind of sitting in plenary_attendance (#71):
-- the meetings in those attendance lists and how many fall in each category, so any rate
-- can be computed. Solemn and commemorative sittings (is_ceremonial) get their own row, so
-- a rate can leave them out. A person who changed group in a legislature has a row per group.
select
    legislature,
    cadastro_id,
    arg_max(parliamentary_name, meeting_date) as parliamentary_name,
    group_code,
    is_ceremonial,
    count(*)::integer as meetings,
    count(*) filter (where category = 'present')::integer as present,
    count(*) filter (where category = 'other_body_or_mission')::integer as other_body_or_mission,
    count(*) filter (where category = 'justified')::integer as justified,
    count(*) filter (where category = 'missed_quorum_vote')::integer as missed_quorum_vote,
    count(*) filter (where category = 'pending')::integer as pending,
    count(*) filter (where category = 'unclassified')::integer as unclassified,
    count(*) filter (where category = 'unjustified')::integer as unjustified,
    min(meeting_date) as first_meeting_date,
    max(meeting_date) as last_meeting_date
from plenary_attendance
group by legislature, cadastro_id, group_code, is_ceremonial
order by legislature, cadastro_id, group_code, is_ceremonial
