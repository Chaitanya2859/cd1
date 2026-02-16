#!/usr/bin/env python3

import argparse
import json
import sys

from compiler_runner import run_cpp_compiler
from error_parser import parse_errors
from error_explainer import enrich_error, explain_error, load_error_data


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="C++ Error Analysis Tool",
        usage="%(prog)s [options] <source_file>"
    )

    parser.add_argument("source_file", help="C++ source file to compile and analyze")
    parser.add_argument("-j", "--json", action="store_true", help="output results in JSON format")
    parser.add_argument("-v", "--verbose", action="store_true", help="show detailed error information")
    parser.add_argument(
        "-c", "--context",
        type=int,
        default=2,
        metavar="LINES",
        help="number of context lines to show around errors (default: 2)"
    )
    parser.add_argument("--no-color", action="store_true", help="disable colored output")

    return parser.parse_args()


def print_error(error, show_context=True, use_color=True):
    if use_color and not args.no_color:
        RED = "\033[91m"
        YELLOW = "\033[93m"
        BLUE = "\033[94m"
        BOLD = "\033[1m"
        RESET = "\033[0m"
    else:
        RED = YELLOW = BLUE = BOLD = RESET = ""

    t = error.error_type.upper()
    if t == "ERROR":
        color = RED
    elif t == "WARNING":
        color = YELLOW
    else:
        color = BLUE

    loc = []
    if error.file:
        loc.append(f"{BOLD}{error.file}{RESET}")
    if error.line is not None:
        loc.append(f"line {error.line}")
    if error.column is not None:
        loc.append(f"column {error.column}")

    print(f"{color}{BOLD}{t}:{RESET} {error.message}")
    if loc:
        print(f"  {BLUE}{' '.join(loc)}{RESET}")

    if error.explanation:
        print(f"\n  {BOLD}Explanation:{RESET} {error.explanation}")
    if error.suggestion:
        print(f"\n  {BOLD}Suggestion:{RESET} {error.suggestion}")

    if show_context and error.context and "lines" in error.context:
        print(f"\n  {BOLD}Context:{RESET}")
        start = error.context["start_line"]

        for i, line in enumerate(error.context["lines"], start=start):
            pref = f"{i:4} "
            if i == error.line:
                print(f"{YELLOW}{pref}→ {line.rstrip()}{RESET}")
                if error.column and error.column > 0:
                    ind = " " * (error.column + len(pref) - 1) + f"{RED}^~~~{RESET}"
                    print(ind)
            else:
                print(f"{pref}  {line.rstrip()}")

    print()


def main():
    global args
    args = parse_arguments()

    out = run_cpp_compiler(args.source_file)
    if not out:
        if args.json:
            print(json.dumps({"status": "success", "message": "Compilation successful"}, indent=2))
        else:
            print("Compilation successful!")
        return 0

    errors = parse_errors(out)
    for e in errors:
        enrich_error(e)

    cat_stats = {}
    for e in errors:
        cat_stats.setdefault(e.category, 0)
        cat_stats[e.category] += 1

    if args.json:
        res = {
            "status": "error",
            "file": args.source_file,
            "error_count": len([e for e in errors if e.error_type == "error"]),
            "warning_count": len([e for e in errors if e.error_type == "warning"]),
            "categories": cat_stats,
            "errors": [e.to_dict() for e in errors],
        }
        print(json.dumps(res, indent=2))
    else:
        print(f"\n{len(errors)} {'error' if len(errors)==1 else 'errors'} found:\n")

        by_type = {}
        for e in errors:
            by_type.setdefault(e.error_type, []).append(e)

        for typ in ["error", "warning", "note", "linker"]:
            if typ in by_type:
                arr = by_type[typ]
                print(f"{len(arr)} {typ.upper()}{'S' if len(arr)!=1 else ''}:")
                for err in arr:
                    print()
                    print_error(err, show_context=args.verbose, use_color=not args.no_color)
                print()

        if cat_stats:
            print("\nCategory Summary:")
            for c, cnt in cat_stats.items():
                print(f"  {c}: {cnt}")

        ec = len([e for e in errors if e.error_type == "error"])
        wc = len([e for e in errors if e.error_type == "warning"])

        if ec or wc:
            parts = []
            if ec:
                parts.append(f"{ec} error{'s' if ec!=1 else ''}")
            if wc:
                parts.append(f"{wc} warning{'s' if wc!=1 else ''}")
            print("\n" + " ".join(parts) + " generated.")

    return 1 if any(e.error_type == "error" for e in errors) else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(2)
