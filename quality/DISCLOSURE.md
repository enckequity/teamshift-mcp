# MCP quality tooling: reporting and disclosure

This policy applies to TeamShift's MCP conformance wrapper and source/package scanner in
`tools/mcp_quality`. It does not authorize testing a third party's running server or account.
Run protocol tests only against systems you own or have explicit permission to test. Static
source review never authorizes executing candidate code, installing its hooks, or using its
credentials. Do not send private package names, source, or data to an advisory service without
permission; use an offline advisory database for private inputs.

Report a suspected issue privately to **team@teamshift.io**, with the affected tool version,
source revision, reproduction using synthetic data, and the relevant finding identifier.
Do not include credentials, customer records, live tokens, or exploit a system to strengthen a
report. A scanner match is an observation for review, not proof of exploitation or a safe/unsafe
certificate. Missing checks, unavailable databases, timeouts, and skipped scenarios are unknown.

For an upstream issue, use the affected project's own private reporting channel and policy.
Avoid posting unreviewed accusations, exploit details, credentials, or identifiable third-party
findings in public issues. Public results must state the authorized scope, exact source and tool
versions, actual tests run, failures, and untested boundaries. Fictional fixtures must be labeled
as fixtures; repeated configurations do not count as independently tested servers.

This document is a reporting procedure, not a contract, response-time guarantee, bug bounty,
legal safe harbor, or permission to bypass a system's controls. No payment is offered.
