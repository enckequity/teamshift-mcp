/** Adapter for the three uncovered core dispatch cases in upstream v0.1.16.
 * Uses the same SDK and hash-checked upstream fixture handlers. Synthetic inputs only.
 */
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { ElicitRequestSchema } from '@modelcontextprotocol/sdk/types.js';
import { StreamableHTTPClientTransport } from '@modelcontextprotocol/sdk/client/streamableHttp.js';
import { getHandler } from './upstream/examples/clients/typescript/everything-client.js';

const scenario = process.env.MCP_CONFORMANCE_SCENARIO;
const url = process.argv[2];
if (!scenario || !url) throw new Error('Official scenario and fixture URL required');
if (scenario === 'sse-retry') {
  await import('./upstream/examples/clients/typescript/sse-retry-test.js');
} else {
  try {
    if (scenario === 'tools_call' || scenario === 'elicitation-sep1034-client-defaults') {
      const capabilities = scenario === 'tools_call' ? {} : { elicitation: { form: { applyDefaults: true } } };
      const client = new Client({ name: 'teamshift-conformance-reference', version: '0.1.0' }, { capabilities });
      if (scenario !== 'tools_call') {
        client.setRequestHandler(ElicitRequestSchema, async () => ({ action: 'accept' as const, content: {} }));
      }
      const transport = new StreamableHTTPClientTransport(new URL(url));
      try {
        await client.connect(transport);
        await client.listTools();
        await client.callTool(scenario === 'tools_call'
          ? { name: 'add_numbers', arguments: { a: 2, b: 3 } }
          : { name: 'test_client_elicitation_defaults', arguments: {} });
      } finally {
        await transport.close();
      }
    } else {
      const handler = getHandler(scenario);
      if (!handler) throw new Error('Unsupported official scenario');
      await handler(url);
    }
    process.exit(0);
  } catch (error) {
    console.error('Trusted client fixture failed:', error);
    process.exit(1);
  }
}
