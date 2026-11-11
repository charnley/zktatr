import argparse
import sys


def add_arguments(p: argparse.ArgumentParser) -> None:
    p.add_argument("words", nargs="+", metavar="TITLE",
                   help="title; trailing @words become tags and +++ sets priority (each + is 25%%)")  # fmt: skip
    p.add_argument("-t", "--tag", action="append", default=[], help="add a tag (repeatable)")
    p.add_argument(
        "-e", "--edit", action="store_true",
        help="open the new task in zk's editor, with the cursor on a placeholder 'Untitled'",
    )  # fmt: skip
    p.add_argument(
        "-p", "--priority", type=int, choices=[1, 2, 3, 4], metavar="N",
        help="priority as a number of '+' (1-4 = 25-100%%); same as ++++",
    )  # fmt: skip


def main() -> None:
    parser = argparse.ArgumentParser(prog="todo", description="Today's zk tasks")
    parser.add_argument(
        "--group",
        nargs="?",
        const="tag",
        choices=["tag"],
        help="group tasks (default key when given without a value: tag)",
    )
    sub = parser.add_subparsers(dest="cmd")
    add = sub.add_parser("add", help="add a task: todo add Fix the build @chorus +++")
    add_arguments(add)
    sub.add_parser("tags", help="list the tags in use, most used first")
    comp = sub.add_parser("completion", help="print a shell completion script")
    comp.add_argument("shell", choices=["zsh"])
    if sys.argv[1:2] == ["add"]:
        # Intermixed, so `todo add Fix -p 3 the build @chorus` works; argparse
        # only allows that without subparsers, hence the dedicated parser.
        add_parser = argparse.ArgumentParser(prog="todo add")
        add_arguments(add_parser)
        args = add_parser.parse_intermixed_args(sys.argv[2:])
        args.cmd = "add"
    else:
        args = parser.parse_args()

    if args.cmd == "tags":
        from .tags import tag_counts

        for tag, _ in tag_counts():
            print(tag)
        return

    if args.cmd == "completion":
        from .completion import SCRIPTS

        print(SCRIPTS[args.shell], end="")
        return

    if args.cmd == "add":
        from .new import EDIT_MARKER, create_task, parse_words, priority_from_pluses

        title, tags, pluses = parse_words(args.words)
        try:
            path = create_task(
                title,
                tags + args.tag,
                priority_from_pluses(max(pluses, args.priority or 0)),
                body=EDIT_MARKER if args.edit else "",
            )
        except (ValueError, RuntimeError) as e:
            sys.exit(f"todo: {e}")
        print(f"added {path.name}: {title}")
        if args.edit:
            from .pick import open_in_editor

            try:
                open_in_editor([str(path)])  # zk edit: your configured editor, re-indexes on exit
            except RuntimeError as e:
                sys.exit(f"todo: {e}")
        return

    from .app import TaskApp

    TaskApp(group=args.group).run()
