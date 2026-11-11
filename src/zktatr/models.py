"""SQLModel mapping of the zk notebook index plus a typed view of task notes.

zk owns the `notes` table; we never create or migrate it. The markdown files are
the source of truth, so treat writes through this layer with care: zk will
overwrite the index from the files on the next `zk index`.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field as PField, field_validator
from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


class Note(SQLModel, table=True):
    """Row of zk's `notes` table (only the columns we use)."""

    __tablename__ = "notes"

    id: int | None = Field(default=None, primary_key=True)
    path: str
    title: str = ""
    # zk stores the frontmatter as JSON text in a column called `metadata`,
    # which clashes with SQLModel's own `.metadata`, hence the alias.
    meta: dict[str, Any] = Field(
        default_factory=dict, sa_column=Column("metadata", JSON, nullable=False)
    )
    # zk writes nanosecond timestamps with an offset, which SQLite's DateTime
    # parser rejects. Keep the raw string and parse on demand.
    created: str = ""
    modified: str = ""


class Task(BaseModel):
    """Validated view of a note in tasks/."""

    path: str
    title: str
    status: str = "open"
    priority: int = 50
    due: date | None = None
    done: date | None = None
    tags: list[str] = PField(default_factory=list)
    link: str | None = None
    depends: list[str] = PField(default_factory=list)

    @field_validator("due", "done", mode="before")
    @classmethod
    def _lenient_date(cls, v: Any) -> date | None:
        if not v:
            return None
        try:
            return datetime.strptime(str(v).strip()[:10], "%Y-%m-%d").date()
        except ValueError:
            return None

    @field_validator("status", mode="before")
    @classmethod
    def _status(cls, v: Any) -> str:
        return str(v or "open").lower()

    @field_validator("priority", mode="before")
    @classmethod
    def _priority(cls, v: Any) -> int:
        return v if isinstance(v, int) else 50

    @field_validator("tags", mode="before")
    @classmethod
    def _tags(cls, v: Any) -> list[str]:
        return [str(t) for t in v] if isinstance(v, list) else []

    @field_validator("link", mode="before")
    @classmethod
    def _link(cls, v: Any) -> str | None:
        if isinstance(v, list):
            v = v[0] if v else None
        return str(v) if v else None

    @field_validator("depends", mode="before")
    @classmethod
    def _depends(cls, v: Any) -> list[str]:
        # YAML turns `depends: [[a]]` (wikilink style) into nested lists, and a
        # bare `depends: a` into a string; accept all of those.
        def flat(x: Any):
            if isinstance(x, (list, tuple)):
                for i in x:
                    yield from flat(i)
            elif x:
                yield str(x)

        return list(flat(v))

    @classmethod
    def from_note(cls, note: Note) -> Task:
        m = note.meta or {}
        # `done:` is not in the template yet; for finished tasks fall back to
        # the note's modified date so "done today" works before it is.
        done = m.get("done") or (note.modified if str(m.get("status")) == "done" else None)
        return cls(
            path=note.path,
            title=note.title,
            status=m.get("status"),
            priority=m.get("priority"),
            due=m.get("due"),
            done=done,
            tags=m.get("tags"),
            link=m.get("link"),
            depends=m.get("depends"),
        )

    @property
    def is_done(self) -> bool:
        return self.status == "done"
