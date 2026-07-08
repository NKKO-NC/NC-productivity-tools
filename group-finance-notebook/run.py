from __future__ import annotations

import argparse
from pathlib import Path

from gfnb.server import serve
from gfnb.service import NotebookService


def main() -> None:
    parser = argparse.ArgumentParser(description="Group Finance Notebook Phase 1 MVP")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument(
        "--db",
        default=str(Path("data") / "group_finance_notebook.db"),
        help="SQLite database path",
    )
    parser.add_argument(
        "--reset-demo",
        action="store_true",
        help="Reset database with built-in demo data before starting",
    )
    args = parser.parse_args()

    service = NotebookService(args.db)
    if args.reset_demo:
        service.reset_demo_data()
    else:
        service.ensure_demo_data()
    serve(service, args.host, args.port)


if __name__ == "__main__":
    main()
