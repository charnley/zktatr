import argparse
import sys


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
    add = sub.add_parser("add", help="add a task: todo add Fix the build @chorus")
    add.add_argument("words", nargs="+", metavar="TITLE", help="title; trailing @words (or #words, quote those) become tags")
    add.add_argument("-t", "--tag", action="append", default=[], help="add a tag (repeatable)")
    args = parser.parse_args()

    if args.cmd == "add":
        from .new import create_task, split_tags

        title, tags = split_tags(args.words)
        try:
            path = create_task(title, tags + args.tag)
        except (ValueError, RuntimeError) as e:
            sys.exit(f"todo: {e}")
        print(f"added {path.name}: {title}")
        return

    from .app import TaskApp

    TaskApp(group=args.group).run()
