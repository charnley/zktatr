"""Engine and queries against the zk notebook database."""

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


def split_tasks(
    tasks: list[Task], today: date, only_today: bool = False
) -> tuple[list[Task], list[Task]]:
    """(to do, done today).

    To do: every open task, or with `only_today` just those due today or
    earlier (undated ones are left out). Both lists are sorted the same way:
    priority (high first), then title. Done: finished on `today` (see
    `Task.finished_on`).
    """
    todo = [
        t for t in tasks
        if not t.is_done and (not only_today or (t.due is not None and t.due <= today))
    ]  # fmt: skip
    done = [t for t in tasks if t.finished_on(today)]
    todo.sort(key=lambda t: (-t.priority, t.title))
    done.sort(key=lambda t: t.title)
    return todo, done


def split_open(tasks: list[Task], today: date) -> tuple[list[Task], list[Task]]:
    """`todo`: all open tasks, plus what was finished today."""
    return split_tasks(tasks, today)


def split_today(tasks: list[Task], today: date) -> tuple[list[Task], list[Task]]:
    """`todo today`: open tasks due today or overdue, plus what was finished today."""
    return split_tasks(tasks, today, only_today=True)


def load_tasks(engine: Engine | None = None) -> list[Task]:
    with Session(engine or make_engine()) as session:
        return all_tasks(session)


def tasks_open(today: date | None = None, engine: Engine | None = None):
    with Session(engine or make_engine()) as session:
        return split_open(all_tasks(session), today or date.today())


def tasks_today(today: date | None = None, engine: Engine | None = None):
    with Session(engine or make_engine()) as session:
        return split_today(all_tasks(session), today or date.today())
