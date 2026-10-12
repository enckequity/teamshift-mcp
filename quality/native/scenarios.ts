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
import { JsonSchema2020_12Scenario } from './upstream/src/scenarios/server/json-schema-2020-12';

export const baselineScenarios = [new ServerInitializeScenario(), new utilities.PingScenario(), new tools.ToolsListScenario()];
export const fixtureScenarios: ClientScenario[] = [
  new ServerInitializeScenario(),
  ...Object.values(utilities).map(Scenario => new Scenario()),
  ...Object.values(tools).map(Scenario => new Scenario()),
  ...Object.values(resources).map(Scenario => new Scenario()),
  ...Object.values(prompts).map(Scenario => new Scenario()),
  new ElicitationDefaultsScenario(), new ElicitationEnumsScenario(),
  new JsonSchema2020_12Scenario()
];

export interface NativeRunOptions {
  /** Fixed-fixture only: run just these upstream scenario names against a narrower owned fixture. */
  only?: readonly string[];
  /** Receives the PID of every owned stdio process this run spawns, for exit verification. */
  ownedPids?: number[];
}

function selectScenarios(profile: 'baseline' | 'fixed-fixture', only?: readonly string[]): ClientScenario[] {
  if (profile === 'baseline') {
    if (only) throw new Error('Baseline coverage is fixed: initialize, ping and tools/list only');
    return baselineScenarios;
  }
  if (!only) return fixtureScenarios;
  const selected = fixtureScenarios.filter(scenario => only.includes(scenario.name));
  if (only.length === 0 || selected.length !== new Set(only).size) throw new Error('Unknown fixed-fixture scenario selection');
  return selected;
}

export async function runNativeScenarios(parameters: StdioServerParameters, profile: 'baseline' | 'fixed-fixture', options: NativeRunOptions = {}) {
  const scenarios = selectScenarios(profile, options.only);
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
    const start = transport.start.bind(transport);
    transport.start = async () => {
      await start();
      if (transport.pid !== null) options.ownedPids?.push(transport.pid);
    };
    transports.push(transport);
    return transport;
  });
  const results = [];
  try {
    for (const scenario of scenarios) {
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
      upstream_pending_cases_not_exercised: ['SSE polling'],
      scenario_count: results.length, check_count: results.reduce((total, result) => total + result.checks.length, 0),
      results
    };
  } finally {
    // Upstream failures may occur before connection.close(); close every transport here too.
    await Promise.all(transports.map(transport => transport.close()));
    if (stderrError) throw stderrError;
  }
}
