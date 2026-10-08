# Release validation, 2026-10-08 UTC

Disclosure was public first in repository PR1 at commit
90ab594c97faa6d1d07425c40859104ca97a7f4d; anonymous exact-byte verification passed.

| Scope | Observed result | Limit |
| --- | --- | --- |
| Python boundary/scanner checks | 8 test methods; 100 labeled positive fixture cases and 4 benign controls passed | Synthetic source observations, not real vulnerabilities or servers |
| Pagination regressions | 4 tests passed | Synthetic client results |
| Official active server suite 0.1.16 | 30 scenarios, 40 checks passed | One trusted upstream loopback reference |
| Live supplemental tools/list | 1 page, 14 tools | Continuation unexercised |
| Official client suite 0.1.16 | 26 scenarios, 321 checks passed | Bundled trusted client against synthetic suite fixtures; SDK 1.32.1 |
| Offline advisory proof | requests==2.31.0 fixture produced OSV findings and review-required exit 1 | Package metadata only; candidate never installed or executed |
| npm audit | Zero reported vulnerabilities | Point-in-time npm advisory coverage |
| Adversarial review | Blocking staging overwrite fixed; final review clear | Bounded artifact review |

The initial trusted-client fixture run failed three dispatch cases; those failures were retained,
diagnosed and repaired in the local adapter. A complete patched rerun passed. The initial OSV
snapshot layout was rejected as incomplete; pinned 2.6.0 cache layout was corrected and the
network-denied pipeline detected the known fixture advisory. Incomplete runs were not certified.

Issue enckequity/teamshift-monorepo#4943 remains open: no 100 distinct actual server executions
are evidenced. The official pin lists 58 client/server scenarios, not 60 server scenarios.
Its actual assertion counts above exceed 60; these units must not be conflated. Candidate
corpus admission, isolated execution and actual server proof remain acceptance gates.
