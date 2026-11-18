import argparse
import sys
from collections.abc import Sequence

from rfikit import __version__

COMMANDS = ("extract", "analyze", "generate", "evaluate")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="rfikit")
    parser.add_argument("--version", action="store_true")
    parser.add_argument("command", nargs="?")
    parser.add_argument("rest", nargs="*")
    args = parser.parse_args(argv)
    if args.version:
        print(__version__)
        return 0
    if args.command is None:
        print(f"rfikit {__version__}")
        print("The commands are not built yet.")
        return 0
    if args.command in COMMANDS:
        print(f"The command {args.command} is not built yet.", file=sys.stderr)
        return 1
    print(f"Unknown command: {args.command}", file=sys.stderr)
    return 2
