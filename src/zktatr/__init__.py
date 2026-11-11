import argparse


def main() -> None:
    from .app import TaskApp

    parser = argparse.ArgumentParser(prog="todo", description="Today's zk tasks")
    parser.add_argument(
        "--group",
        nargs="?",
        const="tag",
        choices=["tag"],
        help="group tasks (default key when given without a value: tag)",
    )
    args = parser.parse_args()
    TaskApp(group=args.group).run()
