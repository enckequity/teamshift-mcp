import assert from 'node:assert/strict';
import { runNativeScenarios } from '../native/scenarios';
await assert.rejects(
  runNativeScenarios({command: process.execPath,
    args: ['--import', 'tsx', 'test/native-reference.ts', '--stderr-on-close'], env: {}}, 'baseline'),
  /stderr.*budget/
);
console.log('Late synthetic stderr overflow refused; no accepted report');
