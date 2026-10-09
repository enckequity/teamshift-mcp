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

The official active server suite requires its fixed synthetic tool/prompt/resource fixtures.
Reports label that contract and do not certify general server compliance. Missing fixture
names are not general protocol violations. Native stdio and mediated HTTP scope remain
distinct; never claim native HTTP from an adapter or count source manifests as tested servers.

`node --test test/pagination-live.test.mjs` exercises four owned synthetic socket-level
pagination cases through the pinned SDK. No candidate server is started or counted.
The fixture closes only its own listener/transports; no provider/tool calls or secrets.

## Native stdio execution

`npm run build:native` verifies the vendored upstream manifest and bundles the pinned SDK.
`npm run test:native` uses an owned synthetic stdio fixture; it is not a real-server count.
`native_stdio.py` accepts explicitly reviewed immutable source/installed-dependency receipts
for baseline initialize, ping and tools/list only. It never invokes candidate tools. Require
the exact runtime, bundle and Bubblewrap hashes, a qualified Linux user cgroup, private
filesystem/PID/network namespaces and proven timeout/child cleanup before admission.
No install hooks, inherited credentials, host HOME/drives/sockets, public endpoints or
fallback containment. Record launcher PID/start ticks and unique unit intent before work;
acceptance reports become visible only after exact-unit cleanup is verified. Keep candidate
receipts/results private under DISCLOSURE.md. Failed startup and static reviews do not count
as executed protocol interactions. HTTP/OAuth/SSE and fixed-fixture scope stay separately labeled.
