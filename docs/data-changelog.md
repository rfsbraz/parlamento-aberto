# Data changelog

Changes to the published marts that consumers should know about. The `## Unreleased` section goes into the next release as its `CHANGELOG.md`.

- Schema changes: one line each, for example `- schema: votes gains committee_id.` Bump `schema_version` in `src/parlamento_aberto/models/schema.yml` too, the major for a breaking change.
- Row drops: a mart that loses more than 5% of its rows in a legislature, against the previous release, blocks the release. If the drop is right, acknowledge it with `- drift: <mart> <legislature>: why`, using `all` for marts without a legislature column. A line the previous release already carried does not count again.

After a release, move the released lines under a heading with its tag.

## Unreleased

- schema: first release, schema 1.0.0.
