# zktatr

Task management on top of [zk](https://github.com/zk-org/zk). Tasks are zk notes in
`<notebook>/tasks` (notebook is in `$ZK_NOTEBOOK_DIR`).

Needs [uv](https://docs.astral.sh/uv/), zk and [fzf](https://github.com/junegunn/fzf).

## Setup

```sh
make install              # installs `todo` into ~/.local/bin
make install-completion   # zsh completion (oh-my-zsh)
```

## Usage

```sh
todo                              # TUI with today's tasks
todo tags                         # tags in use
todo add Fix the build            # add a task
todo add Fix the build @tag1 @tag2 ++   # trailing @tags and + priority (each + = 25)
todo add Fix the build -t tag1 -p 3 -e  # flags; -e opens the editor
```

TUI keys: `enter` or `/` pick tasks with fzf, `r` refresh, `ctrl+d` quit.

## Note format

Frontmatter fields: `title`, `status` (`open`/`done`), `priority`, `tags`, `depends`
(subtasks).

