"""PharmaShed CLI entrypoint. Subcommands added by each module as it lands."""

import argparse
import sys
from pathlib import Path

from pharmashed.params import DRUGS, NUMERIC_PARAMS, UnsourcedParameterError, load_rows

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_PARAMS_PATH = REPO_ROOT / "data" / "params" / "drug_parameters.csv"


def _params_check(args: argparse.Namespace) -> int:
    path = Path(args.path)
    rows = load_rows(path)

    by_drug: dict[str, dict[str, str]] = {d: {} for d in DRUGS}
    for row in rows:
        by_drug[row.drug][row.param] = row.status

    header = "drug".ljust(16) + "".join(p.ljust(12) for p in ["atc", *NUMERIC_PARAMS])
    print(header)
    for drug in DRUGS:
        cells = [by_drug[drug].get(p, "missing") for p in ["atc", *NUMERIC_PARAMS]]
        print(drug.ljust(16) + "".join(c.ljust(12) for c in cells))

    sourced = sum(1 for r in rows if r.status == "sourced")
    todo = len(rows) - sourced
    print(f"\n{sourced} sourced, {todo} todo (of {len(rows)} rows)")

    if args.strict:
        todo_rows = [r for r in rows if r.status == "todo" and r.param != "R"]
        if todo_rows:
            missing = [f"{r.drug}:{r.param}" for r in todo_rows]
            print(f"\nSTRICT MODE FAILED: {len(missing)} unsourced parameter(s)")
            print(UnsourcedParameterError(missing))
            return 1
        print("\nSTRICT MODE OK: all required rows sourced")

    return 0


def main() -> None:
    parser = argparse.ArgumentParser(prog="pharmashed")
    subparsers = parser.add_subparsers(dest="command")

    params_parser = subparsers.add_parser("params", help="drug parameter registry (M02)")
    params_subparsers = params_parser.add_subparsers(dest="params_command")

    check_parser = params_subparsers.add_parser("check", help="print sourced/todo status")
    check_parser.add_argument("--strict", action="store_true")
    check_parser.add_argument("--path", default=str(DEFAULT_PARAMS_PATH))
    check_parser.set_defaults(func=_params_check)

    args = parser.parse_args()
    if not hasattr(args, "func"):
        parser.print_help()
        sys.exit(0)

    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
