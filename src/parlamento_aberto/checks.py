"""Data checks on a built database that tests and the release step can share."""

import duckdb


def committee_votes_without_composition(con: duckdb.DuckDBPyConnection) -> list[tuple[int, int]]:
    """(committee_id, vote_id) for unanimous committee votes that need inferred rows (no
    favour, against or abstention listed) in a committee with no members in ComposicaoOrgaos:
    no record, or a record with an empty HistoricoComposicao. Those votes would
    silently get no group rows."""
    return con.sql(
        """
        select v.committee_id, v.vote_id
        from votes v
        where v.committee_id is not null
          and v.unanimous
          and not exists (
              select 1 from vote_group_positions p
              where p.vote_id = v.vote_id and not p.inferred and p.position <> 'absent'
          )
          and not exists (
              select 1 from stg_composicao_orgaos__committee_members m
              where m.committee_id = v.committee_id
          )
        order by v.committee_id, v.vote_id
        """
    ).fetchall()
