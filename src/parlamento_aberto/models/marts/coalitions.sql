select
    c.legislature,
    c.coalition,
    c.ballot_acronym,
    c.coalition_name,
    c.group_code,
    g.name as group_name,
    c.source_url,
    c.election_url,
    c.note
from seed_coalitions c
left join parliamentary_groups g
    on g.legislature = c.legislature and g.group_acronym = c.group_code
order by c.legislature, c.coalition, c.ballot_acronym, c.group_code
