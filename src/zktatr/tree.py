"""Subtask / dependency tree.

`depends: [B, C]` on task A means B and C must be done before A, so they are
shown as A's subtasks. Nesting can be any depth. A reference can be a filename
stem (`2026-11-11-6rbuh8gy`), the trailing id (`6rbuh8gy`), a path
(`tasks/....md`), a `[[wikilink]]` of any of those, or a unique title.
Unknown references are ignored.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath

from .models import Task


@dataclass
class Row:
    task: Task
    depth: int
    prefix: str  # tree-drawing characters to print before the title
    done_deps: int
    total_deps: int


class Resolver:
    def __init__(self, tasks: list[Task]):
        self.by_key: dict[str, Task] = {}
        titles: dict[str, list[Task]] = {}
        for t in tasks:
            stem = PurePosixPath(t.path).stem
            for key in (t.path, stem, stem.rsplit("-", 1)[-1]):
                self.by_key.setdefault(key, t)
            titles.setdefault(t.title.strip().lower(), []).append(t)
        # Titles only count when unambiguous (duplicates exist in practice).
        self.by_title = {k: v[0] for k, v in titles.items() if len(v) == 1}

    def resolve(self, ref: str) -> Task | None:
        r = ref.strip()
        if r.startswith("[[") and r.endswith("]]"):
            r = r[2:-2].split("|")[0].strip()
        r = r.removeprefix("tasks/")
        for key in (r, r.removesuffix(".md"), f"tasks/{r}"):
            if key in self.by_key:
                return self.by_key[key]
        return self.by_title.get(r.lower())

    def deps(self, task: Task) -> list[Task]:
        seen: set[str] = set()
        out = []
        for ref in task.depends:
            d = self.resolve(ref)
            if d and d.path != task.path and d.path not in seen:
                seen.add(d.path)
                out.append(d)
        return out


def build_rows(all_tasks: list[Task], todo: list[Task]) -> list[Row]:
    """Flatten `todo` (already sorted) into tree rows.

    Only tasks in `todo` are shown. A task whose parent is not in `todo`
    becomes a root, so nothing is hidden because of its parent.
    """
    res = Resolver(all_tasks)
    order = {t.path: i for i, t in enumerate(todo)}
    deps = {t.path: res.deps(t) for t in all_tasks}

    def visible_children(t: Task) -> list[Task]:
        kids = [d for d in deps[t.path] if d.path in order]
        return sorted(kids, key=lambda d: order[d.path])

    has_visible_parent = {c.path for t in todo for c in visible_children(t)}
    roots = [t for t in todo if t.path not in has_visible_parent]

    rows: list[Row] = []
    placed: set[str] = set()

    def walk(t: Task, depth: int, lead: str, is_last: bool, stack: frozenset[str]):
        placed.add(t.path)
        prefix = "" if depth == 0 else lead + ("└─ " if is_last else "├─ ")
        all_deps = deps[t.path]
        rows.append(
            Row(t, depth, prefix, sum(d.is_done for d in all_deps), len(all_deps))
        )
        kids = [k for k in visible_children(t) if k.path not in stack]  # cycle guard
        child_lead = "" if depth == 0 else lead + ("   " if is_last else "│  ")
        for i, k in enumerate(kids):
            walk(k, depth + 1, child_lead, i == len(kids) - 1, stack | {t.path})

    for r in roots:
        walk(r, 0, "", True, frozenset())
    # Tasks only reachable through a dependency cycle still get listed.
    for t in todo:
        if t.path not in placed:
            walk(t, 0, "", True, frozenset())
    return rows
