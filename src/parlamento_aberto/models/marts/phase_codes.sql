-- seed_phase_codes as published, so initiative_events can be joined to an outcome.
select phase_code, phase, outcome, note
from seed_phase_codes
order by cast(phase_code as integer)
