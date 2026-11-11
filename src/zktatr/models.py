"""SQLModel mapping of the zk notebook index plus a typed view of task notes.

zk owns the `notes` table; we never create or migrate it. The markdown files are
the source of truth, so treat writes through this layer with care: zk will
overwrite the index from the files on the next `zk index`.
"""

import re
from datetime import date, datetime
from typing import Any, Self

from pydantic import BaseModel, Field as PField, field_validator
from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


def local_date(ts: str | None) -> date | None:
    """Local calendar date of a zk timestamp.

    zk stores `modified` in UTC with nanoseconds (`2026-11-10 23:30:00.123456789+00:00`),
    so convert to local time before taking the date, and trim to the 6 fractional
    digits datetime understands.
    """
    if not ts:
        return None
    try:
        dt = datetime.fromisoformat(re.sub(r"(\.\d{6})\d+", r"\1", ts.strip()))
    except ValueError:
        return None
    return (dt.astimezone() if dt.tzinfo else dt).date()


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
    modified: date | None = None  # local date of the last edit (from the index)
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
    def from_note(cls, note: Note) -> Self:
        m = note.meta or {}
        return cls(
            path=note.path,
            title=note.title,
            status=m.get("status"),
            priority=m.get("priority"),
            due=m.get("due"),
            done=m.get("done"),
            modified=local_date(note.modified),
            tags=m.get("tags"),
            link=m.get("link"),
            depends=m.get("depends"),
        )

    def finished_on(self, day: date) -> bool:
        """Done, and either marked done on `day` or last edited on `day`."""
        return self.is_done and day in (self.done, self.modified)

    @property
    def is_done(self) -> bool:
        return self.status == "done"
