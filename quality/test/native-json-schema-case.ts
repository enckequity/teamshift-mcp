// One native run per process: the pinned adapter configures its transport factory once.
import { runNativeScenarios } from '../native/scenarios';
const [profile, ...fixtureArgs] = process.argv.slice(2);
if (profile !== 'baseline' && profile !== 'fixed-fixture') throw new Error('Profile required');
const ownedPids: number[] = [];
const report = await runNativeScenarios({command: process.execPath,
  args: ['--import', 'tsx', 'test/native-json-schema-fixture.ts', ...fixtureArgs], env: {}},
  profile, profile === 'fixed-fixture' ? {only: ['json-schema-2020-12'], ownedPids} : {ownedPids});
console.log(JSON.stringify({report, ownedPids}));
