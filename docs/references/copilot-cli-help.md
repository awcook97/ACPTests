# Copilot CLI Help (Captured)

Captured from local `copilot help config && copilot help commands && copilot help environment && copilot help logging && copilot help permissions`
output (user-provided). This is intentionally partial; prefer the official docs for authoritative behavior.

## Configuration Settings (Excerpt)

```text
Configuration Settings:

  `allowed_urls`: list of URLs or domains that are allowed to be accessed without prompting.
  `denied_urls`: list of URLs or domains that are denied access. Denial rules take precedence.
  `log_level`: log level for CLI; defaults to "default". Set to "all" for debug logging.
  `model`: AI model to use for Copilot CLI; can be changed with /model or --model.
  `parallel_tool_execution`: whether to enable parallel execution of tools; defaults to `true`.
  `render_markdown`: whether to render markdown in the terminal; defaults to `true`.
  `trusted_folders`: list of folders where permission to read or execute files has been granted.
```

## Interactive Mode Commands (Excerpt)

```text
  /diff                                                          Review the changes made in the current directory (experimental)
  /init                                                          Initialize Copilot instructions and agentic features for this repository
  /mcp [show|add|edit|delete|disable|enable] [server-name]       Manage MCP server configuration
  /plan [prompt]                                                 Create an implementation plan before coding
  /review [prompt]                                               Run code review agent to analyze changes
  /session [checkpoints [n]|files|plan|rename <name>]            Show session info and workspace summary
```

## Logging (Excerpt)

```text
Examples:
  # Set logging to ./logs
  $ copilot --log-dir ./logs

  # Enable debug level logging
  $ copilot --log-level debug
```

## Permissions (Excerpt)

```text
Tool permissions are managed via --allow-tool, --deny-tool, and --allow-all-tools.

Permission patterns include:
  shell(command:*?)
  write
  url(domain-or-url?)
```

## ACP Server Mode

See `docs/references/copilot-acp-server.md`.

