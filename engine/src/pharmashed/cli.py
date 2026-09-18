"""PharmaShed CLI entrypoint. Subcommands added by each module as it lands."""

import argparse
import sys
from pathlib import Path

from pharmashed.consumption import (
    COUNTRIES,
    UnsourcedConsumptionError,
)
from pharmashed.consumption import (
    load_rows as load_consumption_rows,
)
from pharmashed.params import DRUGS, NUMERIC_PARAMS, UnsourcedParameterError, load_rows
from pharmashed.population import population_in_buffer
from pharmashed.sites import cities, load_sites

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SITES_PATH = REPO_ROOT / "data" / "sites" / "sites.geojson"
DEFAULT_RAW_DIR = REPO_ROOT / "data" / "raw"
DEFAULT_PARAMS_PATH = REPO_ROOT / "data" / "params" / "drug_parameters.csv"
DEFAULT_CONSUMPTION_PATH = REPO_ROOT / "data" / "consumption" / "consumption.csv"


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


def _consumption_check(args: argparse.Namespace) -> int:
    path = Path(args.path)
    rows = load_consumption_rows(path)

    by_country: dict[str, dict[str, str]] = {c: {} for c in COUNTRIES}
    for row in rows:
        label = row.status if row.status == "todo" else f"{row.status}:{row.granularity}"
        by_country[row.country][row.drug] = label

    header = "country".ljust(10) + "".join(d.ljust(18) for d in DRUGS)
    print(header)
    for country in COUNTRIES:
        cells = [by_country[country].get(d, "missing") for d in DRUGS]
        print(country.ljust(10) + "".join(c.ljust(18) for c in cells))

    sourced = sum(1 for r in rows if r.status == "sourced")
    todo = len(rows) - sourced
    print(f"\n{sourced} sourced, {todo} todo (of {len(rows)} rows)")

    if args.strict:
        todo_rows = [r for r in rows if r.status == "todo"]
        if todo_rows:
            missing = [f"{r.country}:{r.drug}" for r in todo_rows]
            print(f"\nSTRICT MODE FAILED: {len(missing)} unsourced row(s)")
            print(UnsourcedConsumptionError(missing))
            return 1
        print("\nSTRICT MODE OK: all rows sourced")

    return 0


def _sites_check(args: argparse.Namespace) -> int:
    path = Path(args.path)
    sites = load_sites(path)
    from collections import Counter
    counts = Counter(s.city for s in sites)
    print(f"{'city':<6} {'count':>5}  {'size classes'}")
    for city in sorted(counts):
        city_sites = [s for s in sites if s.city == city]
        sc = "".join(sorted(s.size_class for s in city_sites))
        print(f"{city:<6} {counts[city]:>5}  {sc}")
    print(f"\nTotal: {len(sites)} sites across {len(counts)} cities")
    return 0


def _population_compute(args: argparse.Namespace) -> int:
    import json  # noqa: PLC0415
    raster_paths = sorted(Path(args.raster_dir).glob("GHS_POP_*.tif"))
    if not raster_paths:
        print(f"No GHS_POP_*.tif files found in {args.raster_dir}")
        print("Run scripts/fetch_ghspop.py first.")
        return 1

    sites_path = Path(args.sites)
    sites = load_sites(sites_path)
    geojson = json.loads(sites_path.read_text())

    flagged = 0
    for feat in geojson["features"]:
        site = next(s for s in sites if s.id == feat["properties"]["id"])
        pop = population_in_buffer(site, raster_paths, radius_m=args.radius)
        feat["properties"]["population_buffer"] = pop
        feat["properties"]["population_source_key"] = f"pop:ghs-pop-r2023a-{args.radius}m"
        if pop == 0:
            flagged += 1
            print(f"  WARNING: {site.id} has population=0 — review placement")

    sites_path.write_text(json.dumps(geojson, indent=2))
    print(f"Updated {len(sites)} sites in {sites_path}; {flagged} zero-population site(s)")
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

    consumption_parser = subparsers.add_parser("consumption", help="consumption registry (M03)")
    consumption_subparsers = consumption_parser.add_subparsers(dest="consumption_command")

    consumption_check_parser = consumption_subparsers.add_parser(
        "check", help="print sourced/todo status"
    )
    consumption_check_parser.add_argument("--strict", action="store_true")
    consumption_check_parser.add_argument("--path", default=str(DEFAULT_CONSUMPTION_PATH))
    consumption_check_parser.set_defaults(func=_consumption_check)

    pop_parser = subparsers.add_parser("population", help="GHS-POP computation (M05)")
    pop_subparsers = pop_parser.add_subparsers(dest="pop_command")
    pop_compute = pop_subparsers.add_parser("compute", help="write population_buffer into sites.geojson")
    pop_compute.add_argument("--raster-dir", default=str(DEFAULT_RAW_DIR))
    pop_compute.add_argument("--sites", default=str(DEFAULT_SITES_PATH))
    pop_compute.add_argument("--radius", type=float, default=500.0)
    pop_compute.set_defaults(func=_population_compute)

    sites_parser = subparsers.add_parser("sites", help="site registry (M04)")
    sites_subparsers = sites_parser.add_subparsers(dest="sites_command")
    sites_check_parser = sites_subparsers.add_parser("check", help="print site counts by city")
    sites_check_parser.add_argument("--path", default=str(DEFAULT_SITES_PATH))
    sites_check_parser.set_defaults(func=_sites_check)

    args = parser.parse_args()
    if not hasattr(args, "func"):
        parser.print_help()
        sys.exit(0)

    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
