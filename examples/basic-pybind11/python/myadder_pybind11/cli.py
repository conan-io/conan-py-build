"""CLI for myadder_pybind11; wired via [project.scripts] in pyproject.toml."""
import argparse
import sys

from myadder_pybind11 import add, add_integers, greet


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="myadder")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_add = sub.add_parser("add", help="Add two floats")
    p_add.add_argument("a", type=float)
    p_add.add_argument("b", type=float)

    p_addi = sub.add_parser("add-int", help="Add two integers")
    p_addi.add_argument("a", type=int)
    p_addi.add_argument("b", type=int)

    p_greet = sub.add_parser("greet", help="Greet someone")
    p_greet.add_argument("name")

    args = parser.parse_args(argv)

    if args.cmd == "add":
        add(args.a, args.b)
    elif args.cmd == "add-int":
        add_integers(args.a, args.b)
    elif args.cmd == "greet":
        greet(args.name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
