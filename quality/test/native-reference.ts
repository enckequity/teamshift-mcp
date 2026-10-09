import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { z } from 'zod';
const server = new McpServer({name: 'owned-native-test-fixture', version: '1.0.0'});
server.registerTool('echo', {description: 'Synthetic echo fixture', inputSchema: {text: z.string()}}, async ({text}) => ({content: [{type:'text',text}]}));
await server.connect(new StdioServerTransport());
if (process.argv.includes('--stderr-on-close')) {
  process.stdin.on('end', () => {
    process.stderr.write(Buffer.alloc(1024 * 1024 + 1, 'x'), () => process.exit(0));
  });
}
