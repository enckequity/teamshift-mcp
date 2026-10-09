import assert from 'node:assert/strict';
import { runNativeScenarios, fixtureScenarios } from '../native/scenarios';
const report = await runNativeScenarios({command: process.execPath, args: ['--import', 'tsx', 'test/native-reference.ts'], env: {}}, 'baseline');
assert.equal(report.transport, 'native-stdio');
assert.equal(report.scenario_count, 3);
assert.equal(report.general_compliance, 'not-certified');
assert.equal(new Set(fixtureScenarios.map(s => s.name)).size, fixtureScenarios.length);
assert.ok(report.results.every(result => result.checks.every(check => check.status === 'SUCCESS')), JSON.stringify(report));
console.log(JSON.stringify({native_baseline_scenarios: report.scenario_count, native_baseline_checks: report.check_count, fixture_scenarios: fixtureScenarios.length, candidate_servers: 0}));