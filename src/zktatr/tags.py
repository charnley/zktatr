"""Tags in use across the whole zk notebook, for completion and `todo add`.

Reads zk's own tag index (what `zk tag` lists): every tag that at least one
note uses, from frontmatter or body hashtags. Stdlib only on purpose: tab
completion runs this on every keypress, and importing sqlmodel/sqlalchemy
would make it feel sluggish.
"""

import os
import re
import sqlite3
from pathlib import Path

# What `todo add` can write as a tag. zk also has tags like `6:1` (from times in
# meeting notes); those are left out since they could not be typed back.
TAG_NAME = re.compile(r"[A-Za-z0-9][\w-]*")


def tag_counts() -> list[tuple[str, int]]:
    """Usable tags of all notes, most used first, then alphabetical."""
    nb = Path(os.environ.get("ZK_NOTEBOOK_DIR", "~/notes")).expanduser()
    db = nb / ".zk" / "notebook.db"
    if not db.exists():
        return []
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        # The join drops stale tags that no note uses any more (zk keeps those
        # rows around), which matches `zk tag`.
        rows = con.execute(
            "SELECT c.name, COUNT(DISTINCT nc.note_id) FROM collections c "
            "JOIN notes_collections nc ON nc.collection_id = c.id "
            "WHERE c.kind = 'tag' GROUP BY c.id"
        ).fetchall()
    except sqlite3.Error:
        return []
    finally:
        con.close()
    rows = [(name, n) for name, n in rows if TAG_NAME.fullmatch(name)]
    return sorted(rows, key=lambda r: (-r[1], r[0].lower(), r[0]))


def known_spellings() -> dict[str, str]:
    """lowercase -> the spelling zk already has (the most used one)."""
    known: dict[str, str] = {}
    for name, _ in tag_counts():
        known.setdefault(name.lower(), name)
    return known
