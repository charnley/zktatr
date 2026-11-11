"""Quick task creation: `todo add Fix the build @chorus +++`.

zk stays in charge of the filename, id and template (`zk new --dry-run` renders
the note and picks the path). We only touch what the template cannot do safely:

* the title is passed to zk already YAML-quoted, because the template writes it
  unquoted and `Call Anna: budget` or `fix #1` would break or truncate it;
* `tags: []` and, when given, `priority:` are filled in;
* the note is written ourselves and `zk index` run, so the TUI sees it at once.
"""

import json
import re
import shutil
import subprocess
from pathlib import Path

from .db import notebook_dir
from .tags import TAG_NAME, known_spellings

TAG_WORD = re.compile(r"[#@]([A-Za-z][\w-]*)")
PLUSES = re.compile(r"\++")
PRIORITY_STEP = 25  # each `+` adds 25%, so `++++` is 100
FRONTMATTER = re.compile(r"(---\n.*?\n---\n)(.*)", re.S)


def parse_words(args: list[str]) -> tuple[str, list[str], int]:
    """Split trailing `@tag` / `#tag` / `+++` words off a title -> (title, tags, pluses).

    `@` exists because interactive zsh/bash (oh-my-zsh turns on
    `interactivecomments`) swallow an unquoted `#tag` before we ever see it.
    Only trailing words count, in any order, and a tag must start with a letter,
    so `fix issue #1`, `look #chorus stuff` and `C++ port` stay as typed.
    Arguments are split on whitespace, so a fully quoted title works too.
    Several `+` words add up. (`+` because zsh/bash history expansion eats `!!`.)
    """
    words = " ".join(args).split()
    tags: list[str] = []
    pluses = 0
    while words:
        if m := TAG_WORD.fullmatch(words[-1]):
            tags.insert(0, m.group(1))
        elif PLUSES.fullmatch(words[-1]):
            pluses += len(words[-1])
        else:
            break
        words.pop()
    return " ".join(words).strip(), tags, pluses


def priority_from_pluses(pluses: int) -> int | None:
    """0 -> None (keep the template default), then 25 per `+`, capped at 100."""
    return min(pluses, 100 // PRIORITY_STEP) * PRIORITY_STEP if pluses > 0 else None


def clean_tags(tags: list[str], known: dict[str, str] | None = None) -> list[str]:
    """Strip `#`, drop duplicates (keeping order); reject odd names.

    A tag zk already has keeps its existing spelling (`known` maps lowercase to
    that spelling, e.g. `litlmol-xp` -> `Litlmol-xp`); a new one is lowercased so
    `Chorus` and `chorus` do not become two tags.
    """
    known = known or {}
    out: list[str] = []
    for t in tags:
        t = t.lstrip("#")
        if not TAG_NAME.fullmatch(t):
            raise ValueError(f"invalid tag: {t!r} (use letters, digits, - and _)")
        t = known.get(t.lower(), t.lower())
        if t not in out:
            out.append(t)
    return out


def render(
    content: str, title: str, quoted_title: str, tags: list[str], priority: int | None = None
) -> str:
    """Fill in tags/priority and put the plain title back in the body heading."""
    m = FRONTMATTER.fullmatch(content)
    if not m:
        raise RuntimeError("task template has no frontmatter")
    front, body = m.groups()
    if tags:
        front = re.sub(r"^tags:.*$", f"tags: [{', '.join(tags)}]", front, count=1, flags=re.M)
    if priority is not None:
        front = re.sub(r"^priority:.*$", f"priority: {priority}", front, count=1, flags=re.M)
    return front + body.replace(quoted_title, title)


def create_task(
    title: str, tags: list[str] | None = None, priority: int | None = None
) -> Path:
    """Create a task note; returns its absolute path.

    `priority=None` leaves the template's default in place.
    """
    title = " ".join(title.split())
    if not title:
        raise ValueError("a task needs a title")
    tags = clean_tags(tags or [], known_spellings())
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
                f.write(render(res.stdout, title, quoted, tags, priority))
        except FileExistsError:
            continue
        idx = subprocess.run([zk, "index", "--quiet", "--notebook-dir", str(nb)],
                             capture_output=True, text=True)  # fmt: skip
        if idx.returncode != 0:
            raise RuntimeError(f"created {path} but `zk index` failed: {idx.stderr.strip()}")
        return path
    raise RuntimeError("could not find a free note id")
