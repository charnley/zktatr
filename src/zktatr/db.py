"""Engine and queries against the zk notebook database."""
from __future__ import annotations

import os
from datetime import date
from pathlib import Path

from sqlalchemy import Engine
from sqlmodel import Session, col, create_engine, select

from .models import Note, Task


def notebook_dir() -> Path:
    return Path(os.environ.get("ZK_NOTEBOOK_DIR", "~/notes")).expanduser()


def db_path() -> Path:
    return notebook_dir() / ".zk" / "notebook.db"


def make_engine(readonly: bool = True) -> Engine:
    db = db_path()
    if not db.exists():
        raise FileNotFoundError(f"zk database not found: {db}")
    mode = "ro" if readonly else "rw"
    return create_engine(f"sqlite:///file:{db}?mode={mode}&uri=true")


def all_tasks(session: Session) -> list[Task]:
    notes = session.exec(select(Note).where(col(Note.path).startswith("tasks/"))).all()
    return [Task.from_note(n) for n in notes]


def split_today(tasks: list[Task], today: date) -> tuple[list[Task], list[Task]]:
    """(to do, done today).

    To do: not done, and no due date or due <= today. Overdue first, then by
    priority (high first), then title. Done: finished on `today`.
    """
    todo = [t for t in tasks if not t.is_done and (t.due is None or t.due <= today)]
    done = [t for t in tasks if t.is_done and t.done == today]
    todo.sort(key=lambda t: (t.due is None, t.due or today, -t.priority, t.title))
    done.sort(key=lambda t: t.title)
    return todo, done


def load_tasks(engine: Engine | None = None) -> list[Task]:
    with Session(engine or make_engine()) as session:
        return all_tasks(session)


def tasks_today(today: date | None = None, engine: Engine | None = None):
    with Session(engine or make_engine()) as session:
        return split_today(all_tasks(session), today or date.today())
