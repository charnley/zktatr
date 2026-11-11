
# Zettlekasten 

Use `zk` setup with tasks management.

## Setup

You need [uv](https://docs.astral.sh/uv/), [zk](https://github.com/zk-org/zk) and
[fzf](https://github.com/junegunn/fzf) (for the task picker). Tasks are zk notes in
`<notebook>/tasks`; the notebook is `~/notes`, or `$ZK_NOTEBOOK_DIR` if set.

### Install `todo` into `~/.local/bin`

From this folder:

```sh
uv tool install --editable .
```

This puts `todo` (and `zktatr`, the same program) in `~/.local/bin`. Check with `todo --help`.

- **Editable** means the installed command runs the code in this folder, so there is no
  reinstall after changing it. The flip side: if you move or delete the folder, run the
  same command again from the new location.
- If `todo` is not found, `~/.local/bin` is not on your `PATH`: run `uv tool update-shell`
  and open a new shell.
- Remove it with `uv tool uninstall zktatr`.

### zsh tab completion

```sh
mkdir -p ~/.oh-my-zsh/custom/completions
ln -sf "$(todo completion zsh --path)" ~/.oh-my-zsh/custom/completions/_todo
```

then open a new shell. It completes subcommands, options, and `@tag` / `-t` from **all** tags
zk knows about (case-insensitive, most used first).

- It is a **symlink** into this repo (`src/zktatr/completions/_todo`), so updating the code
  updates the completion. Re-run the `ln -sf` if you move the folder.
- Without oh-my-zsh, link it into any directory on your `$fpath` that comes before `compinit`
  runs. `todo completion zsh` prints the script if you would rather copy or `source` it.
- If tab prints `todo: error: unrecognized arguments: -f +children ...`, zsh's built-in
  *devtodo* completion is answering because ours is not loaded. Check the symlink, delete
  `~/.zcompdump*` and open a new shell.

## Usage

```sh
todo                 # the TUI: today's tasks
todo --group         # same, grouped by tag
todo add ...         # add a task, see below
todo tags            # tags in use
```

The TUI lists **Open** tasks (not done, and no due date or due today or earlier; overdue ones
first, then by priority) and **Finished** ones (done, and marked done or last edited today).
A priority of 100 shows as `!`. Tasks can nest: `depends: [<id>, ...]` in the frontmatter
shows those tasks as subtasks (`2026-11-11-abcd1234`, `abcd1234`, a path or a `[[wikilink]]`).

| Key | Does |
|---|---|
| `enter` or `/` | pick tasks with fzf and open them in zk's editor |
| `r` | refresh (it also refreshes by itself when zk re-indexes) |
| `ctrl+d` | quit |

In fzf, `enter` opens **every** task still matching your query (just the highlighted one if
the query is empty), `tab` marks tasks one by one, `esc` cancels. Tags are searchable too.

### Adding tasks

```sh
todo add Fix the build                       # just a title
todo add Fix the build @chorus @foxcub       # trailing @words are tags
todo add Fix the build @chorus +++           # trailing + signs set the priority
todo add Fix the build -t chorus -p 3 -e     # same, with flags; -e opens it in the editor
```

- **Tags**: trailing `@tag` words (or `-t tag`). An existing tag keeps the spelling zk already
  has; a new one is lowercased.
- **Priority**: each trailing `+` is 25%, so `+` is 25, `++` is 50, `+++` is 75 and `++++` is
  100. No `+` leaves the template default (50). `-p N` is the same as N pluses.
- **`-e`**: opens the new task with `zk edit` (your configured editor) with a placeholder
  `Untitled` in the body. A zk editor command that searches for `Untitled`, such as
  `vim -c "silent! /Untitled"`, lands the cursor there.
- Only *trailing* words count, so `Fix issue #1` and `Port to C++` stay as typed.
  Titles can contain `:` and `#` safely.
- Options and words can come in any order; a fully quoted title works too.

**Why `@` and `+`, not `#` and `!`?** An unquoted `#tag` is a comment in an interactive shell
with `interactive_comments` on (oh-my-zsh enables it), and `!!` expands to your previous
command. `@` and `+` pass through untouched.

### Notes format

A task is a note in `tasks/` created from zk's `task` template. The frontmatter the app reads:

| Field | Meaning |
|---|---|
| `title` | shown in the list |
| `status` | `open` (default) or `done` |
| `priority` | number, higher first; 100 or more shows `!` |
| `tags` | list, used for grouping and search |
| `depends` | subtasks, see above |
| `due` | optional `YYYY-MM-DD`; hidden until then, overdue afterwards |
| `done` | optional `YYYY-MM-DD` for when it was finished |

The app reads zk's index (`<notebook>/.zk/notebook.db`) and never writes to it. Anything
edited outside zk shows up after the next `zk index`.

## Development

```sh
uv run pytest        # the tests that need zk are skipped if it is not installed
uv run todo          # run from the checkout instead of the installed command
```

## MVP

- [ ] I want to see the tasks I need to finish today

# References

- https://github.com/cstein/pytatr
- https://github.com/tsoding/tatr
- https://github.com/zk-org/zk
