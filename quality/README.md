# MCP quality tools

Read [DISCLOSURE.md](DISCLOSURE.md) before testing or sharing results. This wrapper reuses
[official MCP conformance](https://github.com/modelcontextprotocol/conformance/tree/v0.1.16),
Semgrep and OSV Scanner. It does not implement a competing protocol test suite.

## Install the reviewed tools

Python 3.13+, Node 22+ and macOS with `sandbox-exec` are required for the demonstrated path.
Source scanning refuses to run without kernel network denial; other platforms are unverified.
From this directory:

```sh
npm ci --ignore-scripts
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Install the official [OSV Scanner v2.6.0 release](https://github.com/google/osv-scanner/releases/tag/v2.6.0)
and verify its published checksum. No candidate package installation or hooks are needed.
Semgrep 1.180.0, OSV 2.6.0, conformance 0.1.16, SDK 1.32.1 and tsx 4.23.15 are pinned.
The lockfile binds the npm dependency tree. SDK 1.32.1 includes the
[OAuth issuer-binding fix](https://github.com/advisories/GHSA-6qxp-vccf-f47h).

## Static source/package review

Prepare a dated offline advisory snapshot using official OSV ecosystem archives before
introducing private candidate source. OSV Scanner **2.6.0** consumes this exact layout:

```text
advisories/
  manifest.json
  osv-scalibr/
    npm/all.zip
    PyPI/all.zip
```

Include only the ecosystems needed for your lockfiles. Unsupported or missing ecosystem data
must be resolved before accepting a completed review. `manifest.json` contains a UTC
`downloaded_at` ISO timestamp and `files`, mapping each archive's relative path to its SHA256.
The exact file set is enforced and snapshots older than seven days are refused:

```json
{"downloaded_at":"2026-10-08T00:00:00Z","files":{"osv-scalibr/npm/all.zip":"<64-character archive SHA256>"}}
```

The timestamp is provenance supplied by the operator, not signed freshness attestation.
Download archives from `https://osv-vulnerabilities.storage.googleapis.com/<ecosystem>/all.zip`;
compute their actual hashes rather than using the example placeholder. The hidden
`--local-db-path` option is deliberately bound to reviewed OSV 2.6.0 behavior.

```sh
python3 mcp_quality.py scan-source /absolute/candidate \
  --semgrep "$PWD/.venv/bin/semgrep" --osv /absolute/osv-scanner \
  --database /absolute/advisories --output /private/new-review.json
```

Only regular files are copied; symlinks, special files, empty sources, oversized trees and
malformed manifests fail. Candidate ignore/config files are renamed without replacing any
source bytes, with original-to-staged names recorded. Advisory paths remain exact. Neither
scanner receives inherited credential variables, executes candidate hooks, nor has network access.
Rules flag instruction overrides, invisible controls, execution and egress for human review;
these observations are not automatically vulnerabilities. Package lifecycle hooks are reported,
and an edit-distance heuristic flags confusion with a small reviewed name set. It is not proof
of a typosquat. OSV matches lockfile/package versions against the offline snapshot.

## Authorized local protocol checks

The official server suite may invoke advertised tools. Use only an endpoint you own and
are authorized to exercise with synthetic data, never a customer or arbitrary public endpoint:

```sh
python3 mcp_quality.py conformance --authorized \
  --url http://127.0.0.1:3000/mcp --output /private/new-server.json
python3 mcp_quality.py client-conformance --authorized --output /private/new-client.json
```

The first command runs the official active server suite for handshake, tools/schema/errors and
Streamable HTTP. It then follows `tools/list` cursors using the official SDK, with repeated-cursor,
100-page and 10,000-tool limits. A one-page response explicitly records continuation as unexercised.
The second command runs the bundled, hash-checked trusted reference client against the official
suite's synthetic local fixtures, including OAuth discovery. It does not test a candidate client
or confer OAuth coverage on the first command's endpoint. No credential arguments are accepted.
Numeric loopback HTTP only is admitted; names, remote endpoints and URL credentials are refused.
Each subprocess is time-bounded and its own process group is cleaned on cancellation/timeout.

Reports retain scope, pins, hashes, upstream output and actual exit status. Existing evidence is
never overwritten. Exit 0 means no matches within tested rules or upstream pass reported;
1 means review-required/failed; 2 means incomplete. None is a security certificate. Keep reports
private: candidate source paths, tool outputs and upstream logs can contain sensitive data.

## Validation and actual coverage

```sh
MCP_QUALITY_SEMGREP="$PWD/.venv/bin/semgrep" npm test
npm audit
```

The scanner tests contain **100 labeled synthetic positives** and four held-out benign controls;
they do not represent 100 real servers, novel vulnerabilities, or exhaustive accuracy.
Pagination regression tests exercise continuation, repeated cursors and the page budget.
The official v0.1.16 pin has 58 listed scenarios across client/server roles; active server proof
ran 30 scenarios/40 checks on one trusted reference, and the patched trusted client passed
26 scenarios/321 checks. Counts are different units and are not interchangeable.
No 100-actual-server acceptance is claimed. That requires an authorized corpus and isolated
candidate execution infrastructure; arbitrary package execution on the host is out of scope.

## Upstream provenance

`test/upstream/manifest.json` pins exact official v0.1.16 client sources at revision
21a9a2febd7100d7c17ac1021ee7f2ed9f66a1e0. `test/UPSTREAM-LICENSE` retains the full upstream
license transition notice. `test/reference-server.ts` derives from the same revision with
its listener restricted to loopback. `test/client-adapter.ts` repairs three fixture dispatch
cases: `tools_call`, SSE retry, and elicitation defaults with the current SDK capability shape.
It uses synthetic fixture inputs and does not manufacture expected responses. Upstream files
are unchanged and hash checked; changes to the trusted adapter require updating its reviewed hash.
