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

    header = "drug".ljust(16) + "".join(p.ljust(14) for p in ["atc", *NUMERIC_PARAMS])
    print(header)
    for drug in DRUGS:
        cells = [by_drug[drug].get(p, "missing") for p in ["atc", *NUMERIC_PARAMS]]
        print(drug.ljust(16) + "".join(c.ljust(14) for c in cells))

    sourced = sum(1 for r in rows if r.status == "sourced")
    illustrative = sum(1 for r in rows if r.status == "illustrative")
    todo = len(rows) - sourced - illustrative
    print(f"\n{sourced} sourced, {illustrative} illustrative, {todo} todo (of {len(rows)} rows)")

    if args.strict:
        todo_rows = [r for r in rows if r.status == "todo" and r.param != "R"]
        if todo_rows:
            missing = [f"{r.drug}:{r.param}" for r in todo_rows]
            print(f"\nSTRICT MODE FAILED: {len(missing)} unsourced parameter(s)")
            print(UnsourcedParameterError(missing))
            return 1
        print("\nSTRICT MODE OK: no todo rows (illustrative rows are accepted, D36)")

    return 0


def _consumption_check(args: argparse.Namespace) -> int:
    path = Path(args.path)
    rows = load_consumption_rows(path)

    by_country: dict[str, dict[str, str]] = {c: {} for c in COUNTRIES}
    for row in rows:
        label = row.status if row.status == "todo" else f"{row.status}:{row.granularity}"
        by_country[row.country][row.drug] = label

    header = "country".ljust(10) + "".join(d.ljust(26) for d in DRUGS)
    print(header)
    for country in COUNTRIES:
        cells = [by_country[country].get(d, "missing") for d in DRUGS]
        print(country.ljust(10) + "".join(c.ljust(26) for c in cells))

    sourced = sum(1 for r in rows if r.status == "sourced")
    illustrative = sum(1 for r in rows if r.status == "illustrative")
    todo = len(rows) - sourced - illustrative
    print(f"\n{sourced} sourced, {illustrative} illustrative, {todo} todo (of {len(rows)} rows)")

    if args.strict:
        todo_rows = [r for r in rows if r.status == "todo"]
        if todo_rows:
            missing = [f"{r.country}:{r.drug}" for r in todo_rows]
            print(f"\nSTRICT MODE FAILED: {len(missing)} unsourced row(s)")
            print(UnsourcedConsumptionError(missing))
            return 1
        print("\nSTRICT MODE OK: no todo rows (illustrative rows are accepted, D36)")

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


def _run(args: argparse.Namespace) -> int:
    """Run the Monte Carlo model for every site x drug and write the build artifacts."""
    from pharmashed.export import export_build  # noqa: PLC0415
    from pharmashed.montecarlo import RunContext  # noqa: PLC0415
    from pharmashed.params import UnsourcedParameterError  # noqa: PLC0415
    from pharmashed.consumption import UnsourcedConsumptionError  # noqa: PLC0415

    try:
        ctx = RunContext.from_paths(mode=args.mode)
    except (UnsourcedParameterError, UnsourcedConsumptionError) as exc:
        print(f"STRICT MODE FAILED: {exc}")
        return 1

    zero_pop = [s.id for s in ctx.sites if s.population_buffer <= 0]
    if zero_pop:
        print(f"note: {len(zero_pop)} site(s) have zero population and will score 0: {', '.join(zero_pop)}")

    out = Path(args.out)
    results_path = export_build(ctx, out, variant=args.variant)
    print(
        f"wrote {results_path} ({len(ctx.sites)} sites x {len(DRUGS)} drugs, "
        f"{ctx.n_draws} draws, mode={args.mode}, variant={args.variant}); "
        f"{ctx.illustrative_count()} illustrative and {ctx.sourced_count()} sourced input rows"
    )
    return 0


DEFAULT_BUILD_DIR = REPO_ROOT / "data" / "build"
DEFAULT_FHIR_OUT = REPO_ROOT / "fhir" / "out"


