import shutil
import sqlite3

import pytest

from zktatr.new import clean_tags, create_task, parse_words, priority_from_pluses

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
    assert parse_words(["Fix", "the", "build", "#chorus", "#foxcub"]) == (
        "Fix the build", ["chorus", "foxcub"], 0)
    assert parse_words(["fix", "issue", "#1"]) == ("fix issue #1", [], 0)
    assert parse_words(["look", "#chorus", "stuff"]) == ("look #chorus stuff", [], 0)
    assert parse_words(["#only"]) == ("", ["only"], 0)


def test_split_tags_at_sign_and_quoted_title():
    # `@` survives zsh/bash interactive comment handling; `#` does not.
    assert parse_words(["Fix", "the", "build", "@chorus", "#Foxcub"]) == (
        "Fix the build", ["chorus", "Foxcub"], 0)
    # a whole title passed as one quoted argument is split on whitespace too
    assert parse_words(["Fix the build @chorus"]) == ("Fix the build", ["chorus"], 0)
    assert parse_words(["Fix the build #chorus"]) == ("Fix the build", ["chorus"], 0)
    assert parse_words(["mail @anna about", "it"]) == ("mail @anna about it", [], 0)


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


def test_tag_counts_all_notes_in_use_and_usable(tmp_path, monkeypatch):
    nb = tmp_path.resolve()
    (nb / ".zk").mkdir()
    con = sqlite3.connect(nb / ".zk" / "notebook.db")
    con.executescript(
        """
        create table collections (id integer primary key, kind text, name text);
        create table notes_collections (id integer primary key, note_id integer, collection_id integer);
        insert into collections (id, kind, name) values
            (1, 'tag', 'b'), (2, 'tag', 'a'), (3, 'tag', 'Mixed'),
            (4, 'tag', 'stale'), (5, 'tag', '6:1'), (6, 'other', 'x');
        -- tag b: 2 notes (a task and a meeting), a: 1, Mixed: 1, '6:1': 1, stale: none
        insert into notes_collections (note_id, collection_id) values
            (1, 1), (2, 1), (1, 2), (3, 3), (3, 5), (3, 6);
        """
    )
    con.commit()
    con.close()
    monkeypatch.setenv("ZK_NOTEBOOK_DIR", str(nb))

    from zktatr.tags import known_spellings, tag_counts

    # meeting notes count; unused (`stale`), unusable (`6:1`), non-tag kinds do not
    assert tag_counts() == [("b", 2), ("a", 1), ("Mixed", 1)]  # ties: case-insensitive
    assert known_spellings() == {"b": "b", "a": "a", "mixed": "Mixed"}


def test_tag_counts_without_a_notebook(tmp_path, monkeypatch):
    monkeypatch.setenv("ZK_NOTEBOOK_DIR", str(tmp_path))
    from zktatr.tags import tag_counts

    assert tag_counts() == []


def test_clean_tags_keeps_existing_spelling():
    known = {"litlmol-xp": "Litlmol-xp", "chorus": "chorus"}
    assert clean_tags(["litlmol-xp", "CHORUS", "Brand-New"], known) == [
        "Litlmol-xp", "chorus", "brand-new"]


@needs_zk
def test_add_reuses_the_spelling_of_a_tag_from_any_note(notebook):
    (notebook / "meetings").mkdir()
    (notebook / "meetings" / "m.md").write_text("---\ntitle: M\ntags: [Litlmol-xp]\n---\n\n# M\n")
    import subprocess

    subprocess.run(["zk", "index", "--quiet", "--notebook-dir", str(notebook)], check=True)
    path = create_task("follow up", ["litlmol-xp", "new"])
    assert "tags: [Litlmol-xp, new]" in path.read_text()


def test_parse_pluses_any_order_and_only_trailing():
    assert parse_words(["Fix", "build", "+++"]) == ("Fix build", [], 3)
    assert parse_words(["Fix build +++ @chorus"]) == ("Fix build", ["chorus"], 3)
    assert parse_words(["Fix", "@chorus", "++++"]) == ("Fix", ["chorus"], 4)
    assert parse_words(["Fix", "+", "@a", "++"]) == ("Fix", ["a"], 3)  # several + words add up
    assert parse_words(["Port", "to", "C++"]) == ("Port to C++", [], 0)  # not a pure run of +
    assert parse_words(["Fix", "++", "build"]) == ("Fix ++ build", [], 0)  # not trailing
    assert parse_words(["Fix", "it!", "!!"]) == ("Fix it! !!", [], 0)  # ! is just text now


def test_priority_from_pluses():
    assert [priority_from_pluses(n) for n in (0, 1, 2, 3, 4, 9)] == [None, 25, 50, 75, 100, 100]


@needs_zk
def test_priority_written_only_when_given(notebook):
    plain = create_task("plain").read_text()
    assert "priority: 50\n" in plain  # template default untouched
    urgent = create_task("urgent", ["x"], priority_from_pluses(4)).read_text()
    assert "priority: 100\n" in urgent and "tags: [x]" in urgent
    from zktatr.db import tasks_today

    todo, _ = tasks_today()
    assert {t.title: t.priority for t in todo} == {"plain": 50, "urgent": 100}


@needs_zk
def test_body_lands_in_the_note_and_is_indexed(notebook):
    path = create_task("with body", body="Untitled")
    text = path.read_text()
    assert "# with body\n\nUntitled\n" in text
    assert "Untitled" not in create_task("no body").read_text()
    assert sorted(t for t, _ in indexed(notebook)) == ["no body", "with body"]


@needs_zk
def test_add_dash_e_creates_then_opens_in_editor(notebook, monkeypatch, capsys):
    import sys

    opened = []
    monkeypatch.setattr("zktatr.pick.open_in_editor", lambda paths: opened.extend(paths))
    monkeypatch.setattr(sys, "argv", ["todo", "add", "Call Anna: re budget", "-e", "@chorus"])
    from zktatr import main

    main()
    [path] = opened
    text = open(path).read()
    assert "title: \"Call Anna: re budget\"" in text and "tags: [chorus]" in text
    assert text.rstrip().endswith("Untitled")
    assert "added" in capsys.readouterr().out


@needs_zk
def test_add_without_e_does_not_open_anything(notebook, monkeypatch):
    import sys

    opened = []
    monkeypatch.setattr("zktatr.pick.open_in_editor", lambda paths: opened.extend(paths))
    monkeypatch.setattr(sys, "argv", ["todo", "add", "quiet one"])
    from zktatr import main

    main()
    assert opened == []
    assert "Untitled" not in next((notebook / "tasks").glob("*.md")).read_text()


def test_completion_is_a_real_file_matching_the_printed_script():
    import subprocess

    from zktatr.completion import script, script_path

    p = script_path("zsh")
    assert p.is_file() and p.name == "_todo"
    text = script("zsh")
    assert text.startswith("#compdef todo\n") and "ln -sf" in text
    if shutil.which("zsh"):
        assert subprocess.run(["zsh", "-n", str(p)]).returncode == 0  # parses
