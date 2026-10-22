-- Seats per ballot list and electoral circle, as published by the CNE (1979 to 2005) and the
-- SGMAI (2009 on); seed written by scripts/mai_list_seats.py. Nothing is computed here.
select
    legislature,
    cast(election_date as date) as election_date,
    circle_code,
    circle_name,
    ballot_acronym,
    cast(seats as integer) as seats,
    source_url
from seed_ballot_list_seats
order by election_date, circle_code, ballot_acronym
