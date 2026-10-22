-- Deputies elected per ballot list and electoral circle, 1979 to 1991, from the CNE copies of
-- the lists published in the Diário da República; seed written by scripts/cne_elected.py.
-- Nothing is computed here.
select
    legislature,
    cast(election_date as date) as election_date,
    circle_code,
    circle_name,
    ballot_acronym,
    cast(list_position as integer) as list_position,
    published_name,
    cast(cadastro_id as bigint) as cadastro_id,
    match,
    source_url
from seed_ballot_list_elected
order by election_date, circle_code, ballot_acronym, list_position
