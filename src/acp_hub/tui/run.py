from __future__ import annotations

import sys

from acp_hub.config import HubConfig


def run_tui(cfg: HubConfig) -> int:
    try:
        from textual.app import App, ComposeResult
        from textual.containers import Horizontal
        from textual.widgets import Footer, Header, Static
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

        CSS = """
        Screen {
            layout: vertical;
        }
        #body {
            height: 1fr;
        }
        .panel {
            border: solid $primary;
            padding: 1 1;
            height: 1fr;
        }
        """

        def compose(self) -> ComposeResult:
            yield Header()
            yield Horizontal(
                Static("Agents (transcripts)\n\n(TODO: wire event bus + per-agent panes)", classes="panel"),
                Static("Commands\n\n(TODO: tool/command monitor)", classes="panel"),
                Static("Files\n\n(TODO: fs watcher + git diff)", classes="panel"),
                id="body",
            )
            yield Footer()

        def on_mount(self) -> None:
            # Show where we expect to write logs so users can tail immediately.
            self.sub_title = f"journal: {cfg.journal_path}"

    HubApp().run()
    return 0

