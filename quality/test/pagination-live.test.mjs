import assert from 'node:assert/strict';
import { once } from 'node:events';
import test from 'node:test';
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StreamableHTTPClientTransport } from '@modelcontextprotocol/sdk/client/streamableHttp.js';
import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { createMcpExpressApp } from '@modelcontextprotocol/sdk/server/express.js';
import { StreamableHTTPServerTransport } from '@modelcontextprotocol/sdk/server/streamableHttp.js';
import { ListToolsRequestSchema } from '@modelcontextprotocol/sdk/types.js';
import { collectToolPages } from '../pagination.mjs';

// Owned synthetic SDK fixture only. No candidate process, tool call or provider.
async function fixture(context, readPage, check) {
  const app = createMcpExpressApp({ host: '127.0.0.1' });
  const sessions = new Set();
  const cleanupErrors = [];
  const closing = new Set();
  function closeServer(server) {
    const pending = server.close().catch(error => cleanupErrors.push(error)).finally(() => {
      sessions.delete(server);
      closing.delete(pending);
    });
    closing.add(pending);
    return pending;
  }
  app.post('/mcp', async (request, response) => {
    const server = new Server({ name: 'pagination-fixture', version: '1.0.0' }, { capabilities: { tools: {} } });
    server.setRequestHandler(ListToolsRequestSchema, request => readPage(request.params?.cursor));
    const transport = new StreamableHTTPServerTransport({ sessionIdGenerator: undefined });
    sessions.add(server);
    response.on('close', () => { void closeServer(server); });
    try {
      await server.connect(transport);
      await transport.handleRequest(request, response, request.body);
    } catch {
      if (!response.headersSent) response.status(500).end();
      await closeServer(server);
    }
  });
  app.get('/mcp', (_request, response) => response.status(405).end());
  const listener = app.listen(0, '127.0.0.1');
  await once(listener, 'listening');
  const client = new Client({ name: 'pagination-live-check', version: '1.0.0' });
  const transport = new StreamableHTTPClientTransport(new URL(`http://127.0.0.1:${listener.address().port}/mcp`));
  let cleanupPromise;
  function cleanup() {
    return cleanupPromise ??= (async () => {
      const closed = new Promise(resolve => {
        if (listener.listening) listener.close(resolve);
        else resolve();
      });
      listener.closeAllConnections();
      const results = await Promise.allSettled([
        client.close(), ...[...sessions].map(closeServer), ...closing,
      ]);
      await closed;
      const errors = [...cleanupErrors, ...results.filter(result => result.status === 'rejected').map(result => result.reason)];
      if (errors.length) throw new AggregateError(errors, 'Fixture cleanup failed');
    })();
  }
  const abort = () => { void cleanup().catch(error => cleanupErrors.push(error)); };
  context.signal.addEventListener('abort', abort, { once: true });
  try {
    if (context.signal.aborted) throw context.signal.reason;
    await client.connect(transport);
    await check(client);
  } finally {
    context.signal.removeEventListener('abort', abort);
    await cleanup();
  }
}

const tool = name => ({ name, inputSchema: { type: 'object' } });

test('live SDK preserves opaque cursor and traverses two pages', { timeout: 5000 }, async context => {
  const cursors = [];
  await fixture(context, cursor => {
    cursors.push(cursor);
    return cursor === undefined ? { tools: [tool('first')], nextCursor: 'opaque:second' } : { tools: [tool('second')] };
  }, async client => {
    assert.deepEqual(await collectToolPages(client), { pages: 2, tools: 2, continuation_exercised: true });
  });
  assert.deepEqual(cursors, [undefined, 'opaque:second']);
});

test('live SDK single page does not claim continuation', { timeout: 5000 }, async context => {
  await fixture(context, () => ({ tools: [] }), async client => {
    assert.deepEqual(await collectToolPages(client), { pages: 1, tools: 0, continuation_exercised: false });
  });
});

test('live SDK repeated cursor is refused', { timeout: 5000 }, async context => {
  let calls = 0;
  await fixture(context, () => { calls += 1; return { tools: [], nextCursor: 'repeated' }; }, async client => {
    await assert.rejects(collectToolPages(client), /repeated/);
  });
  assert.equal(calls, 2);
});

test('live SDK page budget ends after exactly 100 pages', { timeout: 10000 }, async context => {
  let calls = 0;
  await fixture(context, () => ({ tools: [], nextCursor: `page:${++calls}` }), async client => {
    await assert.rejects(collectToolPages(client), /page budget/);
  });
  assert.equal(calls, 100);
});
