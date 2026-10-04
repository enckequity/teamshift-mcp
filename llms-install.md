# Installing the TeamShift MCP server (for AI agents)

TeamShift is a hosted remote MCP server. There is nothing to clone, build or run.

1. Ask the user for a TeamShift workspace API key. They create it in the TeamShift portal; it
   starts with `ts_live_` and is shown once. Never invent one, print it back, or write it to a
   shared or committed file.
2. Add this server to the MCP settings, putting the key only in the `Authorization` header:

```json
{
  "mcpServers": {
    "teamshift": {
      "type": "streamableHttp",
      "url": "https://api.teamshift.io/v1/mcp",
      "headers": { "Authorization": "Bearer ts_live_USER_KEY" }
    }
  }
}
```

3. Check the connection by listing the server's tools. A `401` means the key is missing,
   mistyped or revoked: ask the user to create a new key in the portal.

The OAuth endpoint (`https://api.teamshift.io/v1/claude/mcp`) currently completes sign-in only for
Claude and Claude Code, so other clients should use the API-key setup above.
