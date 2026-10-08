# AdaL transport adapter

This is an instruction adapter; no new server or SDK is needed. Setup commands below are for a separately authorized setup session. Their presence is not permission to execute them.

## Choose one route

Use the user's chosen transport. Otherwise follow the current canonical Glasser skill's execution-surface rules: already loaded MCP tools need no CLI installation; a local coding agent may use CLI; a hosted assistant uses its MCP connector path. A terminal alone does not establish a local coding environment. Respect network restrictions and report a setup blocker rather than changing hosts or credentials to bypass it. Do not authenticate both routes just to run one pilot. The GitHub skill mirror may be older than the canonical source.

### AdaL native HTTP MCP

Add Glasser using AdaL's built-in MCP shortcut:

```text
/mcp add glasser
```

Adding an OAuth-capable server can open the browser immediately. With setup authorization, the user signs into Glasser, selects a Workspace, and approves access. Glasser creates a Workspace Key for the client; disconnecting the client does not revoke that Key. Revocation is managed in Glasser. Never request, read, or print token values.

Then use AdaL's `/mcp` dialog to inspect connection status and Test Connection; Authenticate is the fallback if needed. A successful `balance` call and discovered tools establish authenticated access, not paid-pilot success. This AdaL × Glasser combination has not been runtime-verified by this package's static checks.

Use the discovered tool names and argument schemas. These are logical operation mappings, not assumed AdaL prefixes:

| Upstream CLI operation | MCP operation |
|---|---|
| `glasser search` | `search` |
| `glasser inspect` | `inspect` |
| `glasser run` | `run` |
| `glasser runs get` | `runs_get` |
| `glasser runs list` | `runs_list` |
| `glasser runs stop` | `runs_stop` |
| `glasser balance` | `balance` |

For MCP `run`, supply a generated UUID `idempotency_key`; reuse the same key and unchanged request after an ambiguous outcome. Read the current schema for other arguments. Do not mechanically pass CLI flags, assume a Hermes `mcp__glasser__` prefix, or invent MCP equivalents for CLI task/use-case fields. Pass required request context according to the discovered schema; preserve task correlation when supported and in the local run log. Preserve upstream inspect, charge, run-status, provider-response, and run-URL reporting rules. A queued/running call is followed through `runs_get`; stopping after dispatch is not a guaranteed refund.

For clients unable to use OAuth, both products document Authorization headers. An owner-managed existing credential may be an alternative after explicit authorization, but AdaL's environment interpolation and storage behavior must be verified before configuring it. Do not paste a literal key into a command or file as a workaround.

### Skill plus CLI

Read the current [Glasser setup skill](https://glasser.ai/SKILL.md) and [setup guide](https://glasser.ai/docs/setup-skill) before an authorized installation or login. Use the official installer or npm path from those sources; do not package a separate CLI here. Existing installations can be checked with help/version without reading stored credentials. Authentication and paid calls remain separate approvals when the task limits them that way.

The CLI owns its auth and exact flags. Current canonical guidance requires `--use-case` on every CLI search; the older mirror's `--user-request` flag must not be reused without checking the current help. Run the first search alone to obtain a task ID, then use the same ID through later search/inspect/run calls. In JSON mode, a run also requires an explicit idempotency key. Do not import the Hermes plugin's bridge, token cache operations, or `hermes plugins` commands into AdaL.

## Official setup sources

- [AdaL MCP](https://docs.sylph.ai/features/mcp-support-proposed/)
- [Glasser MCP](https://glasser.ai/docs/mcp-server)
- [Glasser Skill + CLI](https://glasser.ai/docs/setup-skill)
- [Public skill addressing and curated contributions](https://github.com/SylphAI-Inc/atskills/blob/main/CONTRIBUTING.md)

Recheck these sources during setup; no endpoint catalog or price is cached in this adapter.
