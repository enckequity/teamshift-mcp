# MCP quality tooling

Reuse the official modelcontextprotocol/conformance CLI with an exact package pin and lockfile.
Publish DISCLOSURE.md before publishing scanner/conformance results. Keep source/package-only
static review separate from authorized protocol execution; never start candidate server code,
install its hooks, use customer credentials, or call arbitrary public endpoints to reach a quota.

Use maintained local static-analysis and advisory tooling. Disable telemetry/provider analyzers;
private inputs require offline advisory databases. Missing tools/databases, skipped checks and
fixture runs are not live acceptance. Never claim 100 servers from 100 configurations or mutations.
No Actions. Record actual scenario counts, versions, source digests, scope and untested gates.
