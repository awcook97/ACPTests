from __future__ import annotations

import asyncio
import sys
import time
from typing import Any

from acp_hub.bus import EventBus
from acp_hub.config import HubConfig
from acp_hub.events import Event
from acp_hub.fs_watch import poll_fs_changes
from acp_hub.journal import JsonlJournal, journal_sink
from acp_hub.proc import ManagedAgentProcess
from acp_hub.protocols import get_adapter
from acp_hub.protocols.base import ProtocolAdapter
from acp_hub.router import Router
from acp_hub.tools.runner import ToolRunner


def run_tui(cfg: HubConfig) -> int:
    try:
        from textual.app import App, ComposeResult
        from textual.containers import Horizontal, Vertical
        from textual.widgets import Footer, Header, Input, RichLog, Static, TabbedContent, TabPane
        from textual.message import Message
    except Exception as e:  # noqa: BLE001 - display a friendly message
        print("Textual is not available yet.", file=sys.stderr)
        print(f"Import error: {type(e).__name__}: {e}", file=sys.stderr)
        print("", file=sys.stderr)
        print("Install deps with:", file=sys.stderr)
        print(
            "  UV_CACHE_DIR=.uv-cache uv sync -p python3 --python-preference only-system --no-python-downloads",
            file=sys.stderr,
        )
        return 1

    class HubApp(App):
        TITLE = "ACP Hub"
        BINDINGS = [
            ("q", "quit", "Quit"),
            ("t", "focus_task", "Task Input"),
        ]

        CSS = """
        Screen {
            layout: vertical;
        }
        #body {
            height: 1fr;
        }
        .panel {
            border: solid $primary;
            height: 1fr;
            overflow-y: auto;
        }
        #transcript-panel {
            width: 3fr;
        }
        #command-panel {
            width: 2fr;
        }
        #files-panel {
            width: 1fr;
        }
        #task-input {
            dock: bottom;
            margin: 0 1;
        }
        #status-bar {
            dock: bottom;
            height: 1;
            background: $accent;
            color: $text;
            padding: 0 1;
        }
        """

        def __init__(self, hub_config: HubConfig) -> None:
            super().__init__()
            self.hub_config = hub_config
            self.bus = EventBus()
            self.journal = JsonlJournal(path=hub_config.journal_path)
            self.tool_runner = ToolRunner(
                self.bus,
                workspace_root=str(hub_config.workspace_root),
                shell_allowlist=hub_config.shell_allowlist,
                require_approval=hub_config.require_tool_approval,
            )
            self._agents: dict[str, ManagedAgentProcess] = {}
            self._adapters: dict[str, ProtocolAdapter] = {}
            self._router: Router | None = None
            self._bg_tasks: list[asyncio.Task[Any]] = []

        def compose(self) -> ComposeResult:
            yield Header()
            yield Horizontal(
                RichLog(id="transcript-log", classes="panel", wrap=True, markup=True),
                RichLog(id="command-log", classes="panel", wrap=True, markup=True),
                RichLog(id="files-log", classes="panel", wrap=True, markup=True),
                id="body",
            )
            yield Input(placeholder="Enter task prompt and press Enter...", id="task-input")
            yield Static("Ready | journal: " + str(hub_config.journal_path), id="status-bar")
            yield Footer()

        async def on_mount(self) -> None:
            self.sub_title = f"journal: {self.hub_config.journal_path}"
            self.journal.open()
            self.bus.subscribe(journal_sink(self.journal))
            self.bus.subscribe(self._route_event_to_ui)

            # Spawn agents
            await self._spawn_agents()

            # Start fs watcher
            if self.hub_config.watch_paths:
                task = asyncio.create_task(
                    poll_fs_changes(
                        self.hub_config.watch_paths,
                        on_event=self.bus.publish,
                    )
                )
                self._bg_tasks.append(task)

        async def _spawn_agents(self) -> None:
            for spec in self.hub_config.agents:
                proc = ManagedAgentProcess(spec=spec, bus=self.bus)
                adapter_cls = get_adapter(spec.protocol)
                adapter = adapter_cls(proc)
                self._agents[spec.id] = proc
                self._adapters[spec.id] = adapter
                try:
                    await proc.start()
                    await adapter.initialize()
                    self._log_transcript(f"[green]Agent '{spec.id}' started[/green]")
                except Exception as exc:
                    self._log_transcript(
                        f"[red]Failed to start '{spec.id}': {exc}[/red]"
                    )

            agent_pairs = {
                aid: (proc, self._adapters[aid])
                for aid, proc in self._agents.items()
            }
            self._router = Router(self.bus, agent_pairs, mode="single")

        async def _route_event_to_ui(self, event: Event) -> None:
            """Route incoming events to appropriate UI panels."""
            kind = event.kind
            if kind.startswith("agent."):
                self._handle_agent_event(event)
            elif kind.startswith("tool."):
                self._handle_tool_event(event)
            elif kind.startswith("fs."):
                self._handle_fs_event(event)
            elif kind.startswith("router."):
                self._handle_router_event(event)

            # Update status bar
            try:
                status = self.query_one("#status-bar", Static)
                agents_str = ", ".join(
                    f"{aid}({'ok' if p.running else 'exit'})"
                    for aid, p in self._agents.items()
                )
                status.update(f"Agents: {agents_str} | journal: {self.hub_config.journal_path}")
            except Exception:
                pass

        def _handle_agent_event(self, event: Event) -> None:
            aid = event.agent_id or "?"
            if event.kind == "agent.stdout":
                self._log_transcript(f"[cyan][{aid}][/cyan] {event.payload.get('text', '')}")
            elif event.kind == "agent.stderr":
                self._log_transcript(f"[yellow][{aid}:err][/yellow] {event.payload.get('text', '')}")
            elif event.kind == "agent.jsonrpc":
                msg = event.payload.get("message", {})
                method = msg.get("method", "response")
                self._log_transcript(f"[blue][{aid}:rpc][/blue] {method}")
                # Check for tool calls
                adapter = self._adapters.get(aid)
                if adapter and adapter.is_tool_call(msg):
                    asyncio.create_task(self._handle_tool_call(aid, msg))
                elif adapter and adapter.is_completion(msg):
                    text = adapter.extract_text(msg)
                    if text:
                        self._log_transcript(f"[green][{aid}:done][/green] {text}")
            elif event.kind == "agent.started":
                self._log_transcript(f"[green]● {aid} started[/green]")
            elif event.kind == "agent.exited":
                code = event.payload.get("exit_code", "?")
                self._log_transcript(f"[red]● {aid} exited ({code})[/red]")

        def _handle_tool_event(self, event: Event) -> None:
            if event.kind == "tool.invocation":
                tool = event.payload.get("tool", "?")
                args = event.payload.get("args", {})
                self._log_command(f"[bold]→ {tool}[/bold] {args}")
            elif event.kind == "tool.result":
                tool = event.payload.get("tool", "?")
                ok = event.payload.get("ok", False)
                mark = "[green]✓[/green]" if ok else "[red]✗[/red]"
                result = event.payload.get("result", {})
                stdout = result.get("stdout", "")
                if stdout:
                    stdout = stdout[:200]
                self._log_command(f"{mark} {tool} {stdout}")

        def _handle_fs_event(self, event: Event) -> None:
            path = event.payload.get("path", "?")
            change = event.payload.get("change", "?")
            self._log_files(f"[magenta]{change}[/magenta] {path}")

        def _handle_router_event(self, event: Event) -> None:
            frm = event.payload.get("from", "?")
            to = event.payload.get("to", "?")
            self._log_transcript(f"[dim]→ routed {frm} → {to}[/dim]")

        async def _handle_tool_call(self, agent_id: str, msg: dict[str, Any]) -> None:
            adapter = self._adapters[agent_id]
            corr_id, tool_name, args = adapter.extract_tool_call(msg)
            agent_proc = self._agents[agent_id]
            result = await self.tool_runner.execute(
                agent_id, tool_name, args, corr_id,
                sandbox=agent_proc.spec.sandbox,
            )
            ok = "error" not in result
            await adapter.send_tool_result(corr_id, result, ok=ok)

        async def on_input_submitted(self, event: Input.Submitted) -> None:
            task = event.value.strip()
            if not task:
                return
            event.input.clear()

            self._log_transcript(f"[bold white]> {task}[/bold white]")

            if self._router:
                try:
                    await self._router.send_task(task)
                except Exception as exc:
                    self._log_transcript(f"[red]Error: {exc}[/red]")

        def action_focus_task(self) -> None:
            self.query_one("#task-input", Input).focus()

        def _log_transcript(self, text: str) -> None:
            try:
                log = self.query_one("#transcript-log", RichLog)
                log.write(text)
            except Exception:
                pass

        def _log_command(self, text: str) -> None:
            try:
                log = self.query_one("#command-log", RichLog)
                log.write(text)
            except Exception:
                pass

        def _log_files(self, text: str) -> None:
            try:
                log = self.query_one("#files-log", RichLog)
                log.write(text)
            except Exception:
                pass

        async def on_unmount(self) -> None:
            for t in self._bg_tasks:
                t.cancel()
            for aid, proc in self._agents.items():
                try:
                    await proc.terminate()
                except Exception:
                    pass
            self.journal.close()

    HubApp(cfg).run()
    return 0

