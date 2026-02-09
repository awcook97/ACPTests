from __future__ import annotations

import argparse
import json
import platform
import sys
from pathlib import Path

from acp_hub.config import ConfigError, load_config


def _default_config_path() -> str:
    # Prefer an explicit file in the repo root, but allow running without config.
    for candidate in ("acp-hub.json", "acp_hub.json", "acp-hub.example.json"):
        if Path(candidate).exists():
            return candidate
    return "acp-hub.json"


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="acp-hub", add_help=True)
    p.add_argument(
        "--config",
        default=_default_config_path(),
        help="Path to hub config JSON (default: auto-detect in cwd).",
    )

    sub = p.add_subparsers(dest="cmd")

    sub.add_parser("tui", help="Run the Textual UI (default).")
    sub.add_parser("doctor", help="Print environment/dependency diagnostics.")
    sub.add_parser("print-config", help="Load config and print normalized JSON.")

    return p


def _cmd_doctor() -> int:
    print("acp-hub doctor")
    print(f"- python: {sys.version.split()[0]}")
    print(f"- platform: {platform.platform()}")

    # Optional deps: we want the CLI to run even before `uv sync`.
    deps = [
        ("agent_client_protocol", "agent-client-protocol"),
        ("textual", "textual"),
        ("watchfiles", "watchfiles"),
        ("typer", "typer"),
    ]
    ok = True
    for import_name, dist_name in deps:
        try:
            __import__(import_name)
            print(f"- dep: {dist_name}: OK")
        except Exception as e:  # noqa: BLE001 - diagnostics only
            ok = False
            print(f"- dep: {dist_name}: MISSING ({type(e).__name__}: {e})")

    # uv convenience hints
    if Path("pyproject.toml").exists():
        print("- hint: install deps:")
        # `uv.toml` in this repo sets cache-dir and disables Python downloads.
        print("  uv sync -p python3")

    return 0 if ok else 1


def _cmd_print_config(config_path: Path) -> int:
    cfg = load_config(config_path)
    print(json.dumps(cfg.to_dict(), indent=2, sort_keys=True))
    return 0


def _cmd_tui(config_path: Path) -> int:
    cfg = load_config(config_path)

    # Import Textual lazily so `doctor` can run without deps installed.
    from acp_hub.tui.run import run_tui

    return run_tui(cfg)


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    ns = parser.parse_args(argv)

    cmd = ns.cmd or "tui"
    config_path = Path(ns.config)

    try:
        if cmd == "doctor":
            return _cmd_doctor()
        if cmd == "print-config":
            return _cmd_print_config(config_path)
        if cmd == "tui":
            return _cmd_tui(config_path)

        parser.error(f"unknown command: {cmd}")
        return 2
    except ConfigError as e:
        print(f"config error: {e}", file=sys.stderr)
        return 2
