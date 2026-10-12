import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { runNativeScenarios, baselineScenarios, fixtureScenarios } from '../native/scenarios';

const scenario = 'json-schema-2020-12';
const checkIds = ['json-schema-2020-12-tool-found', 'json-schema-2020-12-$schema',
  'json-schema-2020-12-$defs', 'json-schema-2020-12-additionalProperties'];
const ownedPids: number[] = [];
type Report = Awaited<ReturnType<typeof runNativeScenarios>>;

function runCase(profile: 'baseline' | 'fixed-fixture', ...fixtureArgs: string[]): Report {
  const output = execFileSync(process.execPath, ['--import', 'tsx', 'test/native-json-schema-case.ts', profile, ...fixtureArgs],
    {encoding: 'utf8', env: {PATH: process.env.PATH ?? ''}, timeout: 60_000});
  const {report, ownedPids: pids} = JSON.parse(output.trim().split('\n').at(-1)!);
  ownedPids.push(...pids);
  return report;
}

function statuses(report: Report) {
  assert.equal(report.profile, 'fixed-fixture');
  assert.equal(report.general_compliance, 'not-certified');
  assert.deepEqual(report.results.map(result => result.scenario), [scenario]);
  return Object.fromEntries(report.results[0].checks.map(check => [check.id, check.status]));
}

// Coverage shape: the unchanged upstream scenario is in the fixed-fixture set; baseline is unchanged.
assert.ok(fixtureScenarios.some(s => s.name === scenario));
assert.deepEqual(baselineScenarios.map(s => s.name), ['server-initialize', 'ping', 'tools-list']);
const anyFixture = {command: process.execPath, args: ['--version'], env: {}};
await assert.rejects(runNativeScenarios(anyFixture, 'baseline', {only: [scenario]}), /Baseline coverage is fixed/);
await assert.rejects(runNativeScenarios(anyFixture, 'fixed-fixture', {only: ['not-a-scenario']}), /Unknown/);

// Positive: the owned fixture passes all four upstream checks.
const positive = runCase('fixed-fixture');
assert.deepEqual(statuses(positive), Object.fromEntries(checkIds.map(id => [id, 'SUCCESS'])), JSON.stringify(positive));
assert.equal(positive.check_count, 4);
assert.deepEqual(positive.upstream_pending_cases_not_exercised, ['SSE polling']);

// Regressions: stripping one keyword fails exactly its corresponding upstream check.
const mutations = {'$schema': 'json-schema-2020-12-$schema', '$defs': 'json-schema-2020-12-$defs',
  additionalProperties: 'json-schema-2020-12-additionalProperties'};
const mutationResults: Record<string, Record<string, string>> = {};
for (const [keyword, failing] of Object.entries(mutations)) {
  const report = runCase('fixed-fixture', `--strip=${keyword}`);
  const observed = statuses(report);
  assert.deepEqual(observed, Object.fromEntries(checkIds.map(id => [id, id === failing ? 'FAILURE' : 'SUCCESS'])), JSON.stringify(report));
  mutationResults[keyword] = observed;
}

// Baseline against the same fixture stays at initialize, ping and tools/list; no tool is invoked.
const baseline = runCase('baseline');
assert.deepEqual(baseline.results.map(result => result.scenario), ['server-initialize', 'ping', 'tools-list']);
assert.ok(baseline.results.every(result => result.checks.every(check => check.status === 'SUCCESS')), JSON.stringify(baseline));

// Every owned fixture process must have exited.
const alive = (pid: number) => { try { process.kill(pid, 0); return true; } catch (error) {
  if ((error as NodeJS.ErrnoException).code === 'ESRCH') return false; throw error; } };
const deadline = Date.now() + 5000;
while (ownedPids.some(alive) && Date.now() < deadline) await new Promise(resolve => setTimeout(resolve, 50));
assert.ok(ownedPids.length >= 5, `expected owned fixture processes, saw ${ownedPids.length}`);
assert.deepEqual(ownedPids.filter(alive), [], 'owned fixture process still running');

console.log(JSON.stringify({json_schema_2020_12: {positive_checks: positive.check_count,
  positive_status: 'all SUCCESS', mutations: mutationResults, baseline_scenarios: baseline.scenario_count,
  owned_processes_spawned: ownedPids.length, owned_processes_still_running: 0, candidate_servers: 0}}));
