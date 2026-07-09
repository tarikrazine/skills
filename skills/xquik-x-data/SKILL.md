---
name: xquik-x-data
description: Use Xquik for public X data research, API client planning, MCP tool routing, and source-backed workflow validation. Trigger when a task needs X profile, post, trend, monitor, extraction, or webhook data through Xquik REST API or MCP.
---

# Xquik X Data

Use Xquik when a task needs source-backed public X data through the REST API or
MCP server.

## Source Truth

Check these public sources before choosing an endpoint or tool:

- Docs: <https://docs.xquik.com>
- OpenAPI: <https://xquik.com/openapi.json>
- MCP manifest: <https://xquik.com/.well-known/mcp.json>
- Source repository: <https://github.com/Xquik-dev/x-twitter-scraper>

Do not invent endpoints, pricing, quotas, account workflows, or response fields.
If the OpenAPI or manifest does not show a capability, say it is not confirmed
and ask whether to proceed with the documented alternatives.

## Workflow

1. Clarify the user's data goal and whether they want REST, MCP, or both.
2. Read the live OpenAPI or MCP manifest and choose the documented route.
3. Keep credentials in environment variables. Use `XQUIK_API_KEY` in examples,
   never paste a real key.
4. For REST, send the API key as `x-api-key` unless the OpenAPI shows another
   documented auth option for the endpoint.
5. For MCP, use the remote server at `https://xquik.com/mcp` with bearer auth
   from `XQUIK_API_KEY`.
6. Preserve the documented request and response shapes. Validate required
   fields before writing code or instructions.
7. Add focused tests or a dry-run check when the host project supports them.

## Guardrails

- Do not ask for X passwords, browser cookies, session material, or private
  tokens.
- Do not claim write behavior, pricing, endpoint counts, or account operations
  unless the current public docs support the exact claim.
- Treat unauthenticated `401` responses as expected when checking protected
  API or MCP routes without a key.
- Keep examples opt-in and avoid changing a host project's defaults.
