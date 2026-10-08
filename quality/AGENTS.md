# MCP quality tooling

Reuse the official modelcontextprotocol/conformance CLI with an exact package pin and lockfile.
Publish DISCLOSURE.md before publishing scanner/conformance results. Keep source/package-only
static review separate from authorized protocol execution; never start candidate server code,
install its hooks, use customer credentials, or call arbitrary public endpoints to reach a quota.

Use maintained local static-analysis and advisory tooling. Disable telemetry/provider analyzers;
private inputs require offline advisory databases. Missing tools/databases, skipped checks and
fixture runs are not live acceptance. Never claim 100 servers from 100 configurations or mutations.
No Actions. Record actual scenario counts, versions, source digests, scope and untested gates.


## Commands and boundaries

`npm ci --ignore-scripts`; pinned engines and snapshot layout: README.md.
`MCP_QUALITY_SEMGREP=/absolute/semgrep npm test` is required (no missing-engine skip).
`npm audit`; validate rules with pinned Semgrep. Protocol commands in README.md require
explicit numeric loopback ownership. Supplemental pagination only calls tools/list through SDK;
record continuation as unexercised for one-page responses. Mac static scans deny network with
sandbox-exec and refuse fallback. Never publish private engine/protocol logs.

Stage every source byte without collisions; retain original hashes and renamed path mapping.
Database staging preserves exact manifest paths, rejects unmanifested bytes, and requires dated
snapshots. Missing/malformed engine output is incomplete. Own child process groups are cleaned
by the launcher on timeout/cancellation; long-lived fixtures need exact PID/start/launcher ledger.
Upstream pinned source and license notice remain intact; adapter changes update its trusted hash.
