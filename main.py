import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from acp_hub.cli import main  # noqa: E402 - path bootstrap comes first


if __name__ == "__main__":
    raise SystemExit(main())
