.PHONY: setup test lint fmt typecheck doctor

setup:
	uv sync -p python3

doctor:
	uv run acp-hub doctor || true

test:
	python3 -m unittest discover -s tests -v

lint:
	uv run ruff check .

fmt:
	uv run ruff format .

typecheck:
	uv run pyright
