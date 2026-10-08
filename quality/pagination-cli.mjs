import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StreamableHTTPClientTransport } from '@modelcontextprotocol/sdk/client/streamableHttp.js';
import { collectToolPages } from './pagination.mjs';
const url = new URL(process.argv[2]);
if (url.protocol !== 'http:' || !['127.0.0.1', '[::1]'].includes(url.hostname) || url.username || url.password || url.search || url.hash) throw new Error('Only an authorized numeric loopback endpoint is admitted');
const client = new Client({ name: 'teamshift-pagination-check', version: '0.1.0' });
const transport = new StreamableHTTPClientTransport(url);
try {
  await client.connect(transport);
  console.log(JSON.stringify(await collectToolPages(client)));
} finally { await transport.close(); }