def _fhir(args: argparse.Namespace) -> int:
    """Build the FHIR bundles and fhir_index.json from the model output in data/build/."""
    from pharmashed.checks.fhir_obs import build_reference_observations  # noqa: PLC0415
    from pharmashed.fhir.builder import build_all  # noqa: PLC0415

    build_dir = Path(args.build_dir)
    if not (build_dir / "results.json").exists():
        print(f"No results.json in {build_dir}. Run `pharmashed run` first.")
        return 1
    index = build_all(build_dir, Path(args.out), ref_obs=build_reference_observations())
    counts = index["resource_counts"]
    print(
        f"wrote {len(index['bundles'])} bundles to {args.out}: "
        f"{counts.get('Location', 0)} Location, {counts.get('Observation', 0)} Observation, "
        f"{index['query_demo']['model_prediction']['count']} model predictions, "
        f"{index['query_demo']['laboratory']['count']} lab/reference observations"
    )
    return 0


def _build(args: argparse.Namespace) -> int:
    """Run the model, then build the FHIR bundles (everything except freeze and checks)."""
    status = _run(args)
    if status != 0:
        return status
    args.build_dir = args.out
    args.out = str(DEFAULT_FHIR_OUT)
    return _fhir(args)


def _freeze(args: argparse.Namespace) -> int:
    """Freeze the predictions: strict run into data/frozen/, git commit and tag (D36)."""
    from pharmashed.freeze import FreezeError, run_freeze  # noqa: PLC0415

    try:
        path = run_freeze(mode="strict")
    except FreezeError as exc:
        print(f"FREEZE REFUSED: {exc}")
        return 1
    print(f"froze predictions: {path}")
    return 0


def _checks(args: argparse.Namespace) -> int:
    """Run the pre-registered consistency checks C1-C5 against the frozen predictions."""
    from pharmashed.checks.run import FrozenIntegrityError, run_checks  # noqa: PLC0415

    try:
        path = run_checks(frozen_dir=Path(args.frozen_dir), build_dir=Path(args.build_dir))
    except FrozenIntegrityError as exc:
        print(f"FROZEN FILE CHANGED: {exc}")
        return 1
    import json  # noqa: PLC0415

    for check in json.loads(path.read_text())["checks"]:
        print(f"  {check['id']}: {check['status']:11s} {check['reason']}")
    print(f"wrote {path}")
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

    run_parser = subparsers.add_parser("run", help="run the model and write data/build/ (M08-M11)")
    run_parser.add_argument("--mode", choices=["dev", "strict"], default="strict")
    run_parser.add_argument("--variant", choices=["full", "pop_only", "wwtp_only"], default="full")
    run_parser.add_argument("--out", default=str(REPO_ROOT / "data" / "build"))
    run_parser.set_defaults(func=_run)

    build_parser = subparsers.add_parser("build", help="run the model and build FHIR bundles")
    build_parser.add_argument("--mode", choices=["dev", "strict"], default="strict")
    build_parser.add_argument("--variant", choices=["full", "pop_only", "wwtp_only"], default="full")
    build_parser.add_argument("--out", default=str(DEFAULT_BUILD_DIR))
    build_parser.set_defaults(func=_build)

    fhir_parser = subparsers.add_parser("fhir", help="build FHIR bundles from data/build/ (M14)")
    fhir_parser.add_argument("--build-dir", default=str(DEFAULT_BUILD_DIR))
    fhir_parser.add_argument("--out", default=str(DEFAULT_FHIR_OUT))
    fhir_parser.set_defaults(func=_fhir)

    freeze_parser = subparsers.add_parser("freeze", help="freeze predictions: commit + git tag (M11)")
    freeze_parser.set_defaults(func=_freeze)

    checks_parser = subparsers.add_parser("checks", help="consistency checks C1-C5 on frozen predictions (M12)")
    checks_parser.add_argument("--frozen-dir", default=str(REPO_ROOT / "data" / "frozen"))
    checks_parser.add_argument("--build-dir", default=str(DEFAULT_BUILD_DIR))
    checks_parser.set_defaults(func=_checks)

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
