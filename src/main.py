#!/usr/bin/env python3

import argparse
import json
import sys

from compiler_runner import run_cpp_compiler
from error_parser import parse_errors
from error_explainer import enrich_error

RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[95m"
BOLD = "\033[1m"
RESET = "\033[0m"

def parse_arguments():
    parser=argparse.ArgumentParser(description="C++ Error Explaination Tool")

    parser.add_argument("source_file",help="C++ source file to compile")
    parser.add_argument("-j","--json",action="store_true",help="print output in JSON format")
    parser.add_argument("-v","--verbose",action="store_true",help="show detailed context")
    parser.add_argument("-c","--context",type=int,default=2,help="number of context lines")

    return parser.parse_args()


def print_error(error,verbose=False):
    etype=error.error_type.lower()

    if etype=="error":
        color=RED
    elif etype=="warning":
        color=YELLOW
    else:
        color=BLUE

    print(f"{color}{BOLD}{etype.upper()}:{RESET} {error.message}")

    if error.file:
        location=error.file
        if error.line is not None:
            location+=f": line {error.line}"
        if error.column is not None:
            location+=f", column {error.column}"
        print(f"  {BLUE}{location}{RESET}")

    if error.explanation:
        print(f"  Explanation: {error.explanation}")

    if error.suggestion:
        print(f"  Suggestion: {error.suggestion}")

    if verbose and error.context and "lines" in error.context:
        print("\n  Context:")
        start=error.context["start_line"]

        for i,line in enumerate(error.context["lines"],start=start):
            marker="->" if i==error.line else "  "
            print(f"  {marker} {i}: {line.rstrip()}")

    print()


def main():

    args=parse_arguments()

    output=run_cpp_compiler(args.source_file)

    if not output:
        if args.json:
            print(json.dumps({"status":"success"},indent=2))
        else:
            print("Compilation successful")
        return 0

    errors=parse_errors(output)

    for e in errors:
        enrich_error(e)

    if args.json:
        result={
            "status":"error",
            "file":args.source_file,
            "error_count":sum(1 for e in errors if e.error_type=="error"),
            "warning_count":sum(1 for e in errors if e.error_type=="warning"),
            "errors":[e.to_dict() for e in errors]
        }
        print(json.dumps(result,indent=2))
        return 1

    print(f"\n{len(errors)} issue(s) found:\n")

    error_count=0
    warning_count=0

    for e in errors:
        if e.error_type=="error":
            error_count+=1
        elif e.error_type=="warning":
            warning_count+=1

        print_error(e,verbose=args.verbose)

    print(f"{error_count} error(s), {warning_count} warning(s)")

    return 1 if error_count>0 else 0


if __name__ == "__main__":
    sys.exit(main())
