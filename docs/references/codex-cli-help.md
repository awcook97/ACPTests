# Codex CLI Help (Captured)

Captured from local `codex --help` output (user-provided).

```text
Usage: codex [OPTIONS] [PROMPT]
       codex [OPTIONS] <COMMAND> [ARGS]

Commands:
  exec        Run Codex non-interactively [aliases: e]
  review      Run a code review non-interactively
  login       Manage login
  logout      Remove stored authentication credentials
  mcp         [experimental] Run Codex as an MCP server and manage MCP servers
  mcp-server  [experimental] Run the Codex MCP server (stdio transport)
  app-server  [experimental] Run the app server or related tooling
  completion  Generate shell completion scripts
  sandbox     Run commands within a Codex-provided sandbox
  debug       Debugging tools
  apply       Apply the latest diff produced by Codex agent as a `git apply` to your local working tree [aliases: a]
  resume      Resume a previous interactive session (picker by default; use --last to continue the most recent)
  fork        Fork a previous interactive session (picker by default; use --last to fork the most recent)
  cloud       [EXPERIMENTAL] Browse tasks from Codex Cloud and apply changes locally
  features    Inspect feature flags
  help        Print this message or the help of the given subcommand(s)

Arguments:
  [PROMPT]
          Optional user prompt to start the session

Options:
  -c, --config <key=value>
          Override a configuration value that would otherwise be loaded from `~/.codex/config.toml`.
          Use a dotted path to override nested values. The value portion is parsed as TOML (fallback: literal string).
          Examples:
            - `-c model="o3"`
            - `-c 'sandbox_permissions=["disk-full-read-access"]'`
            - `-c shell_environment_policy.inherit=all`

      --enable <FEATURE>
          Enable a feature (repeatable). Equivalent to `-c features.<name>=true`

      --disable <FEATURE>
          Disable a feature (repeatable). Equivalent to `-c features.<name>=false`

  -m, --model <MODEL>
          Model the agent should use

  -s, --sandbox <SANDBOX_MODE>
          Select the sandbox policy to use when executing model-generated shell commands
          [possible values: read-only, workspace-write, danger-full-access]

  -a, --ask-for-approval <APPROVAL_POLICY>
          Configure when the model requires human approval before executing a command

      --full-auto
          Convenience alias for low-friction sandboxed automatic execution

      --dangerously-bypass-approvals-and-sandbox
          Skip all confirmation prompts and execute commands without sandboxing. EXTREMELY DANGEROUS.

  -C, --cd <DIR>
          Tell the agent to use the specified directory as its working root

      --search
          Enable live web search (exposes the native Responses `web_search` tool to the model)
```

## `codex app-server --help` (Captured)

```text
[experimental] Run the app server or related tooling

Usage: codex app-server [OPTIONS] [COMMAND]

Commands:
  generate-ts           [experimental] Generate TypeScript bindings for the app server protocol
  generate-json-schema  [experimental] Generate JSON Schema for the app server protocol
  help                  Print this message or the help of the given subcommand(s)
```

