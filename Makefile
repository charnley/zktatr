venv_todo=./.venv/bin/todo

.PHONY: setup install install-completion readme-hero

all:
	uv sync

install:
	uv tool install --editable .

install-completion:
	command -v todo
	mkdir -p ~/.oh-my-zsh/custom/completions
	ln -sf "$$($(venv_todo) completion zsh --path)" ~/.oh-my-zsh/custom/completions/_todo

readme-hero:
	uv run python scripts/hero.py
