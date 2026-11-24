"""Flight Schedule Parser and Query Tool - command-line entry point.

Run from the project folder, for example:
    python flight_parser.py -i data/db.csv -a data/airports.txt
"""
import argparse
import json
import logging
import os
import sys
from datetime import datetime

from csv_loader import parse_files
from query import run_queries
from validator import load_airports

# TODO: set STUDENT_ID to your real student ID (plain ASCII, no spaces/underscores).
STUDENT_ID = "251ADB242"
FIRST_NAME = "Ibrahim"
LAST_NAME = "Alizada"


class RuntimeProblem(Exception):
    """An expected runtime problem; reported as 'Error: ...' with exit code 1."""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="flight_parser.py",
        description="Validate flight CSV files, store them as JSON and query them.")
    parser.add_argument("-i", metavar="FILE", help="parse a single CSV file")
    parser.add_argument("-d", metavar="FOLDER", help="parse every .csv file in a folder")
    parser.add_argument("-j", metavar="FILE", help="load an existing JSON database")
    parser.add_argument("-a", metavar="FILE", help="airport list file (with -i / -d)")
    parser.add_argument("-o", metavar="FILE", help="output JSON database (default: db.json)")
    parser.add_argument("-q", metavar="FILE", help="JSON file with queries")
    parser.add_argument("-r", metavar="FOLDER", default=".",
                        help="folder for the response file (default: current directory)")
    return parser


def load_json(path: str, what: str):
    try:
        with open(path, encoding="utf-8-sig") as f:
            return json.load(f)
    except OSError as exc:
        raise RuntimeProblem(f"cannot read {what} '{path}': {exc.strerror or exc}")
    except (ValueError, UnicodeDecodeError) as exc:
        raise RuntimeProblem(f"{what} '{path}' is not valid JSON: {exc}")


def write_json(path: str, data) -> None:
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except OSError as exc:
        raise RuntimeProblem(f"cannot write '{path}': {exc.strerror or exc}")


def collect_csv_paths(folder: str) -> list[str]:
    try:
        names = sorted(os.listdir(folder))
    except OSError as exc:
        raise RuntimeProblem(f"cannot read folder '{folder}': {exc.strerror or exc}")
    paths = [os.path.join(folder, n) for n in names
             if n.endswith(".csv") and os.path.isfile(os.path.join(folder, n))]
    if not paths:
        raise RuntimeProblem(f"no .csv files found in '{folder}'")
    return paths


def parse_and_store(paths: list[str], airport_file: str, out_path: str) -> list[dict]:
    """Parse CSV files, write the database and errors.log; return the records."""
    try:
        airports = load_airports(airport_file)
        records, errors = parse_files(paths, airports)
    except OSError as exc:
        raise RuntimeProblem(f"cannot read '{exc.filename}': {exc.strerror or exc}")
    except UnicodeDecodeError as exc:
        raise RuntimeProblem(f"file is not valid UTF-8: {exc}")

    log_path = os.path.join(os.path.dirname(os.path.abspath(out_path)), "errors.log")
    logger = logging.getLogger("flight_parser")
    logger.setLevel(logging.INFO)
    try:
        handler = logging.FileHandler(log_path, mode="w", encoding="utf-8")
    except OSError as exc:
        raise RuntimeProblem(f"cannot write '{log_path}': {exc.strerror or exc}")
    handler.setFormatter(logging.Formatter(
        "%(asctime)s %(levelname)s %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
    logger.addHandler(handler)
    try:
        logger.info("Parsed %d file(s): %d valid, %d invalid",
                    len(paths), len(records), len(errors))
        for message in errors:
            logger.warning(message)
    finally:
        logger.removeHandler(handler)
        handler.close()

    write_json(out_path, records)
    print(f"{len(records)} valid flights, {len(errors)} invalid rows")
    return records


def run(args: argparse.Namespace) -> None:
    if args.j:
        db = load_json(args.j, "database")
        if not isinstance(db, list) or not all(isinstance(r, dict) for r in db):
            raise RuntimeProblem(f"database '{args.j}' must be a JSON array of objects")
    else:
        if args.i:
            paths = [args.i]
        else:
            paths = collect_csv_paths(args.d)
        db = parse_and_store(paths, args.a, args.o or "db.json")

    if args.q:
        queries = load_json(args.q, "query file")
        if not isinstance(queries, (dict, list)):
            raise RuntimeProblem(f"query file '{args.q}' must hold an object or an array")
        results = run_queries(db, queries)
        name = (f"response_{STUDENT_ID}_{FIRST_NAME}_{LAST_NAME}_"
                f"{datetime.now().strftime('%Y%m%d_%H%M')}.json")
        write_json(os.path.join(args.r, name), results)


def main(argv: list[str] | None = None) -> int:
    """Run the whole program and return the exit code (0, 1 or 2)."""
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
        sources = [s for s in (args.i, args.d, args.j) if s is not None]
        if len(sources) != 1:
            parser.error("exactly one of -i, -d or -j is required")
        if args.j is None and args.a is None:
            parser.error("-a is required with -i and -d")
        if args.j is not None and args.o is not None:
            parser.error("-o cannot be used with -j")
    except SystemExit as exc:
        code = exc.code
        return code if isinstance(code, int) else (0 if code is None else 2)

    try:
        run(args)
    except RuntimeProblem as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except (OSError, UnicodeDecodeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
