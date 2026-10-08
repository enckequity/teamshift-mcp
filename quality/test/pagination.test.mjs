import { test } from 'node:test';
import assert from 'node:assert/strict';
import { collectToolPages } from '../pagination.mjs';
test('follows opaque cursor and reports actual continuation', async () => {
  const calls = [];
  const result = await collectToolPages({ listTools: async args => {
    calls.push(args);
    return args ? { tools: [{ name: 'second' }] } : { tools: [{ name: 'first' }], nextCursor: 'opaque:2' };
  }});
  assert.deepEqual(calls, [undefined, { cursor: 'opaque:2' }]);
  assert.deepEqual(result, { pages: 2, tools: 2, continuation_exercised: true });
});
test('single page does not certify continuation', async () => {
  assert.equal((await collectToolPages({ listTools: async () => ({ tools: [] }) })).continuation_exercised, false);
});
test('repeated cursor fails before an unbounded loop', async () => {
  await assert.rejects(collectToolPages({ listTools: async () => ({ tools: [], nextCursor: 'same' }) }), /repeated/);
});
test('never-ending distinct cursors hit the page budget', async () => {
  let n = 0;
  await assert.rejects(collectToolPages({ listTools: async () => ({ tools: [], nextCursor: String(++n) }) }), /page budget/);
  assert.equal(n, 100);
});
