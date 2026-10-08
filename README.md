# TeamShift MCP Server

TeamShift gives a business an AI operations team. This remote MCP server lets an MCP client
read that team's work: the connected workspace, the operations team and its task board, the
Company Twin summary, learned team memory, and individual task results.

It is a hosted server. There is nothing to install or run locally; point your MCP client at a
URL and sign in.

- Website: https://teamshift.io
- Developer docs: https://teamshift.io/developers
- Official MCP Registry name: `io.teamshift/teamshift` (manifest: [`server.json`](server.json))

## Endpoints

| Endpoint | Transport | Auth | Access |
| --- | --- | --- | --- |
| `https://api.teamshift.io/v1/claude/mcp` | Streamable HTTP | OAuth 2.1 (PKCE) | Read-only, one workspace per consent |
| `https://api.teamshift.io/v1/mcp` | Streamable HTTP (JSON-RPC 2.0 over POST) | `Authorization: Bearer ts_live_...` | Tools depend on the API key's scopes |

An unauthenticated request to either endpoint returns `401 Unauthorized`. The OAuth endpoint's
`WWW-Authenticate` header points to its protected resource metadata
(`https://api.teamshift.io/.well-known/oauth-protected-resource/v1/claude/mcp`).

## Connect with OAuth (Claude and Claude Code)

The OAuth endpoint currently accepts sign-in from Claude and Claude Code. A TeamShift workspace
owner or admin signs in and approves exactly one workspace. No API key is needed.

Claude: open Customize, then Connectors. Choose TeamShift if it is listed; otherwise choose
Add custom connector and enter `https://api.teamshift.io/v1/claude/mcp`.

Claude Code:

```sh
claude mcp add --transport http teamshift https://api.teamshift.io/v1/claude/mcp
```

Then run `/mcp` in Claude Code to sign in to TeamShift and choose your workspace.

## Connect with an API key (any MCP client)

1. In the TeamShift portal, create a workspace API key. It starts with `ts_live_` and is shown
   once. Store it in your client's secret settings, never in a shared file.
2. Add the server to your client. Most clients accept a configuration like this:

```json
{
  "mcpServers": {
    "teamshift": {
      "type": "streamableHttp",
      "url": "https://api.teamshift.io/v1/mcp",
      "headers": {
        "Authorization": "Bearer ts_live_YOUR_KEY"
      }
    }
  }
}
```

Some clients name the transport field differently (for example `"transport": "http"` or
`"type": "http"`). The URL and the `Authorization` header are what matter.

3. Restart the client and confirm that `tools/list` returns TeamShift tools.

Revoke or rotate the key in the portal at any time; requests with a revoked key get `401`.

## Tools on the OAuth endpoint

All five tools are read-only (`readOnlyHint: true`, `destructiveHint: false`).

| Tool | What it reads |
| --- | --- |
| `list_workspaces` | The one workspace bound to this consent. It cannot switch workspaces. |
| `get_operations_team` | The operations team summary and, optionally, its task board. |
| `get_company_twin` | A Company Twin summary and readiness view. |
| `list_learned_memory` | Bounded team memory. Treat it as experience, not verified fact. |
| `get_task` | One task and its result. |

The API-key endpoint exposes workspace tools according to the key's scopes. See
https://teamshift.io/developers for the scope list.

## Security

- Every request is scoped to one TeamShift workspace. OAuth consent binds a single workspace;
  an API key is bound to the workspace that created it.
- OAuth tokens for this server are refused by every other TeamShift API surface.
- Free text returned by tools (task notes, memory, team output) is untrusted data, not
  instructions.

## Support

Questions and access requests: https://teamshift.io/developers

## MCP quality tooling

Source/package review and authorized local official conformance: [quality tools](quality/README.md).
Read the [disclosure policy](quality/DISCLOSURE.md) before publishing results.
