// Owned synthetic stdio fixture for the upstream v0.1.16 json-schema-2020-12 scenario (SEP-1613).
// It only answers initialize, ping and tools/list. It has no tools/call handler, so no tool can run.
// `--strip=<keyword>` removes one top-level inputSchema keyword to prove the upstream check fails.
import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { ListToolsRequestSchema } from '@modelcontextprotocol/sdk/types.js';

const strippable = ['$schema', '$defs', 'additionalProperties'];
const strip = process.argv.filter(arg => arg.startsWith('--strip=')).map(arg => arg.slice('--strip='.length));
if (strip.some(keyword => !strippable.includes(keyword))) throw new Error('Unknown fixture mutation');

// Exact inputSchema from the upstream scenario's server implementation requirements.
const inputSchema: Record<string, unknown> = {
  $schema: 'https://json-schema.org/draft/2020-12/schema',
  type: 'object',
  $defs: {
    address: {type: 'object', properties: {street: {type: 'string'}, city: {type: 'string'}}}
  },
  properties: {name: {type: 'string'}, address: {$ref: '#/$defs/address'}},
  additionalProperties: false
};
for (const keyword of strip) delete inputSchema[keyword];

const server = new Server({name: 'owned-json-schema-2020-12-fixture', version: '1.0.0'}, {capabilities: {tools: {}}});
server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [{name: 'json_schema_2020_12_tool', description: 'Tool with JSON Schema 2020-12 features', inputSchema}]
}));
await server.connect(new StdioServerTransport());
