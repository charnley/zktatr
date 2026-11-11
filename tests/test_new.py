import shutil
import sqlite3

import pytest

from zktatr.new import clean_tags, create_task, split_tags

needs_zk = pytest.mark.skipif(shutil.which("zk") is None, reason="zk not installed")

CONFIG = """
[note]
filename = "{{format-date now '%Y-%m-%d'}}-{{id}}"
extension = "md"
template = "default.md"
id-charset = "alphanum"
id-length = 8
id-case = "lower"

[group.task]
paths = ["tasks"]

[group.task.note]
filename = "{{format-date now '%Y-%m-%d'}}-{{id}}"
extension = "md"
template = "task.md"
"""

TASK_TEMPLATE = """---
title: {{title}}
date: {{format-date now 'long'}}
status: open
priority: 50
tags: []
depends: []
link:
---

# {{title}}

{{content}}
"""


@pytest.fixture
def notebook(tmp_path, monkeypatch):
    nb = tmp_path.resolve()
    (nb / ".zk" / "templates").mkdir(parents=True)
    (nb / ".zk" / "config.toml").write_text(CONFIG)
    (nb / ".zk" / "templates" / "task.md").write_text(TASK_TEMPLATE)
    (nb / ".zk" / "templates" / "default.md").write_text("# {{title}}\n")
    monkeypatch.setenv("ZK_NOTEBOOK_DIR", str(nb))
    return nb


def indexed(nb):
    con = sqlite3.connect(nb / ".zk" / "notebook.db")
    rows = con.execute("select title, metadata from notes where path like 'tasks/%'").fetchall()
    con.close()
    return rows


def test_split_tags_only_trailing_and_letter_first():
    assert split_tags(["Fix", "the", "build", "#chorus", "#foxcub"]) == (
        "Fix the build", ["chorus", "foxcub"])
    assert split_tags(["fix", "issue", "#1"]) == ("fix issue #1", [])
    assert split_tags(["look", "#chorus", "stuff"]) == ("look #chorus stuff", [])
    assert split_tags(["#only"]) == ("", ["only"])


def test_split_tags_at_sign_and_quoted_title():
    # `@` survives zsh/bash interactive comment handling; `#` does not.
    assert split_tags(["Fix", "the", "build", "@chorus", "#Foxcub"]) == (
        "Fix the build", ["chorus", "Foxcub"])
    # a whole title passed as one quoted argument is split on whitespace too
    assert split_tags(["Fix the build @chorus"]) == ("Fix the build", ["chorus"])
    assert split_tags(["Fix the build #chorus"]) == ("Fix the build", ["chorus"])
    assert split_tags(["mail @anna about", "it"]) == ("mail @anna about it", [])


def test_clean_tags():
    assert clean_tags(["#Chorus", "chorus", "a_b-c"]) == ["chorus", "a_b-c"]
    with pytest.raises(ValueError):
        clean_tags(["has space"])


@needs_zk
def test_create_simple_task_is_indexed(notebook):
    path = create_task("Fix the build")
    assert path.parent == notebook / "tasks" and path.suffix == ".md"
    text = path.read_text()
    assert "# Fix the build\n" in text and "tags: []" in text
    [(title, meta)] = indexed(notebook)
    assert title == "Fix the build" and '"status":"open"' in meta


@needs_zk
def test_awkward_title_and_tags_survive(notebook):
    title = 'Call Anna: re budget #1 "now" ø'
    create_task(title, ["Chorus", "foxcub"])
    [(t, meta)] = indexed(notebook)
    assert t == title
    assert '"tags":["chorus","foxcub"]' in meta
    body = next((notebook / "tasks").glob("*.md")).read_text()
    assert f"# {title}\n" in body  # no stray quotes in the heading


@needs_zk
def test_tasks_get_distinct_files_and_load_in_the_app(notebook):
    a, b = create_task("one"), create_task("two", ["x"])
    assert a != b
    from zktatr.db import tasks_today

    todo, _ = tasks_today()
    assert sorted(t.title for t in todo) == ["one", "two"]


def test_empty_title_rejected(notebook):
    with pytest.raises(ValueError):
        create_task("   ")
