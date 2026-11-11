"""Shell completion scripts, printed by `todo completion <shell>`.

The scripts are real files in `completions/`, so `todo completion zsh --path`
can point a symlink at them and they never go stale.
"""

from importlib.resources import files
from pathlib import Path

FILES = {"zsh": "_todo"}


def script_path(shell: str) -> Path:
    return Path(str(files("zktatr").joinpath("completions", FILES[shell])))


def script(shell: str) -> str:
    return script_path(shell).read_text()
