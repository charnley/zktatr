"""Quick task creation: `todo add Fix the build @chorus`.

zk stays in charge of the filename, id and template (`zk new --dry-run` renders
the note and picks the path). We only touch what the template cannot do safely:

* the title is passed to zk already YAML-quoted, because the template writes it
  unquoted and `Call Anna: budget` or `fix #1` would break or truncate it;
* `tags: []` is filled in;
* the note is written ourselves and `zk index` run, so the TUI sees it at once.
"""

import json
import re
import shutil
import subprocess
from pathlib import Path

from .db import notebook_dir

TAG_WORD = re.compile(r"[#@]([A-Za-z][\w-]*)")
TAG_NAME = re.compile(r"[A-Za-z0-9][\w-]*")
FRONTMATTER = re.compile(r"(---\n.*?\n---\n)(.*)", re.S)


def split_tags(args: list[str]) -> tuple[str, list[str]]:
    """Split trailing `@tag` / `#tag` words off a title.

    `@` exists because interactive zsh/bash (oh-my-zsh turns on
    `interactivecomments`) swallow an unquoted `#tag` before we ever see it.
    Only trailing words count, and a tag must start with a letter, so
    `fix issue #1` and `look #chorus stuff` stay as typed. Arguments are split on
    whitespace, so a fully quoted `"Fix it #chorus"` works too.
    """
    words = " ".join(args).split()
    tags: list[str] = []
    while words and (m := TAG_WORD.fullmatch(words[-1])):
        tags.insert(0, m.group(1))
        words.pop()
    return " ".join(words).strip(), tags


def clean_tags(tags: list[str]) -> list[str]:
    """Lowercase, strip `#`, drop duplicates (keeping order); reject odd names."""
    out: list[str] = []
    for t in tags:
        t = t.lstrip("#").lower()
        if not TAG_NAME.fullmatch(t):
            raise ValueError(f"invalid tag: {t!r} (use letters, digits, - and _)")
        if t not in out:
            out.append(t)
    return out


def render(content: str, title: str, quoted_title: str, tags: list[str]) -> str:
    """Fill in tags and put the plain title back in the body heading."""
    m = FRONTMATTER.fullmatch(content)
    if not m:
        raise RuntimeError("task template has no frontmatter")
    front, body = m.groups()
    if tags:
        front = re.sub(r"^tags:.*$", f"tags: [{', '.join(tags)}]", front, count=1, flags=re.M)
    return front + body.replace(quoted_title, title)


def create_task(title: str, tags: list[str] | None = None) -> Path:
    """Create a task note; returns its absolute path."""
    title = " ".join(title.split())
    if not title:
        raise ValueError("a task needs a title")
    tags = clean_tags(tags or [])
    zk = shutil.which("zk")
    if zk is None:
        raise RuntimeError("zk not found on PATH")

    nb = notebook_dir().resolve()  # zk rejects paths through symlinks like /var
    (nb / "tasks").mkdir(exist_ok=True)  # zk refuses to create notes in a missing directory
    quoted = json.dumps(title, ensure_ascii=False)  # valid YAML double-quoted string
    for _ in range(5):  # a clash on the random id is vanishingly rare, but cheap to handle
        res = subprocess.run(
            [zk, "new", str(nb / "tasks"), "--notebook-dir", str(nb), "--group", "task",
             "--title", quoted, "--no-input", "--dry-run"],
            capture_output=True, text=True,
        )  # fmt: skip
        lines = res.stderr.strip().splitlines()
        if res.returncode != 0 or not lines:
            raise RuntimeError(f"zk new failed: {res.stderr.strip() or res.returncode}")
        path = Path(lines[-1])  # dry-run prints the would-be path on stderr
        try:
            with path.open("x", encoding="utf-8") as f:
                f.write(render(res.stdout, title, quoted, tags))
        except FileExistsError:
            continue
        idx = subprocess.run([zk, "index", "--quiet", "--notebook-dir", str(nb)],
                             capture_output=True, text=True)  # fmt: skip
        if idx.returncode != 0:
            raise RuntimeError(f"created {path} but `zk index` failed: {idx.stderr.strip()}")
        return path
    raise RuntimeError("could not find a free note id")
