"""Command-line entry point: tuivisy [--url ...] [--user ...] [--password ...]."""

from __future__ import annotations

import argparse

from tuivisy import __version__
from tuivisy.app import TuivisyApp
from tuivisy.plc import PlcConfig


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tuivisy",
        description="Terminal UI for CODESYS PLC visualizations over OPC UA.",
    )
    parser.add_argument("--version", action="version", version=f"tuivisy {__version__}")
    parser.add_argument(
        "--url",
        default="opc.tcp://localhost:4840",
        help="OPC UA endpoint (default: %(default)s)",
    )
    parser.add_argument("--user", default=None, help="device user name (CODESYS user management)")
    parser.add_argument("--password", default=None, help="device user password")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = PlcConfig(url=args.url, username=args.user, password=args.password)
    TuivisyApp(config).run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
