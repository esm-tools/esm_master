"""Console script for esm_master."""
import argparse
import sys


check = False
verbose = 0
# import logging
# logging.basicConfig(level=logging.DEBUG)
from . import __version__

def main():

    # global check, verbose

    parser = argparse.ArgumentParser(
        prog="esm_master",
        description="tool for downloading, configuring and compiling.",
    )
    parser.add_argument(
        "target",
        metavar="target",
        nargs="?",
        type=str,
        help="name of the target (leave empty for full list of targets)",
    )
    parser.add_argument(
        "--check",
        "-c",
        action="store_true",
        default=False,
        help="show what would be done, not doing anything",
    )
    parser.add_argument(
        "--verbose", "-v", action="count", default=0, help="toggle verbose mode"
    )
    parser.add_argument(
        "--version", action="version", version="%(prog)s " + __version__
    )
    parser.add_argument(
        "--keep-task-script",
        "-k",
        dest="keep",
        action="store_true",
        default=False,
        help="Keep shell script generated to perform compilation/configuration jobs",
    )
    parser.add_argument("--generate_tab_complete", action="store_true")
    parser.add_argument("--list_all_targets", action="store_true")
    parsed_args = vars(parser.parse_args())

    target = ""
    check = False
    verbose = 0


    if parsed_args:
        if "target" in parsed_args:
            target = parsed_args["target"]
        if "check" in parsed_args:
            check = parsed_args["check"]
        if "verbose" in parsed_args:
            verbose = parsed_args["verbose"]
        if "keep" in parsed_args:
            keep = parsed_args["keep"]

    if not target:
        target = ""

    from .esm_master import main_flow
    main_flow(parsed_args, target)


if __name__ == "__main__":
    main(sys.argv[1:])
