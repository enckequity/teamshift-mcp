import { StdioClientTransport, type StdioServerParameters } from '@modelcontextprotocol/sdk/client/stdio.js';
import type { ClientScenario } from './upstream/src/types';
import { configureNativeTransport } from './upstream/src/scenarios/server/client-helper';
import { ServerInitializeScenario } from './upstream/src/scenarios/server/lifecycle';
import * as utilities from './upstream/src/scenarios/server/utils';
import * as tools from './upstream/src/scenarios/server/tools';
import * as resources from './upstream/src/scenarios/server/resources';
import * as prompts from './upstream/src/scenarios/server/prompts';
import { ElicitationDefaultsScenario } from './upstream/src/scenarios/server/elicitation-defaults';
import { ElicitationEnumsScenario } from './upstream/src/scenarios/server/elicitation-enums';

export const baselineScenarios = [new ServerInitializeScenario(), new utilities.PingScenario(), new tools.ToolsListScenario()];
export const fixtureScenarios: ClientScenario[] = [
  new ServerInitializeScenario(),
  ...Object.values(utilities).map(Scenario => new Scenario()),
  ...Object.values(tools).map(Scenario => new Scenario()),
  ...Object.values(resources).map(Scenario => new Scenario()),
  ...Object.values(prompts).map(Scenario => new Scenario()),
  new ElicitationDefaultsScenario(), new ElicitationEnumsScenario()
];

export async function runNativeScenarios(parameters: StdioServerParameters, profile: 'baseline' | 'fixed-fixture') {
  const transports: StdioClientTransport[] = [];
  let stderrBytes = 0;
  let stderrError: Error | undefined;
  configureNativeTransport(() => {
    const transport = new StdioClientTransport({ ...parameters, env: parameters.env ?? {}, stderr: 'pipe' });
    transport.stderr?.on('data', (chunk: Buffer) => {
      stderrBytes += chunk.length;
      if (stderrBytes > 1024 * 1024 && !stderrError) {
        stderrError = new Error('Candidate stderr exceeds output budget');
        void transport.close().catch(error => {
          stderrError = new Error('Candidate stderr budget and cleanup failure', {cause: error});
        });
      }
    });
    transports.push(transport);
    return transport;
  });
  const results = [];
  try {
    for (const scenario of profile === 'baseline' ? baselineScenarios : fixtureScenarios) {
      const start = transports.length;
      try {
        results.push({ scenario: scenario.name, checks: await scenario.run('stdio:owned') });
        if (stderrError) throw stderrError;
      } finally {
        await Promise.all(transports.slice(start).map(transport => transport.close()));
      }
      if (stderrError) throw stderrError;
    }
    if (stderrError) throw stderrError;
    return {
      transport: 'native-stdio', upstream: 'v0.1.16', profile,
      coverage: profile === 'baseline' ? 'handshake/ping/tools-list; no tool invocation' : 'upstream fixed synthetic fixture contract',
      general_compliance: 'not-certified',
      transport_cases_not_applicable: ['Streamable HTTP', 'SSE', 'HTTP DNS rebinding', 'HTTP OAuth discovery'],
      upstream_pending_cases_not_exercised: ['JSON Schema 2020-12', 'SSE polling'],
      scenario_count: results.length, check_count: results.reduce((total, result) => total + result.checks.length, 0),
      results
    };
  } finally {
    // Upstream failures may occur before connection.close(); close every transport here too.
    await Promise.all(transports.map(transport => transport.close()));
    if (stderrError) throw stderrError;
  }
}
